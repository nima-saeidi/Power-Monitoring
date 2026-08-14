from sqlalchemy.ext.asyncio import AsyncSession
from modules.telemetry.repository import TelemetryRepository
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse
from modules.telemetry.ws_manager import telemetry_ws_manager


class TelemetryService:
    def __init__(self, session: AsyncSession):
        self.repo = TelemetryRepository(session)

    async def add_telemetry_data(self, data: TelemetryCreate):
        # ۱. ذخیره در دیتابیس
        record = await self.repo.create_record(data)

        # ۲. تبدیل رکورد به فرمت دیکشنری مناسب برای JSON
        response_data = TelemetryResponse.model_validate(record).model_dump(mode='json')

        # ۳. ارسال بلادرنگ به فرانت‌اند از طریق وب‌سوکت
        await telemetry_ws_manager.broadcast_telemetry({
            "type": "NEW_TELEMETRY",
            "data": response_data
        })

        return record
