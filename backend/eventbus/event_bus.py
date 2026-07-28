"""
Async EventBus implementation for three-layer decoupled architecture.
Supports wildcard subscriptions, error isolation, and event history.
"""

import asyncio
import fnmatch
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for async handler functions
Handler = Callable[[str, dict], Coroutine[Any, Any, None]]


@dataclass(slots=True)
class EventRecord:
    """Immutable record of a published event."""
    event_type: str
    data: dict
    timestamp: float = field(default_factory=time.time)
    handler_count: int = 0
    error_count: int = 0


class EventBus:
    """Async pub/sub event bus with wildcard subscription support.

    Features:
        - Wildcard patterns: 'data.*' matches all 'data.<anything>' events
        - Error isolation: one failing handler does not affect others
        - Event history: last 1000 events stored for diagnostics
        - Memory-safe: max 50 handlers per topic, max 1000 history records

    Usage:
        bus = EventBus()
        await bus.subscribe('data.fetch.complete', my_handler)
        await bus.subscribe('data.*', wildcard_handler)
        await bus.publish('data.fetch.complete', {'source': 'GEXMetrix'})
    """

    MAX_HISTORY: int = 1000
    MAX_HANDLERS_PER_TOPIC: int = 50

    def __init__(self) -> None:
        # Exact-match subscribers: topic -> [handler, ...]
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        # Wildcard subscribers: pattern -> [handler, ...]
        self._wildcard_subscribers: dict[str, list[Handler]] = defaultdict(list)
        # Event history ring buffer
        self._history: deque[EventRecord] = deque(maxlen=self.MAX_HISTORY)
        # Metrics
        self._total_published: int = 0
        self._total_errors: int = 0
        # Lock for subscriber mutations
        self._lock = asyncio.Lock()

    # ── Subscribe / Unsubscribe ───────────────────────────────────────────────

    async def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Exact topic string or wildcard pattern (e.g. 'data.*').
            handler: Async callable(event_type: str, data: dict) -> None.

        Raises:
            ValueError: If handler is not callable or topic is at capacity.
        """
        if not callable(handler):
            raise ValueError(f"Handler must be callable, got {type(handler)}")

        async with self._lock:
            target = (
                self._wildcard_subscribers
                if "*" in event_type
                else self._subscribers
            )
            handlers = target[event_type]
            if len(handlers) >= self.MAX_HANDLERS_PER_TOPIC:
                raise ValueError(
                    f"Topic '{event_type}' already has {len(handlers)} handlers "
                    f"(max {self.MAX_HANDLERS_PER_TOPIC})"
                )
            if handler not in handlers:
                handlers.append(handler)
                logger.debug(f"Subscribed handler to '{event_type}'")

    async def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """Remove a handler from an event type.

        Silently ignores if the handler was not subscribed.
        """
        async with self._lock:
            target = (
                self._wildcard_subscribers
                if "*" in event_type
                else self._subscribers
            )
            handlers = target.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
                logger.debug(f"Unsubscribed handler from '{event_type}'")

    # ── Publish ────────────────────────────────────────────────────────────────

    async def publish(self, event_type: str, data: dict | None = None) -> None:
        """Publish an event and dispatch to all matching handlers (fire-and-forget).

        Handlers are scheduled as concurrent asyncio tasks. Errors in individual
        handlers are logged but do not propagate.

        Args:
            event_type: The event topic string.
            data: Arbitrary payload dict (default empty).
        """
        data = data or {}
        handlers = self._resolve_handlers(event_type)

        # Record in history
        record = EventRecord(
            event_type=event_type,
            data=data,
            handler_count=len(handlers),
        )
        self._history.append(record)
        self._total_published += 1

        if not handlers:
            logger.debug(f"No handlers for '{event_type}'")
            return

        # Schedule all handlers concurrently
        for handler in handlers:
            asyncio.create_task(
                self._safe_invoke(handler, event_type, data, record)
            )

    async def emit(self, event_type: str, data: dict | None = None) -> list[Any]:
        """Publish an event and wait for all handlers to complete.

        Unlike publish(), this is awaitable and returns collected results.
        Errors in individual handlers are caught and logged; they do not
        prevent other handlers from running.

        Args:
            event_type: The event topic string.
            data: Arbitrary payload dict (default empty).

        Returns:
            List of return values from handlers (None for handlers that
            raised exceptions or returned nothing).
        """
        data = data or {}
        handlers = self._resolve_handlers(event_type)

        record = EventRecord(
            event_type=event_type,
            data=data,
            handler_count=len(handlers),
        )
        self._history.append(record)
        self._total_published += 1

        if not handlers:
            return []

        # Run all handlers concurrently, collect results
        tasks = [
            asyncio.create_task(
                self._safe_invoke_with_result(handler, event_type, data, record)
            )
            for handler in handlers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    # ── History & Diagnostics ──────────────────────────────────────────────────

    def get_history(
        self,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[EventRecord]:
        """Return recent event records, optionally filtered by type.

        Args:
            event_type: Filter to this exact type (None = all types).
            limit: Maximum number of records to return (default 50).

        Returns:
            List of EventRecord in chronological order (oldest first).
        """
        records = list(self._history)
        if event_type:
            records = [r for r in records if r.event_type == event_type]
        return records[-limit:]

    def get_stats(self) -> dict:
        """Return EventBus diagnostic statistics."""
        return {
            "total_published": self._total_published,
            "total_errors": self._total_errors,
            "history_size": len(self._history),
            "subscriber_count": sum(
                len(h) for h in self._subscribers.values()
            ),
            "wildcard_subscriber_count": sum(
                len(h) for h in self._wildcard_subscribers.values()
            ),
            "topics": list(self._subscribers.keys()),
            "wildcard_topics": list(self._wildcard_subscribers.keys()),
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _resolve_handlers(self, event_type: str) -> list[Handler]:
        """Collect all handlers matching the given event type.

        Matches both exact subscribers and wildcard patterns.
        """
        handlers: list[Handler] = []

        # Exact match
        handlers.extend(self._subscribers.get(event_type, []))

        # Wildcard match: check all registered patterns
        for pattern, pattern_handlers in self._wildcard_subscribers.items():
            if fnmatch.fnmatch(event_type, pattern):
                handlers.extend(pattern_handlers)

        return handlers

    @staticmethod
    async def _safe_invoke(
        handler: Handler,
        event_type: str,
        data: dict,
        record: EventRecord,
    ) -> None:
        """Invoke a handler, catching and logging any exception."""
        try:
            await handler(event_type, data)
        except Exception as exc:
            record.error_count += 1
            logger.error(
                f"EventBus handler error for '{event_type}': "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )

    @staticmethod
    async def _safe_invoke_with_result(
        handler: Handler,
        event_type: str,
        data: dict,
        record: EventRecord,
    ) -> Any:
        """Invoke a handler and return its result, or None on error."""
        try:
            return await handler(event_type, data)
        except Exception as exc:
            record.error_count += 1
            logger.error(
                f"EventBus handler error for '{event_type}': "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            return None
