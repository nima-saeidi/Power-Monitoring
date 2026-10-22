from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from core.config import settings

class InfluxDBManager:
    def __init__(self):
        self._client: InfluxDBClientAsync | None = None

    def get_client(self) -> InfluxDBClientAsync:
        if self._client is None:
            self._client = InfluxDBClientAsync(
                url=settings.INFLUX_URL,
                token=settings.INFLUX_TOKEN,
                org=settings.INFLUX_ORG,
                # Default is 10s; long-range energy queries need more (main_api waits up to 30s).
                timeout=30_000,
            )
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None

influx_manager = InfluxDBManager()


async def get_influx_write_api():
    client = influx_manager.get_client()
    return client.write_api()

