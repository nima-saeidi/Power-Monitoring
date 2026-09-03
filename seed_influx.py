import datetime
import math
import random
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ----------------- تنظیمات استخراج شده از docker-compose -----------------
INFLUX_URL = "http://localhost:8086"  # از روی سیستم لوکال
TOKEN = "super-secret-token-for-power"
ORG = "power_org"
BUCKET = "telemetry_bucket"

# ----------------- تنظیمات بازه زمانی -----------------
END_TIME = datetime.datetime.now(datetime.timezone.utc)
START_TIME = END_TIME - datetime.timedelta(days=365)  # بازه یک ساله
STEP_MINUTES = 5  # هر ۵ دقیقه یک نمونه
BATCH_SIZE = 5000

# نام فیدرها بر اساس ساختار پروژه
FEEDERS = [
    "Feeder_Main",
    "Feeder_Production_1",
    "Feeder_Production_2",
    "Feeder_HVAC",
]


def generate_point(timestamp, feeder_id):
    hour = timestamp.hour
    is_peak = 8 <= hour <= 18
    load_factor = 1.6 if is_peak else 0.7
    noise = random.uniform(0.92, 1.08)

    voltage = round(220 + random.uniform(-6, 6), 2)
    current = round(random.uniform(15, 45) * load_factor * noise, 2)
    power_factor = round(random.uniform(0.86, 0.97), 2)
    active_power = round((voltage * current * power_factor) / 1000.0, 2)
    reactive_power = round(
        (voltage * current * math.sqrt(1 - power_factor**2)) / 1000.0, 2
    )
    frequency = round(50 + random.uniform(-0.12, 0.12), 2)

    return (
        Point("electrical_measurements")
        .tag("feeder_id", feeder_id)
        .tag("device_type", "power_meter")
        .field("voltage", float(voltage))
        .field("current", float(current))
        .field("active_power", float(active_power))
        .field("reactive_power", float(reactive_power))
        .field("power_factor", float(power_factor))
        .field("frequency", float(frequency))
        .time(timestamp, WritePrecision.S)
    )


def main():
    print(f"⏳ در حال اتصال به InfluxDB ({INFLUX_URL})...")
    client = InfluxDBClient(url=INFLUX_URL, token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    current_time = START_TIME
    batch = []
    total_written = 0

    print("🚀 شروع فرآیند تزریق دیتای ساختگی ۱ ساله...")
    while current_time <= END_TIME:
        for feeder in FEEDERS:
            batch.append(generate_point(current_time, feeder))

            if len(batch) >= BATCH_SIZE:
                write_api.write(bucket=BUCKET, record=batch)
                total_written += len(batch)
                print(
                    f"✓ تعداد {total_written:,} رکورد تا تاریخ {current_time.strftime('%Y-%m-%d %H:%M')} تزریق شد."
                )
                batch.clear()

        current_time += datetime.timedelta(minutes=STEP_MINUTES)

    if batch:
        write_api.write(bucket=BUCKET, record=batch)
        total_written += len(batch)

    print(f"\n✅ عملیات با موفقیت پایان یافت! مجموع کل رکوردها: {total_written:,}")
    client.close()


if __name__ == "__main__":
    main()
