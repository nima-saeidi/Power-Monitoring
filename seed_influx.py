import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ۱. تنظیمات اتصال به InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "SecretPassword123!"  # یا توکن ادمین ساخته‌شده
INFLUX_ORG = "power_org"
INFLUX_BUCKET = "telemetry_bucket"

# داده‌های مدنظر شما (می‌تواند از فایل json خوانده شود یا مستقیم قرار گیرد)
raw_data = [...]  # لیست JSON بالا

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

points = []
for item in raw_data:
    point = (
        Point("feeder_telemetry")
        .tag("feeder_id", str(item["feeder_id"]))
        .field("voltage", float(item["voltage"]))
        .field("current", float(item["current"]))
        .field("active_power", float(item["active_power"]))
        .field("reactive_power", float(item["reactive_power"]))
        .field("power_factor", float(item["power_factor"]))
        .field("frequency", float(item["frequency"]))
        .time(item["timestamp"], WritePrecision.S)
    )

    if item.get("post_id") is not None:
        point.tag("post_id", str(item["post_id"]))

    points.append(point)

# ۲. ارسال دسته‌ای (Batch Write)
write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
print(f"تعداد {len(points)} رکورد با موفقیت در InfluxDB ذخیره شد.")

client.close()
