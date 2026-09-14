# test_publisher.py
import pika
import json
from datetime import datetime, timezone

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=pika.PlainCredentials('guest', 'guest') # یا یوزرنیم/پسورد خودتان
    )
)
channel = connection.channel()

payload = {
    "feeder_id": 1,
    "active_power": 25.4,
    "reactive_power": 4.1,
    "voltage": 220.5,
    "current": 12.3,
    "power_factor": 0.98,
    "timestamp": datetime.now(timezone.utc).isoformat()
}

channel.basic_publish(
    exchange='telemetry_exchange',
    routing_key='telemetry.metric',
    body=json.dumps(payload)
)

print("✅ پیام تستی با موفقیت به RabbitMQ ارسال شد.")
connection.close()
