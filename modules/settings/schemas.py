from pydantic import BaseModel, Field
from typing import Optional

class SettingUpdate(BaseModel):
    alfa: Optional[float] = Field(None, ge=0.0, description="ضریب آلفا")
    beta: Optional[float] = Field(None, ge=0.0, description="ضریب بتا")
    access_token_expire_minutes: Optional[int] = Field(None, gt=0, description="مدت اعتبار توکن به دقیقه")
    polling_interval: Optional[int] = Field(None, gt=0, description="بازه زمانی نمونه‌برداری به ثانیه")
    max_telemetry_failures: Optional[int] = Field(None, ge=1, description="تعداد خطاهای مجاز تله‌متری")

class SettingResponse(BaseModel):
    id: int
    alfa: float
    beta: float
    access_token_expire_minutes: int
    polling_interval: int
    max_telemetry_failures: int

    class Config:
        from_attributes = True
