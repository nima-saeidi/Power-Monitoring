import asyncio
import re
from datetime import datetime, timedelta, timezone
import httpx
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.config import settings
from main_api.core.email_templates import build_feeder_offline_email_html
from main_api.core.errors import api_error
from main_api.modules.telemetry.repository import TelemetryRepository
from main_api.modules.telemetry.schemas import (
    TelemetryCreate, TelemetryResponse, ActiveFeederConfig, FeederStatusUpdate,
)
from main_api.modules.telemetry.ws_manager import ws_manager
from main_api.modules.notifications.models import NotificationType, NotificationPriority
from main_api.modules.notifications.alerts import dispatch_alert

from main_api.modules.audit_logs.services import send_audit_log


_RELATIVE_TIME = re.compile(r"^-(\d+)([smhdw])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_time(value: str, now: Optional[datetime] = None) -> datetime:
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
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "INVALID_TIME_FORMAT",
            f"قالب زمان نامعتبر است: {value} (مثال: -24h، now() یا ISO)"
        )
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def internal_headers() -> Dict[str, str]:
    return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}


def _forward_microservice_error(response: httpx.Response) -> HTTPException:
    """Re-raise a failed microservice response as-is when it already carries a
    structured {error_code, message} body, so the frontend sees the real cause
    (e.g. DEVICE_UNREACHABLE) instead of a generic HTTP_502. Falls back to a
    generic code only for responses the microservice didn't shape itself
    (e.g. a raw 502 from an unreachable container, not from its app code)."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict) and isinstance(body.get("detail"), dict) and "message" in body["detail"]:
        return HTTPException(status_code=response.status_code, detail=body["detail"])
    message = (body or {}).get("detail") if isinstance(body, dict) else response.text
    return api_error(
        response.status_code, "TELEMETRY_SERVICE_ERROR",
        message or "خطای نامشخص از میکروسرویس تله‌متری"
    )


async def telemetry_request(method: str, path: str, *, params=None, json=None, timeout: float = 10.0) -> Any:
    url = f"{settings.TELEMETRY_SERVICE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json, headers=internal_headers())
    except httpx.RequestError as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE, "TELEMETRY_SERVICE_UNAVAILABLE",
            f"ارتباط با میکروسرویس تله‌متری برقرار نشد: {exc}"
        )
    if response.status_code >= 400:
        raise _forward_microservice_error(response)
    return response.json()


def time_range_params(start: str, stop: str, window: str) -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    start_dt, stop_dt = parse_time(start, now), parse_time(stop, now)
    if start_dt >= stop_dt:
        raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_TIME_RANGE", "زمان شروع باید قبل از زمان پایان باشد.")
    return {"start_time": start_dt.isoformat(), "end_time": stop_dt.isoformat(), "window": window}


class TelemetryService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        if session:
            self.repo = TelemetryRepository(session)
        else:
            self.repo = None

    async def get_active_feeders(self) -> List[ActiveFeederConfig]:
        if not self.repo:
            raise ValueError("AsyncSession is required for database operations.")

        try:
            return await self.repo.get_active_feeders()
        except Exception as e:
            asyncio.create_task(send_audit_log(
                action="GET_ACTIVE_FEEDERS_ERROR",
                username="System",
                success=False,
                severity="ERROR",
                description=f"خطا در دریافت لیست فیدرهای فعال از دیتابیس جهت Polling: {str(e)}"
            ))
            raise

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
            feeder_id = data.feeder_id if hasattr(data, 'feeder_id') else 'نامشخص'
            asyncio.create_task(send_audit_log(
                action="TELEMETRY_INGESTION_ERROR",
                username="System",
                success=False,
                severity="CRITICAL",
                description=f"خطا در ثبت داده‌های تلمتری در دیتابیس محلی (فیدر: {feeder_id}): {str(e)}"
            ))
            raise

    @staticmethod
    async def _proxy_get(path: str, *, params=None, timeout: float,
                         unavailable_action: str, unavailable_description: str,
                         severity: str = "ERROR") -> Any:
        """Shared GET-and-forward logic for the three read-only telemetry_service
        proxies below: on a genuine connectivity failure (service down/unreachable)
        it fires the same TELEMETRY_MICROSERVICE_UNAVAILABLE audit log they each
        used to duplicate; any app-level error the microservice itself returned
        (4xx/5xx with a structured body) is forwarded to the caller unchanged via
        telemetry_request(), so its real error_code/message survive intact."""
        try:
            return await telemetry_request("GET", path, params=params, timeout=timeout)
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and exc.detail.get("error_code") == "TELEMETRY_SERVICE_UNAVAILABLE":
                asyncio.create_task(send_audit_log(
                    action=unavailable_action,
                    username="System",
                    success=False,
                    severity=severity,
                    description=f"{unavailable_description} {exc.detail.get('message')}"
                ))
            raise

    @staticmethod
    async def get_latest_telemetry(feeder_id: str) -> Dict[str, Any]:
        return await TelemetryService._proxy_get(
            f"/telemetry/latest/{feeder_id}", timeout=5.0,
            unavailable_action="TELEMETRY_MICROSERVICE_UNAVAILABLE", severity="CRITICAL",
            unavailable_description=f"عدم دسترسی به میکروسرویس تلمتری برای دریافت آخرین داده فیدر {feeder_id}.",
        )

    @staticmethod
    async def get_history(
            feeder_id: str,
            start: str = "-1h",
            stop: str = "now()",
            window: str = "1m",
            timeout: float = 10.0
    ) -> List[Dict[str, Any]]:
        params = time_range_params(start, stop, window)
        return await TelemetryService._proxy_get(
            f"/telemetry/history/{feeder_id}", params=params, timeout=timeout,
            unavailable_action="TELEMETRY_MICROSERVICE_UNAVAILABLE",
            unavailable_description=f"دریافت تاریخچه برای فیدر {feeder_id} با خطا مواجه شد.",
        )

    @staticmethod
    async def get_chart_data(
            feeder_id: str,
            start: str = "-24h",
            stop: str = "now()",
            window: str = "5m"
    ) -> Dict[str, Any]:
        params = time_range_params(start, stop, window)
        return await TelemetryService._proxy_get(
            f"/telemetry/chart/{feeder_id}", params=params, timeout=10.0,
            unavailable_action="TELEMETRY_MICROSERVICE_UNAVAILABLE",
            unavailable_description=f"دریافت داده‌های چارت برای فیدر {feeder_id} شکست خورد.",
        )

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
