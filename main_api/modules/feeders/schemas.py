from typing import Optional, Dict, Any
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from main_api.core.domain import normalize_energy_role


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    feeder_type: Optional[str] = None
    max_current: Optional[float] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    modbus_address: Optional[int] = None
    active_power_register: Optional[int] = None
    reactive_power_register: Optional[int] = None
    voltage_register: Optional[int] = None
    current_register: Optional[int] = None
    power_factor_register: Optional[int] = None
    # آدرس Coil فرمان قطع/وصل
    control_register: Optional[int] = None
    # تنظیم مقیاس رجیسترها در metadata_info (اختیاری):
    #   {"register_scales": {"voltage": 0.1, "power_factor": 0.001}, "signed_registers": ["reactive_power"]}
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_online: bool = True
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None

    @field_validator("feeder_type", mode="before")
    @classmethod
    def _normalize_feeder_type(cls, value):
        return normalize_energy_role(value)


class FeederCreate(FeederBase):
    post_id: int


class FeederUpdate(BaseModel):
    name: Optional[str] = None
    feeder_type: Optional[str] = None
    max_current: Optional[float] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    modbus_address: Optional[int] = None
    active_power_register: Optional[int] = None
    reactive_power_register: Optional[int] = None
    voltage_register: Optional[int] = None
    current_register: Optional[int] = None
    power_factor_register: Optional[int] = None
    control_register: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    consecutive_failures: Optional[int] = None

    @field_validator("feeder_type", mode="before")
    @classmethod
    def _normalize_feeder_type(cls, value):
        return normalize_energy_role(value)


class FeederResponse(FeederBase):
    id: int
    post_id: int
    # normal / warning / critical / unknown
    load_status: str = "unknown"

    @field_validator("feeder_type", mode="before")
    @classmethod
    def _tolerant_feeder_type(cls, value):
        # داده‌های قدیمی ممکن است مقدار نامعتبر داشته باشند؛ در خروجی خطا ندهد
        try:
            return normalize_energy_role(value)
        except ValueError:
            return value

    model_config = ConfigDict(from_attributes=True)


# ----------------- فرمان قطع/وصل (با تأیید دومرحله‌ای ایمیلی) -----------------
class CommandRequest(BaseModel):
    """مرحله‌ی اول: درخواست فرمان؛ کد تأیید به ایمیل کاربر ارسال می‌شود."""
    action: Literal["connect", "disconnect"]


class CommandChallengeResponse(BaseModel):
    message: str
    challenge_token: str
    expires_in: int


class CommandConfirmRequest(BaseModel):
    """مرحله‌ی دوم: تأیید فرمان با کد ایمیل‌شده."""
    challenge_token: str = Field(..., max_length=2048)
    code: str = Field(..., max_length=10)
