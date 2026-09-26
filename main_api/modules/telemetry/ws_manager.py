import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

# حداکثر زمان ارسال به یک کلاینت؛ کلاینت کند نباید ارسال به بقیه را متوقف کند
SEND_TIMEOUT_SECONDS = 5


class ConnectionManager:
    def __init__(self):
        # هر اتصال -> feeder_id مورد علاقه‌ی کلاینت (None یعنی داده‌ی همه‌ی فیدرها)
        self.active_connections: Dict[WebSocket, Optional[int]] = {}

    async def connect(self, websocket: WebSocket, feeder_id: Optional[int] = None):
        await websocket.accept()
        self.active_connections[websocket] = feeder_id
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if self.active_connections.pop(websocket, "missing") != "missing":
            logger.info("WebSocket client disconnected.")

    async def _send(self, connection: WebSocket, text_data: str):
        try:
            await asyncio.wait_for(connection.send_text(text_data), timeout=SEND_TIMEOUT_SECONDS)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            self.disconnect(connection)

    async def broadcast(self, message: dict):
        """ارسال داده به کلاینت‌های متصل (فقط کلاینت‌هایی که همین فیدر یا همه‌ی فیدرها را خواسته‌اند)"""
        text_data = json.dumps(message, default=str)
        feeder_id = (message.get("data") or {}).get("feeder_id")
        targets = [
            conn for conn, wanted in list(self.active_connections.items())
            if wanted is None or feeder_id is None or wanted == feeder_id
        ]
        await asyncio.gather(*(self._send(conn, text_data) for conn in targets))

ws_manager = ConnectionManager()
