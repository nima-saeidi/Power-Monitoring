import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

# ایمپورت تابع اجرای زمان‌بند
from telemetry_service.scheduler import start_scheduler

app = FastAPI(title="Telemetry Service", description="Modbus Reading and WebSocket Broadcasting")


# --- مدیریت اتصالات وب‌سوکت تله‌متری ---
class TelemetryConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # کپی از لیست برای جلوگیری از خطای تغییر سایز لیست حین حلقه
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending data to websocket: {e}")
                self.disconnect(connection)


telemetry_manager = TelemetryConnectionManager()


# --- رویدادهای راه‌اندازی سرویس ---
@app.on_event("startup")
async def startup_event():
    print("Starting Telemetry Service...")

    # گرفتن Event Loop اصلی برنامه برای ارسال به ترد
    loop = asyncio.get_running_loop()

    # اجرای زمان‌بند در ترد جداگانه و پاس دادن loop و manager به آن
    threading.Thread(
        target=start_scheduler,
        args=(loop, telemetry_manager),
        daemon=True
    ).start()


# --- Endpoint وب‌سوکت ---
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await telemetry_manager.connect(websocket)
    try:
        while True:
            # کلاینت فقط گوش می‌دهد، اما اگر پیامی داد دریافت می‌کنیم تا ارتباط قطع نشود
            await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_manager.disconnect(websocket)
