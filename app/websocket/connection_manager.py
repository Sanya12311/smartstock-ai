import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks connected /ws/market clients and broadcasts ticks to all of them."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("WebSocket connected: /ws/market (active=%s)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("WebSocket disconnected: /ws/market (active=%s)", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections)
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)


manager = ConnectionManager()


class UserConnectionManager:
    """Tracks connected websocket clients keyed by user id, for private per-user push."""

    def __init__(self) -> None:
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)
        logger.info("WebSocket connected: /ws/notifications user_id=%s", user_id)

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        async with self._lock:
            connections = self._connections.get(user_id)
            if connections:
                connections.discard(websocket)
                if not connections:
                    del self._connections[user_id]
        logger.info("WebSocket disconnected: /ws/notifications user_id=%s", user_id)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(user_id, ()))
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection, user_id)


notification_manager = UserConnectionManager()
