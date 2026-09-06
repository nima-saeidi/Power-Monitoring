from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client import Point
from core.config import settings

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

    async def write_telemetry(self, feeder_id: int, data: dict, timestamp=None):
        """ثبت ۵ پارامتر الکتریکی به صورت Point در InfluxDB"""
        point = (
            Point("feeder_telemetry")
            .tag("feeder_id", str(feeder_id))
            .field("active_power", float(data.get("active_power", 0.0)))
            .field("reactive_power", float(data.get("reactive_power", 0.0)))
            .field("voltage", float(data.get("voltage", 0.0)))
            .field("current", float(data.get("current", 0.0)))
            .field("power_factor", float(data.get("power_factor", 0.0)))
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

db_client = TimeSeriesDB()
