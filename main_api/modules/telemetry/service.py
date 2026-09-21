import asyncio
import httpx
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.config import settings
from main_api.modules.telemetry.repository import TelemetryRepository
from main_api.modules.telemetry.schemas import TelemetryCreate, TelemetryResponse, ActiveFeederConfig
from main_api.modules.telemetry.ws_manager import ws_manager

# ایمپورت سیستم Audit Logging
from main_api.modules.audit_logs.services import send_audit_log


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

        try:
            return await self.repo.get_active_feeders()
        except Exception as e:
            # ثبت لاگ در صورت بروز خطای دیتابیس هنگام دریافت تنظیمات فیدرها
            asyncio.create_task(send_audit_log(
                action="GET_ACTIVE_FEEDERS_ERROR",
                username="System",
                success=False,
                severity="ERROR",
                description=f"خطا در دریافت لیست فیدرهای فعال از دیتابیس جهت Polling: {str(e)}"
            ))
            raise

    # ==========================================
    # ۲. متد ذخیره دیتابیس محلی و برادکست وب‌سوکت
    # ==========================================
    async def add_telemetry_data(self, data: TelemetryCreate) -> TelemetryResponse:
        if not self.repo:
            raise ValueError("AsyncSession is required for database operations.")

        try:
            record = await self.repo.create_record(data)

            response_model = TelemetryResponse.model_validate(record)
            response_data = response_model.model_dump(mode="json")

            await ws_manager.broadcast({
                "type": "NEW_TELEMETRY",
                "data": response_data
            })

            return record
        except Exception as e:
            # فقط حالت خطا لاگ می‌شود تا از پر شدن دیتابیس حسابرسی با رکوردهای موفق جلوگیری شود
            feeder_id = data.feeder_id if hasattr(data, 'feeder_id') else 'نامشخص'
            asyncio.create_task(send_audit_log(
                action="TELEMETRY_INGESTION_ERROR",
                username="System",
                success=False,
                severity="CRITICAL",
                description=f"خطا در ثبت داده‌های تلمتری در دیتابیس محلی (فیدر: {feeder_id}): {str(e)}"
            ))
            raise

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
                error_msg = f"ارتباط با میکروسرویس تلمتری برقرار نشد: {str(exc)}"

                # ثبت لاگ قطعی ارتباط با میکروسرویس (سطح بحرانی)
                asyncio.create_task(send_audit_log(
                    action="TELEMETRY_MICROSERVICE_UNAVAILABLE",
                    username="System",
                    success=False,
                    severity="CRITICAL",
                    description=f"عدم دسترسی به میکروسرویس تلمتری برای دریافت آخرین داده فیدر {feeder_id}. {error_msg}"
                ))

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg
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
                error_msg = f"عدم پاسخگویی میکروسرویس تلمتری در واکشی تاریخچه: {str(exc)}"

                asyncio.create_task(send_audit_log(
                    action="TELEMETRY_MICROSERVICE_UNAVAILABLE",
                    username="System",
                    success=False,
                    severity="ERROR",
                    description=f"دریافت تاریخچه برای فیدر {feeder_id} با خطا مواجه شد. {error_msg}"
                ))

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg
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
                error_msg = f"عدم پاسخگویی میکروسرویس تلمتری در واکشی داده‌های نمودار: {str(exc)}"

                asyncio.create_task(send_audit_log(
                    action="TELEMETRY_MICROSERVICE_UNAVAILABLE",
                    username="System",
                    success=False,
                    severity="ERROR",
                    description=f"دریافت داده‌های چارت برای فیدر {feeder_id} شکست خورد. {error_msg}"
                ))

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg
                )
