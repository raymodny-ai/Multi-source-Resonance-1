"""
Async EventBus implementation for three-layer decoupled architecture.
Supports wildcard subscriptions, error isolation, and event history.
"""

import asyncio
import contextvars
import copy
import fnmatch
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for async handler functions
Handler = Callable[[str, dict], Coroutine[Any, Any, None]]

# ContextVar so the static _safe_invoke helpers can find the active bus
# without holding a reference per-task. The pipeline publishes from a
# single bus per process, so this is safe.
_current_bus: contextvars.ContextVar["EventBus | None"] = contextvars.ContextVar(
    "current_event_bus", default=None
)


def _get_current_bus() -> "EventBus | None":
    return _current_bus.get()


@dataclass(slots=True)
class EventRecord:
    """Record of a published event.

    PIPE-16: ``data`` is a deep-copy snapshot taken at publish time so
    later mutations of the caller's dict do not silently rewrite the
    history. The previous version held a direct reference, which meant
    any handler that mutated its ``data`` argument corrupted the bus's
    audit log.
    """
    event_type: str
    data: dict
    timestamp: float = field(default_factory=time.time)
    handler_count: int = 0
    error_count: int = 0

    def __post_init__(self) -> None:
        # FIX-16: deep-copy at construction so the record is decoupled
        # from whatever dict the publisher passed in.
        try:
            self.data = copy.deepcopy(self.data)
        except Exception:
            # Fall back to a shallow copy if deep-copy fails (e.g. a
            # non-pickleable value in the payload). This is still better
            # than a shared reference.
            self.data = dict(self.data)


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
        # PIPE-08: keep a bounded set of in-flight handler tasks so
        # shutdown can await them instead of having them silently
        # cancelled mid-dispatch.
        self._inflight_tasks: set[asyncio.Task] = set()
        # Lock for subscriber mutations
        self._lock = asyncio.Lock()
        # PIPE-09: register this bus as the "current" one for the
        # static _safe_invoke helpers to find.
        _current_bus.set(self)

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

        # PIPE-08: keep a strong reference to every dispatched task so
        # shutdown can drain them. ``add_done_callback`` removes the task
        # from the set as soon as it completes (success or failure), so
        # the set stays bounded.
        for handler in handlers:
            task = asyncio.create_task(
                self._safe_invoke(handler, event_type, data, record)
            )
            self._inflight_tasks.add(task)
            task.add_done_callback(self._inflight_tasks.discard)

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
        """Invoke a handler, catching and logging any exception.

        PIPE-09: increment the bus-level ``_total_errors`` counter on
        every handler failure so ``get_stats()`` reflects reality. The
        previous version only updated the per-record counter, so the
        bus-level total stayed at 0 forever.
        """
        try:
            await handler(event_type, data)
        except Exception as exc:
            record.error_count += 1
            # PIPE-09: surface the failure in the bus-wide counter.
            # We reach into the bus instance via a thread-local lookup
            # so this static helper can still update the singleton.
            try:
                bus = _get_current_bus()
                if bus is not None:
                    bus._total_errors += 1
            except Exception:
                pass
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
            # PIPE-09: same as _safe_invoke — keep the bus-level counter honest.
            try:
                bus = _get_current_bus()
                if bus is not None:
                    bus._total_errors += 1
            except Exception:
                pass
            logger.error(
                f"EventBus handler error for '{event_type}': "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            return None

    # ── Shutdown ───────────────────────────────────────────────────────────────

    async def drain(self, timeout: float = 5.0) -> None:
        """PIPE-08: wait for all in-flight handler tasks to finish.

        Called during application shutdown. Safe to invoke when no tasks
        are running (immediate return). Per-task cancellation is
        escalated only if the global timeout expires.
        """
        if not self._inflight_tasks:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._inflight_tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"EventBus.drain: {len(self._inflight_tasks)} handler(s) "
                f"still in flight after {timeout}s; cancelling"
            )
            for task in list(self._inflight_tasks):
                if not task.done():
                    task.cancel()
