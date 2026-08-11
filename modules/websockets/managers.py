from fastapi import WebSocket
from typing import List, Dict

# ---------------------------------------------------------
# ۱. مدیر اتصالات تله‌متری (برای دیتای لحظه‌ای سنسورها - ساختار شما)
# ---------------------------------------------------------
class TelemetryConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_telemetry(self, data: dict):
        for connection in self.active_connections.copy(): # از copy استفاده کنید تا در حین حلقه ارور ندهد
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

# ---------------------------------------------------------
# ۲. مدیر اتصالات نوتیفیکیشن‌ها (برای هشدارها و پیام‌های سیستمی - با تفکیک کاربر)
# ---------------------------------------------------------
class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections and websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, data: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_json(data)
                except Exception:
                    self.disconnect(connection, user_id)

    async def broadcast_alarm(self, data: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections.copy():
                try:
                    await connection.send_json(data)
                except Exception:
                    self.disconnect(connection, user_id)


# ایجاد نمونه‌ها (Singleton) برای استفاده در کل اپلیکیشن
telemetry_manager = TelemetryConnectionManager()
notification_manager = NotificationConnectionManager()
