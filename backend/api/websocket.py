"""
WebSocket endpoint for real-time data push.
Subscribes to EventBus events and broadcasts them to connected WebSocket clients.
Supports multiple concurrent clients with automatic cleanup on disconnect.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.eventbus.event_bus import EventBus
from backend.eventbus.events import EventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """Manages WebSocket connections and EventBus subscriptions.

    Each connected client receives all events (or filtered by topic).
    Supports multiple concurrent clients with automatic cleanup.
    """

    def __init__(self) -> None:
        # Active connections: websocket -> set of subscribed topics (empty = all)
        self._connections: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = set()  # empty = subscribe to all
        logger.info(f"WebSocket client connected. Total: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Total: {len(self._connections)}")

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        disconnected: list[WebSocket] = []

        async with self._lock:
            connections = list(self._connections.items())

        topic = message.get("topic", "?")
        sent = 0
        for ws, topics in connections:
            try:
                # If client has topic filters, check them
                if topics:
                    msg_topic = message.get("topic", "")
                    if msg_topic not in topics and "*" not in topics:
                        continue
                await ws.send_text(payload)
                sent += 1
            except Exception as exc:
                logger.warning(f"[ws] send_text failed for topic={topic}: {type(exc).__name__}: {exc}")
                disconnected.append(ws)

        if sent or disconnected:
            logger.info(f"[ws] broadcast topic={topic} sent={sent}/{len(connections)} disconnected={len(disconnected)}")

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._connections)


# Global WebSocket manager instance
ws_manager = WebSocketManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time data push.

    Message format:
    {
        "topic": "GEXMETRIX_SNAPSHOT",
        "payload": {...},
        "timestamp": "2026-07-28T05:49:51"
    }

    Clients receive all events by default.
    """
    await ws_manager.connect(websocket)

    try:
        while True:
            # Listen for client messages (commands, topic filters, etc.)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Handle subscribe/unsubscribe commands
                action = msg.get("action")
                if action == "subscribe":
                    topic = msg.get("topic")
                    if topic:
                        async with ws_manager._lock:
                            if websocket in ws_manager._connections:
                                ws_manager._connections[websocket].add(topic)
                        await websocket.send_text(json.dumps({
                            "topic": "system",
                            "payload": {"message": f"Subscribed to {topic}"},
                        }))
                elif action == "unsubscribe":
                    topic = msg.get("topic")
                    if topic:
                        async with ws_manager._lock:
                            if websocket in ws_manager._connections:
                                ws_manager._connections[websocket].discard(topic)
                        await websocket.send_text(json.dumps({
                            "topic": "system",
                            "payload": {"message": f"Unsubscribed from {topic}"},
                        }))
                elif action == "ping":
                    await websocket.send_text(json.dumps({
                        "topic": "system",
                        "payload": {"pong": True},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }))
            except json.JSONDecodeError:
                pass  # Ignore malformed messages
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)


async def setup_event_bus_bridge(event_bus: EventBus) -> None:
    """Subscribe WebSocket broadcaster to all relevant EventBus events.

    Called during application startup to bridge EventBus -> WebSocket clients.
    """
    # Topics to broadcast to WebSocket clients
    topics_to_bridge = [
        EventType.GEXMETRIX_SNAPSHOT,
        EventType.SIGNAL,
        EventType.SIGNAL_GENERATED,
        EventType.SIGNAL_ALERT,
        EventType.INCIDENT,
        EventType.CONFIG,
        EventType.DATA_FETCH_COMPLETE,
        EventType.DATA_FETCH_ERROR,
        EventType.SCORING_COMPLETE,
        EventType.SYSTEM_CONFIG_CHANGE,
        EventType.SYSTEM_START,
        EventType.SYSTEM_STOP,
    ]

    async def ws_bridge_handler(event_type: str, data: dict) -> None:
        """Bridge EventBus events to WebSocket clients."""
        message = {
            "topic": event_type,
            "payload": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await ws_manager.broadcast(message)

    for topic in topics_to_bridge:
        await event_bus.subscribe(topic, ws_bridge_handler)

    # Also subscribe to wildcard to catch all events
    await event_bus.subscribe("data.*", ws_bridge_handler)
    await event_bus.subscribe("signal.*", ws_bridge_handler)
    await event_bus.subscribe("system.*", ws_bridge_handler)

    logger.info(f"WebSocket bridge subscribed to {len(topics_to_bridge)} event topics")
