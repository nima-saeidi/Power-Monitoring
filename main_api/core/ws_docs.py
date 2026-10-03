"""Document the WebSocket endpoints in Swagger/OpenAPI.

OpenAPI has no native WebSocket support, so each WebSocket route is exposed as a
pseudo ``GET`` operation (tag "WebSockets") that describes the connection URL,
query parameters, close codes and the JSON messages the server pushes. The
message models are also registered under ``components.schemas``.
"""
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

from main_api.modules.notifications.schemas import NotificationResponse

WS_TAG = "WebSockets"

_CLOSE_CODES = (
    "**Close codes:** `1008` — توکن نامعتبر/ارسال‌نشده (یا عدم تطابق کاربر)؛ "
    "اتصال بلافاصله بسته می‌شود.\n\n"
    "**Heartbeat:** کلاینت متن `ping` می‌فرستد و سرور با متن `pong` پاسخ می‌دهد "
    "(این دو پیام JSON نیستند). پیام‌های دیگر نادیده گرفته می‌شوند."
)


class TelemetryMetricData(BaseModel):
    feeder_id: int
    active_power: float
    reactive_power: float
    voltage: float
    current: float
    power_factor: float
    timestamp: str
    load_status: Optional[Literal["normal", "warning", "critical", "unknown"]] = None
    load_percent: Optional[float] = Field(None, description="جریان نسبت به جریان نامی (درصد)")
    role: Optional[Literal["consumer", "producer"]] = None
    post_id: Optional[int] = None


class DeviceOfflineData(BaseModel):
    feeder_id: int
    failures_count: int
    error_message: str
    timestamp: str


class StatusChangeData(BaseModel):
    entity: Literal["feeder", "link"]
    id: int
    name: str
    feeder_id: int
    old_status: Literal["normal", "warning", "critical", "unknown"]
    new_status: Literal["normal", "warning", "critical", "unknown"]
    load_percent: Optional[float] = None
    current: Optional[float] = None


class WsNewTelemetry(BaseModel):
    type: Literal["NEW_TELEMETRY"]
    data: TelemetryMetricData


class WsDeviceAlert(BaseModel):
    type: Literal["DEVICE_ALERT"]
    data: DeviceOfflineData


class WsStatusChange(BaseModel):
    type: Literal["STATUS_CHANGE"]
    data: StatusChangeData


class WsNewNotification(BaseModel):
    type: Literal["NEW_NOTIFICATION"]
    data: NotificationResponse


def _query(name: str, schema_type: str, description: str, required: bool = False) -> Dict[str, Any]:
    return {"name": name, "in": "query", "required": required,
            "description": description, "schema": {"type": schema_type}}


def _ref(model: type) -> Dict[str, str]:
    return {"$ref": f"#/components/schemas/{model.__name__}"}


_WS_DOCS: Dict[str, Dict[str, Any]] = {
    "/telemetry/ws": {
        "summary": "WebSocket — telemetry live stream",
        "description": (
            "**URL:** `ws://<host>/telemetry/ws?token=<JWT>&feeder_id=<id>`\n\n"
            "پخش زنده‌ی تلمتری. بدون `feeder_id` همه‌ی فیدرها و با `feeder_id` فقط همان فیدر "
            "دریافت می‌شود. سرور سه نوع پیام می‌فرستد (فیلد `type` را بررسی کنید):\n\n"
            "- `NEW_TELEMETRY` — نمونه‌ی جدید اندازه‌گیری\n"
            "- `DEVICE_ALERT` — قطع ارتباط با دستگاه\n"
            "- `STATUS_CHANGE` — تغییر وضعیت بار (فیدر/لینک)\n\n"
            + _CLOSE_CODES
        ),
        "parameters": [
            _query("token", "string", "توکن JWT (access token)", required=True),
            _query("feeder_id", "integer", "اختیاری؛ فقط رویدادهای این فیدر"),
        ],
        "messages": [WsNewTelemetry, WsDeviceAlert, WsStatusChange],
    },
    "/notifications/ws/{user_id}": {
        "summary": "WebSocket — live notifications",
        "description": (
            "**URL:** `ws://<host>/notifications/ws/<user_id>?token=<JWT>`\n\n"
            "اعلان‌های لحظه‌ای کاربر. `user_id` باید با کاربرِ توکن یکسان باشد، وگرنه اتصال "
            "با کد `1008` بسته می‌شود. هر اعلان جدید با پیام `NEW_NOTIFICATION` می‌رسد.\n\n"
            + _CLOSE_CODES
        ),
        "parameters": [
            {"name": "user_id", "in": "path", "required": True,
             "description": "شناسه‌ی کاربر (باید برابر کاربر توکن باشد)", "schema": {"type": "integer"}},
            _query("token", "string", "توکن JWT (access token)", required=True),
        ],
        "messages": [WsNewNotification],
    },
}


def _build_openapi(app: FastAPI) -> Dict[str, Any]:
    schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    paths = schema.setdefault("paths", {})

    for path, doc in _WS_DOCS.items():
        messages: List[type] = doc["messages"]
        for model in messages:
            model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
            for name, definition in model_schema.pop("$defs", {}).items():
                components.setdefault(name, definition)
            components[model.__name__] = model_schema
        paths[path] = {"get": {
            "tags": [WS_TAG],
            "summary": doc["summary"],
            "description": doc["description"],
            "parameters": doc["parameters"],
            "responses": {
                "101": {
                    "description": "Switching Protocols — پیام‌های سرور (JSON)",
                    "content": {"application/json": {"schema": {"oneOf": [_ref(m) for m in messages]}}},
                },
                "403": {"description": "Rejected / closed with code 1008"},
            },
        }}
    return schema


def setup_ws_docs(app: FastAPI) -> None:
    def custom_openapi() -> Dict[str, Any]:
        if not app.openapi_schema:
            app.openapi_schema = _build_openapi(app)
        return app.openapi_schema

    app.openapi = custom_openapi
