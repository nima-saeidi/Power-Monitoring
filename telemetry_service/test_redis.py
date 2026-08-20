import asyncio
import redis.asyncio as redis


async def monitor_redis():
    # اتصال به ردیس با تنظیمات سازگار (پروتکل ۲)
    r = redis.Redis(host='127.0.0.1', port=6379, db=0, protocol=2)
    pubsub = r.pubsub()

    # گوش دادن به تمامی کانال‌ها
    await pubsub.psubscribe('*')
    print("🟢 Listening for Redis messages... (Press Ctrl+C to stop)")

    try:
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                print(f"📥 New Data on channel '{message['channel'].decode()}': {message['data'].decode()}")
    except Exception as e:
        print(f"🔴 Error: {e}")


if __name__ == "__main__":
    asyncio.run(monitor_redis())
