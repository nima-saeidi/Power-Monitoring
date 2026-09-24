import logging
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client import Point
from core.config import settings

logger = logging.getLogger(__name__)

def _safe_float(val, default=0.0) -> float:
    """تبدیل ایمن مقادیر با پشتیبانی از مقادیر None یا رشته‌های خراب"""
    if val is None:
        return float(default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(default)

class TimeSeriesDB:
    def __init__(self):
        self.client = None
        self.write_api = None

    async def connect(self):
        self.client = InfluxDBClientAsync(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG
        )
        self.write_api = self.client.write_api()
        logger.info(" Connected to InfluxDB Async Client.")

    async def write_telemetry(self, feeder_id: int, data: dict, timestamp=None):
        """ثبت ۵ پارامتر الکتریکی به صورت Point در InfluxDB"""
        point = (
            Point("feeder_telemetry")
            .tag("feeder_id", str(feeder_id))
            .field("active_power", _safe_float(data.get("active_power")))
            .field("reactive_power", _safe_float(data.get("reactive_power")))
            .field("voltage", _safe_float(data.get("voltage")))
            .field("current", _safe_float(data.get("current")))
            .field("power_factor", _safe_float(data.get("power_factor")))
        )
        if timestamp:
            point.time(timestamp)

        await self.write_api.write(
            bucket=settings.INFLUXDB_BUCKET,
            record=point
        )

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info(" InfluxDB Client closed.")

db_client = TimeSeriesDB()
