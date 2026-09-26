"""
محاسبات تحلیلی روی داده‌های InfluxDB: انرژی (انتگرال توان) و پیش‌بینی ساعتی توان.

واحدها: توان در InfluxDB به همان واحدی ذخیره می‌شود که دستگاه می‌دهد (پیش‌فرض kW / kVAR)،
پس انرژی خروجی kWh / kVARh است.
"""
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from core.config import settings
from core.database import influx_manager

logger = logging.getLogger(__name__)

ENERGY_FIELDS = ("active_power", "reactive_power")
# منطقه‌ی زمانی برای الگوی ساعتی مصرف (ساعت ۸ صبح تهران، نه UTC)
LOCAL_TZ = ZoneInfo(os.getenv("TZ") or "Asia/Tehran")


def flux_location() -> str:
    """
    پنجره‌های ساعتی/روزانه‌ی Flux باید با ساعت محلی هم‌تراز باشند؛ تهران UTC+3:30 است و بدون این،
    هر پنجره‌ی ساعتی نیمی از دو ساعت محلی را مخلوط و پنجره‌ی روزانه ساعت ۳:۳۰ بامداد قطع می‌شد.
    آفست فعلی در پایتون (tzdata) حساب می‌شود، چون InfluxDB ممکن است پایگاه منطقه‌ی زمانی نداشته باشد.
    """
    minutes = int(datetime.now(LOCAL_TZ).utcoffset().total_seconds() // 60)
    return f"timezone.fixed(offset: {minutes}m)"


def _feeder_filter(feeder_ids: List[int]) -> str:
    ids = ", ".join(f'"{int(fid)}"' for fid in feeder_ids)
    return f'filter(fn: (r) => contains(value: r["feeder_id"], set: [{ids}]))'


async def get_energy(
        feeder_ids: List[int], start_time: datetime, end_time: datetime, window: Optional[str] = None
) -> Dict[int, dict]:
    """
    انرژی اکتیو (kWh) و راکتیو (kVARh) هر فیدر در بازه = انتگرال توان بر حسب ساعت.
    با window (مثلاً 1h یا 1d) سری زمانی انرژی هر بازه هم برگردانده می‌شود.
    """
    fields = ", ".join(f'"{f}"' for f in ENERGY_FIELDS)
    base = f'''
    import "timezone"
    from(bucket: "{settings.INFLUX_BUCKET}")
      |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
      |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
      |> {_feeder_filter(feeder_ids)}
      |> filter(fn: (r) => contains(value: r["_field"], set: [{fields}]))
    '''
    query_api = influx_manager.get_client().query_api()
    result: Dict[int, dict] = {
        int(fid): {"feeder_id": int(fid), "active_energy_kwh": 0.0, "reactive_energy_kvarh": 0.0, "series": []}
        for fid in feeder_ids
    }
    key_of = {"active_power": "active_energy_kwh", "reactive_power": "reactive_energy_kvarh"}

    totals = await query_api.query(base + "|> integral(unit: 1h)", org=settings.INFLUX_ORG)
    for table in totals:
        for record in table.records:
            fid = int(record.values["feeder_id"])
            result[fid][key_of[record.get_field()]] = round(float(record.get_value() or 0.0), 3)

    if window:
        series_query = base + f'''
          |> aggregateWindow(every: {window}, fn: (column, tables=<-) => tables |> integral(unit: 1h, column: column),
                             createEmpty: false, location: {flux_location()})
        '''
        buckets: Dict[int, Dict[str, dict]] = defaultdict(dict)
        for table in await query_api.query(series_query, org=settings.INFLUX_ORG):
            for record in table.records:
                fid = int(record.values["feeder_id"])
                ts = record.get_time().isoformat()
                point = buckets[fid].setdefault(ts, {"timestamp": ts, "active_energy_kwh": 0.0, "reactive_energy_kvarh": 0.0})
                point[key_of[record.get_field()]] = round(float(record.get_value() or 0.0), 3)
        for fid, points in buckets.items():
            result[fid]["series"] = sorted(points.values(), key=lambda p: p["timestamp"])
    return result


async def get_forecast(feeder_id: int, hours: int = 24, history_days: int = 7) -> dict:
    """
    پیش‌بینی ساعتی توان اکتیو و راکتیو برای «hours» ساعت آینده با روش میانگین فصلی ساعتی:
    مقدار هر ساعت = میانگین همان ساعت از شبانه‌روز در «history_days» روز گذشته.
    (مصرف برق دانشگاه الگوی روزانه‌ی تکرارشونده دارد؛ اگر بعداً API پیش‌بینی خارجی در دسترس
    قرار گرفت، فقط همین تابع جایگزین می‌شود و قرارداد خروجی ثابت می‌ماند.)
    """
    fields = ", ".join(f'"{f}"' for f in ENERGY_FIELDS)
    query = f'''
    import "timezone"
    from(bucket: "{settings.INFLUX_BUCKET}")
      |> range(start: -{int(history_days)}d)
      |> filter(fn: (r) => r["_measurement"] == "feeder_telemetry")
      |> filter(fn: (r) => r["feeder_id"] == "{int(feeder_id)}")
      |> filter(fn: (r) => contains(value: r["_field"], set: [{fields}]))
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false, timeSrc: "_start", location: {flux_location()})
    '''
    profile: Dict[str, Dict[int, List[float]]] = {f: defaultdict(list) for f in ENERGY_FIELDS}
    for table in await influx_manager.get_client().query_api().query(query, org=settings.INFLUX_ORG):
        for record in table.records:
            value = record.get_value()
            if value is None:
                continue
            # timeSrc: "_start" -> زمان هر رکورد شروع پنجره است (پنجره‌ی ناقص ساعت جاری هم درست حساب می‌شود)
            hour = record.get_time().astimezone(LOCAL_TZ).hour
            profile[record.get_field()][hour].append(float(value))

    next_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    points = []
    for i in range(hours):
        ts = next_hour + timedelta(hours=i)
        hour = ts.astimezone(LOCAL_TZ).hour
        point = {"timestamp": ts.isoformat(), "samples": len(profile["active_power"].get(hour, []))}
        for field in ENERGY_FIELDS:
            values = profile[field].get(hour)
            point[field] = round(sum(values) / len(values), 3) if values else None
        points.append(point)

    return {
        "feeder_id": feeder_id,
        "method": "seasonal_hourly_average",
        "history_days": history_days,
        "points": points,
    }
