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
    def _get_post_id(record) -> Optional[str]:
        """
        post_id به‌صورت tag ذخیره می‌شود و می‌تواند مانند POST_1 باشد.
        """
        value = record.values.get("post_id")

        if value is None or value == "":
            return None

        return str(value)

    @staticmethod
    def _safe_float(
        value,
        default: float = 0.0,
        precision: int = 2,
    ) -> float:
        """تبدیل امن مقدار به float."""
        if value is None:
            return default

        try:
            return round(float(value), precision)
        except (TypeError, ValueError):
            return default

    @staticmethod
    async def write_point(data: TelemetryCreate) -> bool:
        """نوشتن یک نقطه تله‌متری در InfluxDB."""
        try:
            client = influx_manager.get_client()
            write_api = client.write_api()

            timestamp = (
                data.timestamp
                if data.timestamp
                else datetime.now(timezone.utc)
            )

            point = (
                Point("feeder_telemetry")
                .tag("feeder_id", str(data.feeder_id))
                .field("voltage", float(data.voltage))
                .field("current", float(data.current))
                .field("active_power", float(data.active_power))
                .field("reactive_power", float(data.reactive_power))
                .field("power_factor", float(data.power_factor))
                .field(
                    "frequency",
                    float(
                        data.frequency
                        if data.frequency is not None
                        else 50.0
                    ),
                )
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
            logger.error(
                "Error writing telemetry to InfluxDB: %s",
                exc,
                exc_info=True,
            )
            return False

    @staticmethod
    async def get_latest_by_feeder(
        feeder_id: int,
    ) -> Optional[TelemetryResponse]:
        """دریافت آخرین رکورد ثبت‌شده برای یک فیدر."""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: -30d)
              |> filter(fn: (r) =>
                  r["_measurement"] == "feeder_telemetry"
              )
              |> filter(fn: (r) =>
                  r["feeder_id"] == "{feeder_id}"
              )
              |> pivot(
                  rowKey: ["_time"],
                  columnKey: ["_field"],
                  valueColumn: "_value"
              )
              |> sort(columns: ["_time"], desc: true)
              |> limit(n: 1)
            '''

            tables = await query_api.query(
                query,
                org=settings.INFLUX_ORG,
            )

            for table in tables:
                for record in table.records:
                    return TelemetryResponse(
                        feeder_id=feeder_id,
                        post_id=TelemetryRepository._get_post_id(record),
                        voltage=TelemetryRepository._safe_float(
                            record.values.get("voltage"),
                            default=0.0,
                            precision=2,
                        ),
                        current=TelemetryRepository._safe_float(
                            record.values.get("current"),
                            default=0.0,
                            precision=2,
                        ),
                        active_power=TelemetryRepository._safe_float(
                            record.values.get("active_power"),
                            default=0.0,
                            precision=2,
                        ),
                        reactive_power=TelemetryRepository._safe_float(
                            record.values.get("reactive_power"),
                            default=0.0,
                            precision=2,
                        ),
                        power_factor=TelemetryRepository._safe_float(
                            record.values.get("power_factor"),
                            default=1.0,
                            precision=3,
                        ),
                        frequency=TelemetryRepository._safe_float(
                            record.values.get("frequency"),
                            default=50.0,
                            precision=2,
                        ),
                        timestamp=record.get_time(),
                    )

            return None

        except Exception as exc:
            logger.error(
                "Error fetching latest telemetry for feeder %s: %s",
                feeder_id,
                exc,
                exc_info=True,
            )
            return None

    @staticmethod
    async def get_range_report(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m",
    ) -> List[TelemetryResponse]:
        """دریافت گزارش بازه زمانی با میانگین‌گیری دوره‌ای."""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(
                  start: time(v: "{start_iso}"),
                  stop: time(v: "{end_iso}")
              )
              |> filter(fn: (r) =>
                  r["_measurement"] == "feeder_telemetry"
              )
              |> filter(fn: (r) =>
                  r["feeder_id"] == "{feeder_id}"
              )
              |> aggregateWindow(
                  every: {window_period},
                  fn: mean,
                  createEmpty: false
              )
              |> pivot(
                  rowKey: ["_time"],
                  columnKey: ["_field"],
                  valueColumn: "_value"
              )
              |> sort(columns: ["_time"])
            '''

            tables = await query_api.query(
                query,
                org=settings.INFLUX_ORG,
            )

            results: List[TelemetryResponse] = []

            for table in tables:
                for record in table.records:
                    results.append(
                        TelemetryResponse(
                            feeder_id=feeder_id,
                            post_id=TelemetryRepository._get_post_id(record),
                            voltage=TelemetryRepository._safe_float(
                                record.values.get("voltage"),
                                0.0,
                                2,
                            ),
                            current=TelemetryRepository._safe_float(
                                record.values.get("current"),
                                0.0,
                                2,
                            ),
                            active_power=TelemetryRepository._safe_float(
                                record.values.get("active_power"),
                                0.0,
                                2,
                            ),
                            reactive_power=TelemetryRepository._safe_float(
                                record.values.get("reactive_power"),
                                0.0,
                                2,
                            ),
                            power_factor=TelemetryRepository._safe_float(
                                record.values.get("power_factor"),
                                1.0,
                                3,
                            ),
                            frequency=TelemetryRepository._safe_float(
                                record.values.get("frequency"),
                                50.0,
                                2,
                            ),
                            timestamp=record.get_time(),
                        )
                    )

            return results

        except Exception as exc:
            logger.error(
                "Error fetching range report for feeder %s: %s",
                feeder_id,
                exc,
                exc_info=True,
            )
            return []

    @staticmethod
    async def get_chart_data(
        feeder_id: int,
        start_time: datetime,
        end_time: datetime,
        window_period: str = "1m",
    ) -> dict:
        """دریافت داده‌های نمودار به‌صورت سری جداگانه برای هر field."""
        try:
            client = influx_manager.get_client()
            query_api = client.query_api()

            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()

            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(
                  start: time(v: "{start_iso}"),
                  stop: time(v: "{end_iso}")
              )
              |> filter(fn: (r) =>
                  r["_measurement"] == "feeder_telemetry"
              )
              |> filter(fn: (r) =>
                  r["feeder_id"] == "{feeder_id}"
              )
              |> aggregateWindow(
                  every: {window_period},
                  fn: mean,
                  createEmpty: false
              )
              |> sort(columns: ["_time"])
            '''

            tables = await query_api.query(
                query,
                org=settings.INFLUX_ORG,
            )

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
                        logger.warning(
                            "Skipping non-numeric value for field %s: %r",
                            field,
                            value,
                        )
                        continue

                    series[field].append(
                        {
                            "timestamp": (
                                timestamp.isoformat()
                                if hasattr(timestamp, "isoformat")
                                else str(timestamp)
                            ),
                            "value": numeric_value,
                        }
                    )

            return {
                "feeder_id": feeder_id,
                "series": dict(series),
            }

        except Exception as exc:
            logger.error(
                "Error fetching chart data for feeder %s: %s",
                feeder_id,
                exc,
                exc_info=True,
            )

            return {
                "feeder_id": feeder_id,
                "series": {},
            }
