import math
import random
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "super-secret-token-for-power"
INFLUX_ORG = "power_org"
INFLUX_BUCKET = "telemetry_bucket"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

now = datetime.now(timezone.utc)
DAYS = 365
feeder_ids = [1, 2, 3]

time_step = timedelta(hours=1)
total_steps = int(timedelta(days=DAYS) / time_step)
start_time = now - timedelta(days=DAYS)

print(f"در حال تولید {total_steps * len(feeder_ids)} رکورد تله‌متری برای بازه ۱ سال گذشته...")

points = []
BATCH_SIZE = 5000

for step in range(total_steps):
    current_time = start_time + (step * time_step)

    t = step / 10.0
    day_of_year = step / 24.0
    hour_of_day = (step % 24) / 24.0

    for feeder_id in feeder_ids:
        phase_offset = feeder_id * 1.5

        seasonal = 0.6 * math.cos(2 * math.pi * day_of_year / 365.0)

        daily = 1.0 + 0.4 * math.sin(2 * math.pi * (hour_of_day - 0.35))

        voltage = 220.0 + 5.0 * math.sin(t + phase_offset) + random.uniform(-1, 1)

        current = (15.0 + 8.0 * math.sin(t / 2 + phase_offset)
                   + 6.0 * seasonal * daily + random.uniform(-0.5, 0.5))
        current = max(1.0, current)

        power_factor = 0.92 + 0.05 * math.cos(t) + random.uniform(-0.02, 0.02)
        power_factor = min(0.99, max(0.80, power_factor))

        apparent_power = (voltage * current) / 1000.0
        active_power = apparent_power * power_factor
        reactive_power = apparent_power * math.sin(math.acos(power_factor))

        frequency = 50.0 + 0.1 * math.sin(t * 3) + random.uniform(-0.05, 0.05)

        point = (
            Point("feeder_telemetry")
            .tag("feeder_id", str(feeder_id))
            .tag("post_id", f"POST_{(feeder_id % 2) + 1}")
            .field("voltage", round(voltage, 2))
            .field("current", round(current, 2))
            .field("active_power", round(active_power, 3))
            .field("reactive_power", round(reactive_power, 3))
            .field("power_factor", round(power_factor, 3))
            .field("frequency", round(frequency, 2))
            .time(current_time, WritePrecision.S)
        )
        points.append(point)

    if len(points) >= BATCH_SIZE:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        print(f"✓ ارسال {len(points)} رکورد... (مرحله {step + 1}/{total_steps})")
        points = []

if points:
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    print(f"✓ ارسال {len(points)} رکورد نهایی...")

total_records = total_steps * len(feeder_ids)
print(f"\n✓ کامل شد! {total_records} رکورد برای بازه ۱ ساله با موفقیت در InfluxDB ذخیره شد.")

client.close()
