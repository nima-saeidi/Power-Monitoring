from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_telemetry(self, data: dict):
        """ارسال دیتای جدید به تمامی کلاینت‌های متصل"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                # اگر کانکشن قطع شده باشد، آن را حذف می‌کنیم
                self.active_connections.remove(connection)

# یک نمونه سراسری (Singleton) ایجاد می‌کنیم
telemetry_ws_manager = ConnectionManager()
