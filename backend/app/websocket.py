"""WebSocket manager for real-time optimization progress updates.

Provides:
- Connection management per user
- Room-based broadcasting (per portfolio, per optimization)
- Heartbeat keepalive
- Graceful reconnection support
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("quantive.websocket")


class ConnectionManager:
    """Manages WebSocket connections with room-based broadcasting."""

    def __init__(self):
        # user_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        # room_id (portfolio/optimization id) -> set of user_ids
        self._rooms: dict[str, set[str]] = {}
        # user_id -> set of room_ids they've joined
        self._user_rooms: dict[str, set[str]] = {}
        # last heartbeat per connection
        self._heartbeats: dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        self._heartbeats[websocket] = time.time()
        logger.info(f"WebSocket connected: user={user_id}")

        # Send welcome message
        await self._send_to(websocket, {
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a disconnected WebSocket."""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
                # Clean up rooms
                if user_id in self._user_rooms:
                    for room_id in self._user_rooms[user_id]:
                        if room_id in self._rooms:
                            self._rooms[room_id].discard(user_id)
                            if not self._rooms[room_id]:
                                del self._rooms[room_id]
                    del self._user_rooms[user_id]
        self._heartbeats.pop(websocket, None)
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def join_room(self, user_id: str, room_id: str) -> None:
        """Subscribe a user to a room (e.g., portfolio or optimization updates)."""
        if user_id not in self._user_rooms:
            self._user_rooms[user_id] = set()
        self._user_rooms[user_id].add(room_id)

        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(user_id)
        logger.debug(f"User {user_id} joined room {room_id}")

    async def leave_room(self, user_id: str, room_id: str) -> None:
        """Unsubscribe a user from a room."""
        if user_id in self._user_rooms:
            self._user_rooms[user_id].discard(room_id)
        if room_id in self._rooms:
            self._rooms[room_id].discard(user_id)
        logger.debug(f"User {user_id} left room {room_id}")

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any]) -> int:
        """Broadcast a message to all users in a room.

        Returns the number of connections that received the message.
        """
        if room_id not in self._rooms:
            return 0

        user_ids = self._rooms[room_id]
        sent = 0

        for user_id in list(user_ids):
            if user_id in self._connections:
                dead = []
                for ws in list(self._connections[user_id]):
                    try:
                        await self._send_to(ws, message)
                        sent += 1
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self.disconnect(ws, user_id)

        return sent

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> int:
        """Send a message to all connections of a specific user.

        Returns the number of connections that received the message.
        """
        if user_id not in self._connections:
            return 0

        sent = 0
        dead = []
        for ws in list(self._connections[user_id]):
            try:
                await self._send_to(ws, message)
                sent += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

        return sent

    async def broadcast_all(self, message: dict[str, Any]) -> int:
        """Broadcast to ALL connected users. Use sparingly."""
        sent = 0
        for user_id in list(self._connections):
            sent += await self.send_to_user(user_id, message)
        return sent

    def get_online_users(self) -> list[str]:
        """Get list of currently connected user IDs."""
        return list(self._connections.keys())

    def get_room_members(self, room_id: str) -> list[str]:
        """Get user IDs in a room."""
        return list(self._rooms.get(room_id, set()))

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    async def handle_message(self, websocket: WebSocket, user_id: str, data: dict) -> None:
        """Handle an incoming WebSocket message from a client."""
        msg_type = data.get("type", "")

        if msg_type == "ping":
            self._heartbeats[websocket] = time.time()
            await self._send_to(websocket, {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

        elif msg_type == "join_room":
            room_id = data.get("room_id")
            if room_id:
                await self.join_room(user_id, room_id)
                await self._send_to(websocket, {"type": "room_joined", "room_id": room_id})

        elif msg_type == "leave_room":
            room_id = data.get("room_id")
            if room_id:
                await self.leave_room(user_id, room_id)
                await self._send_to(websocket, {"type": "room_left", "room_id": room_id})

        else:
            await self._send_to(websocket, {"type": "error", "message": f"Unknown message type: {msg_type}"})

    @staticmethod
    async def _send_to(websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single WebSocket."""
        await websocket.send_json(message)


# ── Singleton ─────────────────────────────────────────────────────────────

_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


# ── Helper for broadcasting optimization progress ────────────────────────

async def broadcast_optimization_progress(
    optimization_id: str,
    user_id: str,
    status: str,
    progress: int,
    message: str = "",
    result: Optional[dict] = None,
) -> None:
    """Broadcast optimization progress to the optimization room and the user."""
    manager = get_ws_manager()
    payload = {
        "type": "optimization_progress",
        "optimization_id": optimization_id,
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if result:
        payload["result"] = result

    # Broadcast to optimization room
    await manager.broadcast_to_room(f"optimization:{optimization_id}", payload)

    # Also send directly to user
    await manager.send_to_user(user_id, payload)


async def broadcast_portfolio_update(portfolio_id: str, action: str, data: dict) -> None:
    """Broadcast a portfolio change event to the portfolio room."""
    manager = get_ws_manager()
    await manager.broadcast_to_room(f"portfolio:{portfolio_id}", {
        "type": "portfolio_update",
        "portfolio_id": portfolio_id,
        "action": action,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
