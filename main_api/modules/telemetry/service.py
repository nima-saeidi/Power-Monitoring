import httpx
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.config import settings
from main_api.modules.telemetry.repository import TelemetryRepository
from main_api.modules.telemetry.schemas import TelemetryCreate, TelemetryResponse, ActiveFeederConfig
from main_api.modules.telemetry.ws_manager import ws_manager


class TelemetryService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        if session:
            self.repo = TelemetryRepository(session)
        else:
            self.repo = None

    # ==========================================
    # ۱. دریافت لیست فیدرهای فعال جهت شروع Polling
    # ==========================================
    async def get_active_feeders(self) -> List[ActiveFeederConfig]:
        if not self.repo:
            raise ValueError("AsyncSession is required for database operations.")
        return await self.repo.get_active_feeders()

    # ==========================================
    # ۲. متد ذخیره دیتابیس محلی و برادکست وب‌سوکت
    # ==========================================
    async def add_telemetry_data(self, data: TelemetryCreate) -> TelemetryResponse:
        if not self.repo:
            raise ValueError("AsyncSession is required for database operations.")

        record = await self.repo.create_record(data)

        response_model = TelemetryResponse.model_validate(record)
        response_data = response_model.model_dump(mode="json")

        await ws_manager.broadcast({
            "type": "NEW_TELEMETRY",
            "data": response_data
        })

        return record

    # ==========================================
    # ۳. ارتباط Proxy با میکروسرویس تلمتری (InfluxDB)
    # ==========================================
    @staticmethod
    async def get_latest_telemetry(feeder_id: str) -> Dict[str, Any]:
        url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}/telemetry/latest/{feeder_id}"

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == status.HTTP_200_OK:
                    return response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "خطا در دریافت داده از میکروسرویس تلمتری"
                )
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"ارتباط با میکروسرویس تلمتری برقرار نشد: {str(exc)}"
                )

    @staticmethod
    async def get_history(
        feeder_id: str,
        start: str = "-1h",
        stop: str = "now()",
        window: str = "1m"
    ) -> List[Dict[str, Any]]:
        url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}/telemetry/history/{feeder_id}"
        params = {
            "start": start,
            "stop": stop,
            "window": window
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == status.HTTP_200_OK:
                    return response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "خطا در دریافت تاریخچه از میکروسرویس تلمتری"
                )
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"عدم پاسخگویی میکروسرویس تلمتری در واکشی تاریخچه: {str(exc)}"
                )

    @staticmethod
    async def get_chart_data(
        feeder_id: str,
        start: str = "-24h",
        stop: str = "now()",
        window: str = "5m"
    ) -> Dict[str, Any]:
        """پروکسی دریافت داده‌های تفکیک‌شده نمودار از میکروسرویس تلمتری"""
        url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}/telemetry/chart/{feeder_id}"
        params = {
            "start": start,
            "stop": stop,
            "window": window
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == status.HTTP_200_OK:
                    return response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "خطا در دریافت داده‌های نمودار از میکروسرویس تلمتری"
                )
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"عدم پاسخگویی میکروسرویس تلمتری در واکشی داده‌های نمودار: {str(exc)}"
                )
