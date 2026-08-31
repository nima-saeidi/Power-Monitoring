from typing import List, Dict
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # نگهداری کانکشن‌ها بر اساس feeder_id یا اتصال عمومی
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected.")

    async def broadcast(self, message: dict):
        """ارسال داده به تمامی کلاینت‌های متصل"""
        text_data = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_data)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.disconnect(connection)

ws_manager = ConnectionManager()
