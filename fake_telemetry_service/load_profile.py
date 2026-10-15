"""Synthetic but plausible feeder readings.

Producers follow a solar curve (zero at night, peak at local noon); consumers
follow a campus load curve (low at night, high during working hours). Current
stays below `max_load_ratio` of the feeder's rated current, which must be
lower than the warning threshold so demo data never raises load alerts.
"""
import math
import random
from datetime import datetime, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=3, minutes=30))  # Asia/Tehran (no DST since 1402)
DEFAULT_RATED_CURRENT = 100.0


def _solar(hour: float) -> float:
    return math.sin(math.pi * (hour - 6.5) / 12.0) if 6.5 < hour < 18.5 else 0.0


def _campus(hour: float, weekday: int) -> float:
    base = 0.3 + 0.7 * max(0.0, math.sin(math.pi * (hour - 6.0) / 14.0)) if 6 < hour < 20 else 0.3
    return base * (0.6 if weekday == 4 else 1.0)  # Friday is quieter


def sample(ts: datetime, feeder_id: int, rated_current, role, max_load_ratio: float = 0.35) -> dict:
    rated = float(rated_current) if rated_current and rated_current > 0 else DEFAULT_RATED_CURRENT
    local = ts.astimezone(LOCAL_TZ)
    hour = local.hour + local.minute / 60 + local.second / 3600
    day_factor = 0.85 + 0.15 * math.sin(local.toordinal() * 1.7 + feeder_id)

    if role == "producer":
        shape = _solar(hour)
        floor = 0.005
    else:
        shape = _campus(hour, local.weekday())
        floor = 0.1

    peak = 0.92 * max_load_ratio
    ratio = max(floor * max_load_ratio, peak * shape * day_factor * (1 + random.uniform(-0.04, 0.04)))
    current = min(rated * ratio + random.uniform(0, 0.4), rated * max_load_ratio)

    voltage = 230.0 + 3.0 * math.sin(hour / 24 * 2 * math.pi + feeder_id) + random.uniform(-1.2, 1.2)
    pf = 0.97 if role == "producer" else 0.91
    pf = min(0.99, max(0.8, pf + random.uniform(-0.015, 0.015) - (0.06 if shape < 0.1 else 0.0)))
    apparent_kva = voltage * current / 1000.0
    return {
        "active_power": round(apparent_kva * pf, 3),
        "reactive_power": round(apparent_kva * math.sin(math.acos(pf)), 3),
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "power_factor": round(pf, 3),
    }
