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

    @staticmethod
    def _format_time(dt: datetime) -> str:
        """تبدیل تاریخ به فرمت استاندارد RFC3339 برای InfluxDB"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _get_post_id(record) -> Optional[str]:
        value = record.values.get("post_id")
        return str(value) if value is not None and value != "" else None

    @staticmethod
    def _safe_float(value, default: float = 0.0, precision: int = 2) -> float:
        if value is None:
            return default
        try:
            return round(float(value), precision)
        except (TypeError, ValueError):
            return default

    @staticmethod
    async def write_point(data: TelemetryCreate) -> bool:
        try:
            client = influx_manager.get_client()
            write_api = client.write_api()

            timestamp = data.timestamp if data.timestamp else datetime.now(timezone.utc)

            point = (
                Point("feeder_telemetry")
                .tag("feeder_id", str(data.feeder_id))
                .field("voltage", float(data.voltage))
                .field("current", float(data.current))
                .field("active_power", float(data.active_power))
                .field("reactive_power", float(data.reactive_power))
                .field("power_factor", float(data.power_factor))
                .field("frequency", float(data.frequency if data.frequency is not None else 50.0))
                .time(timestamp)
            )

            if data.post_id is not None:
                point.tag("post_id", str(data.post_id))

            await write_api.write(
                bucket=settings.INFLUX_BUCKET,
                org=settings.INFLUX_ORG,
                record=point,
            )
            return True

        except Exception as exc:
            logger.error("Error writing telemetry to InfluxDB: %s", exc, exc_info=True)
            return False

    @staticmethod
    async def get_latest_by_feeder(feeder_id: int) -> Optional[TelemetryResponse]:
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            # اضافه شدن group() قبل از pivot برای ادغام تمام فیلدها در یک رکورد
            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> group(columns: ["_measurement", "feeder_id"])
              |> pivot(
                  rowKey: ["_time"],
                  columnKey: ["_field"],
                  valueColumn: "_value"
              )
              |> sort(columns: ["_time"], desc: true)
              |> limit(n: 1)
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)

            for table in tables:
                for record in table.records:
                    return TelemetryResponse(
                        feeder_id=feeder_id,
                        post_id=TelemetryRepository._get_post_id(record),
                        voltage=TelemetryRepository._safe_float(record.values.get("voltage")),
                        current=TelemetryRepository._safe_float(record.values.get("current")),
                        active_power=TelemetryRepository._safe_float(record.values.get("active_power")),
                        reactive_power=TelemetryRepository._safe_float(record.values.get("reactive_power")),
                        power_factor=TelemetryRepository._safe_float(record.values.get("power_factor"), default=1.0, precision=3),
                        frequency=TelemetryRepository._safe_float(record.values.get("frequency"), default=50.0),
                        timestamp=record.get_time(),
                    )
            return None

        except Exception as exc:
            logger.error("Error fetching latest telemetry for feeder %s: %s", feeder_id, exc, exc_info=True)
            return None

    @staticmethod
    async def get_range_report(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m",
    ) -> List[TelemetryResponse]:
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_str = TelemetryRepository._format_time(start_time)
            end_str = TelemetryRepository._format_time(end_time)

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: {start_str}, stop: {end_str})
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> aggregateWindow(
                  every: {window_period},
                  fn: mean,
                  timeSrc: "_start",
                  createEmpty: false
              )
              |> group(columns: ["_measurement", "feeder_id"])
              |> pivot(
                  rowKey: ["_time"],
                  columnKey: ["_field"],
                  valueColumn: "_value"
              )
              |> sort(columns: ["_time"])
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)
            results: List[TelemetryResponse] = []

            for table in tables:
                for record in table.records:
                    results.append(
                        TelemetryResponse(
                            feeder_id=feeder_id,
                            post_id=TelemetryRepository._get_post_id(record),
                            voltage=TelemetryRepository._safe_float(record.values.get("voltage")),
                            current=TelemetryRepository._safe_float(record.values.get("current")),
                            active_power=TelemetryRepository._safe_float(record.values.get("active_power")),
                            reactive_power=TelemetryRepository._safe_float(record.values.get("reactive_power")),
                            power_factor=TelemetryRepository._safe_float(record.values.get("power_factor"), default=1.0, precision=3),
                            frequency=TelemetryRepository._safe_float(record.values.get("frequency"), default=50.0),
                            timestamp=record.get_time(),
                        )
                    )
            return results

        except Exception as exc:
            logger.error("Error fetching range report for feeder %s: %s", feeder_id, exc, exc_info=True)
            return []

    @staticmethod
    async def get_chart_data(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m",
    ) -> dict:
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_str = TelemetryRepository._format_time(start_time)
            end_str = TelemetryRepository._format_time(end_time)

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: {start_str}, stop: {end_str})
              |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
              |> filter(fn: (r) => r["feeder_id"] == "{feeder_id}")
              |> aggregateWindow(
                  every: {window_period},
                  fn: mean,
                  timeSrc: "_start",
                  createEmpty: false
              )
              |> sort(columns: ["_time"])
            '''

            tables = await query_api.query(query, org=settings.INFLUX_ORG)
            series = defaultdict(list)

            for table in tables:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    timestamp = record.get_time()

                    if not field or value is None:
                        continue

                    try:
                        numeric_value = round(float(value), 2)
                    except (TypeError, ValueError):
                        continue

                    series[field].append({
                        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                        "value": numeric_value,
                    })

            return {
                "feeder_id": feeder_id,
                "series": dict(series),
            }

        except Exception as exc:
            logger.error("Error fetching chart data for feeder %s: %s", feeder_id, exc, exc_info=True)
            return {
                "feeder_id": feeder_id,
                "series": {},
            }
