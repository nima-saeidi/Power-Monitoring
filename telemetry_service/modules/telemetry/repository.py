import logging
from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from influxdb_client import Point
from core.config import settings
from core.database import influx_manager
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse

logger = logging.getLogger(__name__)


class TelemetryRepository:
    """مسئول خواندن و نوشتن مستقیم روی InfluxDB با زبان Flux"""

    @staticmethod
    async def write_point(data: TelemetryCreate) -> bool:
        """نوشتن نقطه داده تله‌متری در InfluxDB"""
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
                .field("reactive_power", float(data.reactive_power))
                .field("power_factor", float(data.power_factor))
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
            logger.error(f"Error writing telemetry to InfluxDB: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_latest_by_feeder(feeder_id: int) -> Optional[TelemetryResponse]:
        """دریافت آخرین مقدار ثبت‌شده یک فیدر"""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            # کوئری Flux برای دریافت آخرین رکورد در ۳۰ روز گذشته
            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> last()
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)

            for table in tables:
                for record in table.records:
                    return TelemetryResponse(
                        feeder_id=int(record.values.get("feeder_id", feeder_id)),
                        post_id=int(record.values.get("post_id")) if record.values.get("post_id") else None,
                        voltage=record.values.get("voltage", 0.0),
                        current=record.values.get("current", 0.0),
                        active_power=record.values.get("active_power", 0.0),
                        reactive_power=record.values.get("reactive_power", 0.0),
                        power_factor=record.values.get("power_factor", 1.0),
                        frequency=record.values.get("frequency", 50.0),
                        timestamp=record.get_time()
                    )
            return None
        except Exception as e:
            logger.error(f"Error fetching latest telemetry for feeder {feeder_id}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_range_report(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m"
    ) -> List[TelemetryResponse]:
        """دریافت گزارش بازه زمانی با میانگین‌گیری دوره‌ای (Aggregate Window)"""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: {start_iso}, stop: {end_iso})
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)
              |> yield(name: "mean")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)
            results: List[TelemetryResponse] = []

            for table in tables:
                for record in table.records:
                    def safe_round(key: str, default: float, precision: int = 2):
                        val = record.values.get(key)
                        if val is None:
                            return default
                        return round(float(val), precision)

                    results.append(
                        TelemetryResponse(
                            feeder_id=feeder_id,
                            post_id=int(record.values.get("post_id")) if record.values.get("post_id") is not None else None,
                            voltage=safe_round("voltage", 0.0, 2),
                            current=safe_round("current", 0.0, 2),
                            active_power=safe_round("active_power", 0.0, 2),
                            reactive_power=safe_round("reactive_power", 0.0, 2),
                            power_factor=safe_round("power_factor", 1.0, 3),
                            frequency=safe_round("frequency", 50.0, 2),
                            timestamp=record.get_time()
                        )
                    )
            return results
        except Exception as e:
            logger.error(f"Error fetching range report for feeder {feeder_id}: {e}", exc_info=True)
            return []

    @staticmethod
    async def get_chart_data(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m"
    ) -> dict:
        """دریافت داده‌های بازه زمانی برای نمودار به صورت آرایه‌ای از اشياء (timestamp, value) برای هر پارامتر"""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()

            # کوئری بدون pivot تا داده‌ها به صورت فیلد به فیلد پیمایش شوند
            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: {start_iso}, stop: {end_iso})
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)
              |> yield(name: "mean")
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)
            series = defaultdict(list)

            for table in tables:
                for record in table.records:
                    field = record.get_field()
                    val = record.get_value()
                    ts = record.get_time()

                    if field and val is not None:
                        series[field].append({
                            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                            "value": round(float(val), 2)
                        })

            return {
                "feeder_id": feeder_id,
                "series": dict(series)
            }
        except Exception as e:
            logger.error(f"Error fetching chart data for feeder {feeder_id}: {e}", exc_info=True)
            return {
                "feeder_id": feeder_id,
                "series": {}
            }
