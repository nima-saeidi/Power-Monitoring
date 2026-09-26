import asyncio
import re
from datetime import datetime, timedelta, timezone
import httpx
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.config import settings
from main_api.core.email_templates import build_feeder_offline_email_html
from main_api.modules.telemetry.repository import TelemetryRepository
from main_api.modules.telemetry.schemas import (
    TelemetryCreate, TelemetryResponse, ActiveFeederConfig, FeederStatusUpdate,
)
from main_api.modules.telemetry.ws_manager import ws_manager
from main_api.modules.notifications.models import NotificationType, NotificationPriority
from main_api.modules.notifications.alerts import dispatch_alert

# ایمپورت سیستم Audit Logging
from main_api.modules.audit_logs.services import send_audit_log


_RELATIVE_TIME = re.compile(r"^-(\d+)([smhdw])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_time(value: str, now: Optional[datetime] = None) -> datetime:
    """
    تبدیل زمان ورودی کاربر به datetime: «now()»، زمان نسبی مثل «-24h» / «-7d» یا ISO.
    (میکروسرویس تله‌متری start_time/end_time از نوع datetime می‌خواهد.)
    """
    now = now or datetime.now(timezone.utc)
    text = (value or "").strip()
    if text in ("", "now()", "now"):
        return now
    match = _RELATIVE_TIME.match(text)
    if match:
        return now - timedelta(seconds=int(match.group(1)) * _UNIT_SECONDS[match.group(2)])
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"قالب زمان نامعتبر است: {value} (مثال: -24h، now() یا ISO)")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def internal_headers() -> Dict[str, str]:
    """telemetry_service همه‌ی اندپوینت‌هایش را پشت کلید مشترک INTERNAL_API_KEY گذاشته است."""
    return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}


async def telemetry_request(method: str, path: str, *, params=None, json=None, timeout: float = 10.0) -> Any:
    """درخواست به میکروسرویس تله‌متری با تبدیل خطاها به HTTPException مناسب."""
    url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json, headers=internal_headers())
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"ارتباط با میکروسرویس تله‌متری برقرار نشد: {exc}")
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail or "خطای میکروسرویس تله‌متری")
    return response.json()


def time_range_params(start: str, stop: str, window: str) -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    start_dt, stop_dt = parse_time(start, now), parse_time(stop, now)
    if start_dt >= stop_dt:
        raise HTTPException(status_code=400, detail="زمان شروع باید قبل از زمان پایان باشد.")
    return {"start_time": start_dt.isoformat(), "end_time": stop_dt.isoformat(), "window": window}


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
    # ۱ب. دریافت گزارش وضعیت اتصال فیدر از telemetry_service (آنلاین/آفلاین)
    # ==========================================
    async def report_feeder_status(self, data: FeederStatusUpdate) -> None:
        if not self.repo:
            raise ValueError("AsyncSession is required for database operations.")

        feeder = await self.repo.update_feeder_status(
            feeder_id=data.feeder_id,
            is_online=data.is_online,
            consecutive_failures=data.consecutive_failures,
            last_success=data.last_success,
        )
        if not feeder:
            return

        # فقط در لحظه‌ی واقعی تغییر وضعیت (نه هر Polling) لاگ ثبت می‌شود تا
        # سیستم لاگینگ با پیام‌های تکراری پر نشود.
        if data.status_changed:
            action = "FEEDER_ONLINE" if data.is_online else "FEEDER_OFFLINE"
            description = (
                f"فیدر «{feeder.name}» (ID={feeder.id}) دوباره پاسخگو شد و آنلاین علامت‌گذاری شد."
                if data.is_online else
                f"فیدر «{feeder.name}» (ID={feeder.id}) پس از {data.consecutive_failures} بار عدم پاسخ، "
                f"آفلاین علامت‌گذاری شد."
            )
            asyncio.create_task(send_audit_log(
                action=action,
                username="System",
                service_name="telemetry_service",
                success=data.is_online,
                severity="INFO" if data.is_online else "WARNING",
                description=description,
                feeder_id=feeder.id,
                feeder_name=feeder.name,
                post_id=feeder.post_id,
                consecutive_failures=data.consecutive_failures,
            ))

            # فقط در لحظه‌ی واقعی قطعی فیدر (نه هر بار Polling)، به کاربرانی که
            # ادمین برایشان ارسال نوتیفیکیشن را فعال کرده، ایمیل هشدار ارسال می‌شود.
            # ارسال واقعی ایمیل توسط notification_service (از طریق صف notification_events)
            # انجام می‌شود؛ main_api فقط رویداد را منتشر می‌کند.
            # هشدار قطعی/اتصال مجدد: نوتیفیکیشن برای کاربران فعال و در قطعی، ایمیل به کاربرانی که
            # دریافت هشدار برایشان فعال است. await می‌شود (نه create_task) چون از همان AsyncSession
            # درخواست جاری استفاده می‌کند و AsyncSession برای همزمانی امن نیست.
            await self._alert_feeder_status(feeder, data)

    async def _alert_feeder_status(self, feeder, data: FeederStatusUpdate) -> None:
        metadata = {"event_type": "feeder_online" if data.is_online else "feeder_offline",
                    "feeder_id": feeder.id, "post_id": feeder.post_id,
                    "consecutive_failures": data.consecutive_failures}
        if data.is_online:
            await dispatch_alert(
                self.session,
                title=f"اتصال مجدد فیدر: {feeder.name}",
                message=f"فیدر «{feeder.name}» (شناسه {feeder.id}) دوباره پاسخگو شد و آنلاین است.",
                n_type=NotificationType.SUCCESS, priority=NotificationPriority.MEDIUM,
                source_type="feeder", source_id=feeder.id, metadata=metadata,
            )
            return
        await dispatch_alert(
            self.session,
            title=f"قطعی فیدر: {feeder.name}",
            message=(
                f"فیدر «{feeder.name}» (شناسه {feeder.id}) پس از {data.consecutive_failures} بار "
                "عدم پاسخ‌دهی، آفلاین علامت‌گذاری شد."
            ),
            n_type=NotificationType.ALERT, priority=NotificationPriority.HIGH,
            source_type="feeder", source_id=feeder.id, metadata=metadata,
            email_html=build_feeder_offline_email_html(feeder.name, feeder.id, data.consecutive_failures),
        )

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
                response = await client.get(url, headers=internal_headers())
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
            window: str = "1m",
            timeout: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        نکته کارایی: برای گزارش‌های بزرگ (بازه‌های زمانی طولانی/window ریز) کوئری
        InfluxDB می‌تواند بیش از timeout پیش‌فرض طول بکشد. صداکننده‌های گزارش‌گیری
        (export) باید timeout بزرگ‌تری پاس بدهند تا با خطای انقضای اتصال شکست نخورند.
        """
        url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}/telemetry/history/{feeder_id}"
        params = time_range_params(start, stop, window)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params, headers=internal_headers())
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
        params = time_range_params(start, stop, window)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params, headers=internal_headers())
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

    # ==========================================
    # ۴. انرژی، پیش‌بینی و فرمان (پروکسی به میکروسرویس تله‌متری)
    # ==========================================
    @staticmethod
    async def get_energy(feeder_ids: List[int], start: str, stop: str, window: Optional[str] = None,
                         timeout: float = 30.0) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        params: Dict[str, Any] = {
            "feeder_ids": feeder_ids,
            "start_time": parse_time(start, now).isoformat(),
            "end_time": parse_time(stop, now).isoformat(),
        }
        if window:
            params["window"] = window
        return await telemetry_request("GET", "/telemetry/energy", params=params, timeout=timeout)

    @staticmethod
    async def get_forecast(feeder_id: int, hours: int = 24, history_days: int = 7) -> Dict[str, Any]:
        return await telemetry_request(
            "GET", f"/telemetry/forecast/{feeder_id}", params={"hours": hours, "history_days": history_days}
        )

    @staticmethod
    async def send_coil_command(ip_address: str, port: int, slave_id: int, register_address: int,
                                value: bool) -> Dict[str, Any]:
        return await telemetry_request("POST", "/telemetry/command", json={
            "ip_address": ip_address, "port": port, "slave_id": slave_id,
            "register_address": register_address, "value": value,
        }, timeout=15.0)
