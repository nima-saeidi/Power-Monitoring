import math
import random
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ۱. تنظیمات اتصال به InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "super-secret-token-for-power"  # توکن معتبر خود را جایگزین کنید
INFLUX_ORG = "power_org"
INFLUX_BUCKET = "telemetry_bucket"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ۲. تنظیمات بازه زمانی: ۱ سال گذشته
now = datetime.now(timezone.utc)
DAYS = 365
feeder_ids = [1, 2, 3]  # شبیه‌سازی ۳ فیدر مختلف

# گام زمانی: ۱ ساعت (۸۷۶۰ نقطه در سال به ازای هر فیدر)
time_step = timedelta(hours=1)
total_steps = int(timedelta(days=DAYS) / time_step)
start_time = now - timedelta(days=DAYS)

print(f"در حال تولید {total_steps * len(feeder_ids)} رکورد تله‌متری برای بازه ۱ سال گذشته...")

points = []
BATCH_SIZE = 5000  # ارسال دسته‌ای جهت جلوگیری از Timeout

for step in range(total_steps):
    current_time = start_time + (step * time_step)

    # متغیرهای پیوسته برای ایجاد الگوهای فصلی و روزانه
    t = step / 10.0                     # نوسان پایه
    day_of_year = step / 24.0           # پیشروی فصلی
    hour_of_day = (step % 24) / 24.0    # چرخه شبانه‌روزی

    for feeder_id in feeder_ids:
        # فاز متفاوت برای هر فیدر جهت تفکیک در نمودار
        phase_offset = feeder_id * 1.5

        # الگوی فصلی مصرف (زمستان سرد → بار بیشتر، تابستان → بار کمتر)
        seasonal = 0.6 * math.cos(2 * math.pi * day_of_year / 365.0)

        # الگوی شبانه‌روزی (اوج مصرف عصر، کمترین مصرف نیمه‌شب)
        daily = 1.0 + 0.4 * math.sin(2 * math.pi * (hour_of_day - 0.35))

        # شبیه‌سازی ولتاژ: نوسان دور ۲۲۰ ولت (۲۱۵ تا ۲۲۵)
        voltage = 220.0 + 5.0 * math.sin(t + phase_offset) + random.uniform(-1, 1)

        # شبیه‌سازی جریان: بار مصرفی متغیر با الگوی فصلی و روزانه
        current = (15.0 + 8.0 * math.sin(t / 2 + phase_offset)
                   + 6.0 * seasonal * daily + random.uniform(-0.5, 0.5))
        current = max(1.0, current)  # جلوگیری از منفی شدن جریان

        # ضریب توان (Power Factor): بین ۰.۸۰ تا ۰.۹۹
        power_factor = 0.92 + 0.05 * math.cos(t) + random.uniform(-0.02, 0.02)
        power_factor = min(0.99, max(0.80, power_factor))

        # توان ظاهری، اکتیو و راکتیو
        apparent_power = (voltage * current) / 1000.0                       # کیلو ولت-آمپر (kVA)
        active_power = apparent_power * power_factor                        # کیلووات (kW)
        reactive_power = apparent_power * math.sin(math.acos(power_factor)) # کیلووار (kVAR)

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

    # ارسال دسته‌ای در حین تولید (پاک کردن حافظه پس از هر بچ)
    if len(points) >= BATCH_SIZE:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        print(f"✓ ارسال {len(points)} رکورد... (مرحله {step + 1}/{total_steps})")
        points = []

# ارسال داده‌های باقی‌مانده (کمتر از BATCH_SIZE)
if points:
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    print(f"✓ ارسال {len(points)} رکورد نهایی...")

total_records = total_steps * len(feeder_ids)
print(f"\n✓ کامل شد! {total_records} رکورد برای بازه ۱ ساله با موفقیت در InfluxDB ذخیره شد.")

client.close()
