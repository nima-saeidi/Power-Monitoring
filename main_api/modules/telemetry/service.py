from sqlalchemy.ext.asyncio import AsyncSession
from main_api.modules.telemetry.repository import TelemetryRepository
from main_api.modules.telemetry.schemas import TelemetryCreate, TelemetryResponse
from main_api.modules.telemetry.ws_manager import telemetry_ws_manager


class TelemetryService:
    def __init__(self, session: AsyncSession):
        self.repo = TelemetryRepository(session)

    async def add_telemetry_data(self, data: TelemetryCreate) -> TelemetryResponse:
        """
        دریافت داده تله‌متری، ذخیره در دیتابیس و برادکست آنی به فرانت‌اند.
        """
        # ۱. ذخیره امن در دیتابیس (توسط Repository)
        record = await self.repo.create_record(data)

        # ۲. تبدیل رکورد دیتابیس (SQLAlchemy) به مدل Pydantic و سپس JSON
        response_model = TelemetryResponse.model_validate(record)
        response_data = response_model.model_dump(mode='json')

        # ۳. ارسال بلادرنگ به فرانت‌اند از طریق مدیر وب‌سوکت
        await telemetry_ws_manager.broadcast_telemetry({
            "type": "NEW_TELEMETRY",
            "data": response_data
        })

        return record
