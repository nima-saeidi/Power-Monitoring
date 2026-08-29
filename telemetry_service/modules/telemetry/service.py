import json
import logging
from datetime import timezone
from influxdb_client import Point
from core.config import settings
from core.database import influx_manager
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse

logger = logging.getLogger(__name__)


class TelemetryService:
    @staticmethod
    async def save_telemetry_to_influx(data: TelemetryCreate) -> bool:
        """تبدیل متریک‌ها به Time-Series Point و ذخیره در InfluxDB"""
        try:
            client = influx_manager.get_client()
            write_api = client.write_api()

            ts = data.timestamp if data.timestamp else datetime.now(timezone.utc)

            point = (
                Point("feeder_telemetry")
                .tag("feeder_id", str(data.feeder_id))
                .field("voltage", float(data.voltage))
                .field("current", float(data.current))
                .field("active_power", float(data.active_power))
                .field("frequency", float(data.frequency if data.frequency is not None else 50.0))
                .time(ts)
            )

            if data.post_id:
                point.tag("post_id", str(data.post_id))

            await write_api.write(
                bucket=settings.INFLUX_BUCKET,
                org=settings.INFLUX_ORG,
                record=point
            )
            return True
        except Exception as e:
            logger.error(f"Failed to write telemetry to InfluxDB: {e}")
            return False

    @classmethod
    async def process_and_store(cls, data: TelemetryCreate, redis_client=None) -> TelemetryResponse:
        """ذخیره در دیتابیس سری‌زمانی و انتشار زنده روی Message Broker"""
        # ۱. ذخیره سری‌زمانی در InfluxDB
        await cls.save_telemetry_to_influx(data)

        response_data = TelemetryResponse.model_validate(data)

        # ۲. انتشار زنده برای main_api یا سرویس وب‌سوکت
        if redis_client:
            try:
                payload = response_data.model_dump(mode="json")
                await redis_client.publish("live_power_data", json.dumps(payload))
            except Exception as e:
                logger.error(f"Error publishing live data to Redis: {e}")

        return response_data
