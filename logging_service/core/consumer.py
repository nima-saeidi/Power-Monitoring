import json
import asyncio
import aio_pika
from core.config import settings

RABBITMQ_URL = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


async def process_audit_message(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        print(f" [x] Received Audit Event: {data}")

        # ذخیره در دیتابیس (MongoDB / PostgreSQL)
        # await db.audit_logs.insert_one(data)


async def start_consumer():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue("audit_logs", durable=True)
    await queue.consume(process_audit_message)
    print(" [*] RabbitMQ Consumer started. Waiting for logs...")
