import json
import logging
from datetime import datetime
from typing import List, Optional
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse
from modules.telemetry.repository import TelemetryRepository

logger = logging.getLogger(__name__)


class TelemetryService:
    @staticmethod
    async def process_and_store(data: TelemetryCreate, redis_client=None) -> TelemetryResponse:
        """۱. ذخیره در InfluxDB و ۲. انتشار روی Redis برای اطلاع لحظه‌ای Main API"""
        # ذخیره در ریپازیتوری
        await TelemetryRepository.write_point(data)

        response_data = TelemetryResponse.model_validate(data)

        # انتشار در پاب/ساب ردیس
        if redis_client:
            try:
                payload = response_data.model_dump(mode="json")
                await redis_client.publish("live_power_data", json.dumps(payload))
            except Exception as e:
                logger.error(f"Error publishing live data to Redis: {e}")

        return response_data

    @staticmethod
    async def get_latest_telemetry(feeder_id: int) -> Optional[TelemetryResponse]:
        """دریافت آخرین دیتای پایش‌شده فیدر"""
        return await TelemetryRepository.get_latest_by_feeder(feeder_id)

    @staticmethod
    async def get_telemetry_history(feeder_id: str, start_time: str, end_time: str):
        # مطمئن شوید feeder_id رشته است
        feeder_id_str = str(feeder_id)

        query = f'''
        from(bucket: "{settings.INFLUX_BUCKET}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
          |> filter(fn: (r) => r["feeder_id"] == "{feeder_id_str}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''

        result = await influx_client.query_api().query(query=query, org=settings.INFLUX_ORG)

        records = []
        for table in result:
            for record in table.records:
                records.append(record.values)

        return records

    @staticmethod
    async def get_chart_data(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m"
    ) -> dict:
        """دریافت داده‌های نمودار جهت نمایش در فرانت‌اند"""
        # خروجی repository از قبل ساختار استاندارد {"feeder_id": ..., "series": {"voltage": [{"timestamp": ..., "value": ...}], ...}} دارد
        return await TelemetryRepository.get_chart_data(
            feeder_id=feeder_id,
            start_time=start_time,
            end_time=end_time,
            window_period=window_period
        )
