# main_api/core/rabbitmq.py
"""
این ماژول قبلاً یک نسخه‌ی دوم و مستقل از RabbitMQPublisher را تعریف می‌کرد که
هرگز در lifespan برنامه به RabbitMQ متصل نمی‌شد (چون فقط message_broker موجود
در core.broker در main.py متصل می‌شود). در نتیجه هر بخشی از پروژه که از این
ماژول استفاده می‌کرد (مثلاً settings/router.py) با یک اتصال مرده کار می‌کرد و
رویدادهایش عملاً هیچ‌وقت منتشر نمی‌شد.

برای رفع این باگ، این ماژول اکنون صرفاً از core.broker بازصادر (re-export)
می‌کند تا کل پروژه از یک نمونه‌ی واحد و متصلِ RabbitMQPublisher استفاده کند.
"""

from main_api.core.broker import (
    RabbitMQPublisher,
    MessageBroker,
    message_broker,
    get_rabbitmq_publisher,
    send_log_to_rabbitmq,
)

__all__ = [
    "RabbitMQPublisher",
    "MessageBroker",
    "message_broker",
    "get_rabbitmq_publisher",
    "send_log_to_rabbitmq",
]
