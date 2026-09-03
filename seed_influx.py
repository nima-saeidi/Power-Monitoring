import math
import random
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ۱. تنظیمات اتصال به InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "SecretPassword123!"  # در صورت نیاز توکن واقعی را جایگزین کنید
INFLUX_ORG = "power_org"
INFLUX_BUCKET = "telemetry_bucket"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ۲. تولید دیتای سری‌زمانی پویا و پیوسته
points = []
now = datetime.now(timezone.utc)
feeder_ids = [1, 2, 3]  # شبیه‌سازی ۳ فیدر مختلف

# تولید داده برای ۲۴ ساعت گذشته با گام‌های ۵ دقیقه‌ای (۲۸۸ نقطه برای هر فیدر)
total_steps = 288
time_step = timedelta(minutes=5)
start_time = now - (total_steps * time_step)

print("در حال ساخت داده‌های شبیه‌سازی‌شده...")

for step in range(total_steps):
    current_time = start_time + (step * time_step)
    t = step / 10.0  # متغیر پیوسته برای ایجاد موج سینوسی

    for feeder_id in feeder_ids:
        # فاز متفاوت برای هر فیدر جهت تفکیک در نمودار
        phase_offset = feeder_id * 1.5

        # شبیه‌سازی ولتاژ: نوسان دور ۲۲۰ ولت (۲۱۵ تا ۲۲۵)
        voltage = 220.0 + 5.0 * math.sin(t + phase_offset) + random.uniform(-1, 1)

        # شبیه‌سازی جریان: الگوی بار مصرفی با نوسان
        current = 15.0 + 8.0 * math.sin(t / 2 + phase_offset) + random.uniform(-0.5, 0.5)
        current = max(1.0, current)  # جلوگیری از منفی شدن جریان

        # ضریب توان (Power Factor): بین ۰.۸۵ تا ۰.۹۸
        power_factor = 0.92 + 0.05 * math.cos(t) + random.uniform(-0.02, 0.02)
        power_factor = min(0.99, max(0.80, power_factor))

        # توان ظاهری، اکتیو و راکتیو
        apparent_power = (voltage * current) / 1000.0  # کیلو ولت-آمپر (kVA)
        active_power = apparent_power * power_factor   # کیلووات (kW)
        reactive_power = apparent_power * math.sin(math.acos(power_factor))  # کیلووار (kVAR)

        # فرکانس: نوسان ریز دور ۵۰ هرتز (۴۹.۸ تا ۵۰.۲)
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

# ۳. ارسال دسته‌ای (Batch Write) به InfluxDB
print(f"در حال ارسال {len(points)} رکورد به InfluxDB...")
write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
print(f"✓ تعداد {len(points)} رکورد برای بازه ۲۴ ساعت گذشته با موفقیت ذخیره شد.")

client.close()
