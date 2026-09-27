import asyncio
import json
import logging
from fastapi import WebSocket
from typing import Dict, List

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 5


class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def _send(self, connection: WebSocket, text_data: str, user_id: int):
        try:
            await asyncio.wait_for(connection.send_text(text_data), timeout=SEND_TIMEOUT_SECONDS)
        except Exception as e:
            logger.warning(f"Dropping notification WebSocket of user {user_id}: {e}")
            self.disconnect(connection, user_id)

    async def send_personal_message(self, message: dict, user_id: int):
        connections = list(self.active_connections.get(user_id, []))
        if not connections:
            return
        text_data = json.dumps(message, default=str)
        await asyncio.gather(*(self._send(conn, text_data, user_id) for conn in connections))

notifier_manager = NotificationConnectionManager()
