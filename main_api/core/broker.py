import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from main_api.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """کلاس مدیریت اتصال و انتشار رویدادها به RabbitMQ از طریق Topic Exchange"""
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None
        # کش صف‌هایی که با موفقیت declare شده‌اند تا publish_to_queue مجبور به
        # declare مجدد صف در هر بار فراخوانی نباشد (چون آرگومان‌های DLX تغییری
        # نمی‌کنند، یک بار declare کافی است).
        self._declared_queues: set = set()

    @property
    def is_connected(self) -> bool:
        """بررسی فعال بودن اتصال برای Health Check"""
        return bool(
            self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    async def connect(self):
        """برقراری اتصال پایدار به RabbitMQ و راه‌اندازی Topic Exchange"""
        rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            # تنظیم prefetch_count برای بهبود کارایی worker-ها
            await self.channel.set_qos(prefetch_count=10)
            self._declared_queues = set()

            # تعریف Topic Exchange اصلی برای مسیریابی رویدادها
            self.exchange = await self.channel.declare_exchange(
                name="power_monitoring_events",
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("✅ Successfully connected to RabbitMQ and declared Topic Exchange 'power_monitoring_events'.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            self.exchange = None

    async def close(self):
        """قطع ایمن اتصال در زمان خاموش شدن برنامه"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish_event(self, routing_key: str, message: Dict[str, Any]):
        """
        متد اصلی برای انتشار رویدادها به Topic Exchange.
        تمام سرویس‌ها باید از این متد استفاده کنند.
        """
        if not self.exchange or not self.is_connected:
            logger.warning(f"RabbitMQ is not connected. Cannot publish event to routing_key '{routing_key}'.")
            # در یک سناریوی واقعی، می‌توان پیام را در یک صف موقت ذخیره و بعداً ارسال کرد
            return

        try:
            body = json.dumps(message, default=str).encode("utf-8")
            pika_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT, # ذخیره پیام روی دیسک تا زمان تحویل
                content_type="application/json"
            )
            await self.exchange.publish(pika_message, routing_key=routing_key)
            logger.debug(f"Event published to exchange 'power_monitoring_events' with routing_key: '{routing_key}'")
        except Exception as e:
            logger.error(f"Error publishing event with routing_key '{routing_key}': {e}")

    async def publish_to_queue(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        انتشار مستقیم یک پیام به یک صف با نام مشخص (روی Default Exchange)، با
        استفاده از همان کانکشن/کانال پایدار سراسری که در startup برنامه یک‌بار
        باز شده است.

        بهینه‌سازی مهم: قبلاً هر بار که این نوع پیام (لاگ/نوتیفیکیشن) ارسال
        می‌شد، یک کانکشن AMQP کاملاً جدید باز و بسته می‌شد (هندشیک کامل
        TCP+AMQP به‌ازای هر پیام) که زیر بار سنگین یا با چند replica از main_api
        هم روی تأخیر هر درخواست اثر می‌گذاشت و هم مصرف منابع RabbitMQ را بالا
        می‌برد. حالا از کانکشن پایدار موجود استفاده می‌شود.

        صف مقصد با آرگومان Dead-Letter-Exchange declare می‌شود تا اگر مصرف‌کننده
        (logging_service/notification_service) در پردازش یک پیام با خطا مواجه
        شود، پیام به‌جای گم شدن کامل، به صف DLQ منتقج و قابل بررسی/reprocess شود.
        این آرگومان‌ها باید دقیقاً با آرگومان declare سمت مصرف‌کننده یکسان باشند
        (وگرنه RabbitMQ خطای PRECONDITION_FAILED می‌دهد)، به همین دلیل نام‌گذاری
        DLX/DLQ بر اساس یک قرارداد ثابت (f"{queue_name}.dlx" / ".dlq") در همه‌ی
        سرویس‌ها تکرار شده است.
        """
        if not self.is_connected:
            logger.warning(f"RabbitMQ is not connected. Cannot publish to queue '{queue_name}'.")
            return False

        try:
            if queue_name not in self._declared_queues:
                await self._ensure_queue_with_dlq(queue_name)

            body = json.dumps(message, default=str).encode("utf-8")
            pika_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await self.channel.default_exchange.publish(pika_message, routing_key=queue_name)
            return True
        except Exception as e:
            logger.error(f"Error publishing to queue '{queue_name}': {e}")
            return False

    async def _ensure_queue_with_dlq(self, queue_name: str) -> None:
        """
        Declare صف با x-dead-letter-exchange. اگر صف از قبل (قبل از این تغییر)
        با آرگومان‌های متفاوت وجود داشته باشد، AMQP با PRECONDITION_FAILED
        کانال جاری (self.channel) را می‌بندد. چون self.channel/self.exchange
        سراسری و مشترک بین همه‌ی متدهای این کلاس هستند (از جمله publish_event
        که برای رویدادهای CQRS استفاده می‌شود)، این خطا را می‌گیریم و یک کانال
        تازه باز کرده و Topic Exchange اصلی را دوباره declare می‌کنیم تا بقیه‌ی
        عملکرد publisher سالم بماند؛ فقط برای این صف خاص بدون DLQ ادامه می‌دهیم
        (تا زمانی که صف قدیمی یک‌بار به‌صورت دستی حذف شود).
        """
        dlx_name = f"{queue_name}.dlx"
        dlq_name = f"{queue_name}.dlq"
        try:
            dlx_exchange = await self.channel.declare_exchange(dlx_name, aio_pika.ExchangeType.FANOUT, durable=True)
            dlq = await self.channel.declare_queue(dlq_name, durable=True)
            await dlq.bind(dlx_exchange)
            await self.channel.declare_queue(
                queue_name, durable=True, arguments={"x-dead-letter-exchange": dlx_name}
            )
            self._declared_queues.add(queue_name)
        except aio_pika.exceptions.ChannelClosed:
            logger.warning(
                f"Queue '{queue_name}' already exists with incompatible arguments. "
                "Falling back WITHOUT dead-letter support for it; delete the queue manually once to enable DLQ."
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            self.exchange = await self.channel.declare_exchange(
                name="power_monitoring_events", type=aio_pika.ExchangeType.TOPIC, durable=True
            )
            await self.channel.declare_queue(queue_name, durable=True)
            self._declared_queues.add(queue_name)


# نمونه سراسری بروکر
message_broker = RabbitMQPublisher()

# نام مستعار جهت سازگاری
MessageBroker = RabbitMQPublisher


def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """تابع وابستگی (Dependency Injection) برای استفاده در FastAPI"""
    return message_broker


NOTIFICATION_QUEUE_NAME = "notification_events"


async def send_notification_to_queue(
    title: str,
    message: str,
    html_message: Optional[str] = None,
    channel: str = "email",
    email_addresses: Optional[list] = None,
    phone_numbers: Optional[list] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    انتشار مستقیم یک پیام نوتیفیکیشن (ایمیل/پیامک) به صف notification_events.
    ارسال واقعی (SMTP/SMS) توسط notification_service که این صف را Consume می‌کند
    انجام می‌شود؛ main_api صرفاً پیام را منتشر می‌کند.

    از کانکشن پایدار سراسری (message_broker) استفاده می‌شود نه یک کانکشن AMQP
    جدید به‌ازای هر پیام (نگاه کنید به توضیح publish_to_queue).
    """
    message_body = {
        "channel": channel,
        "title": title,
        "message": message,
        "html_message": html_message,
        "email_addresses": email_addresses or [],
        "phone_numbers": phone_numbers or [],
        "priority": priority,
        "metadata": metadata or {},
    }

    success = await message_broker.publish_to_queue(NOTIFICATION_QUEUE_NAME, message_body)
    if not success:
        logger.error(f"Failed to publish '{title}' notification to RabbitMQ.")


async def send_log_to_rabbitmq(
    level: str,
    message: str,
    service: str = "main_api",
    extra_data: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    ارسال لاگ‌های سیستمی (رویدادهای عمومی، خطاها و ...) به سرویس لاگ.

    توجه: این تابع دیگر مستقیماً به Topic Exchange پیام نمی‌فرستد (چون هیچ
    کانسومری روی routing_key قدیمی 'logs.audit' گوش نمی‌داد و لاگ‌ها گم
    می‌شدند). به‌جای آن از همان مسیر واحد و تست‌شده‌ی صف 'logs_queue' که
    توسط logging_service مصرف می‌شود استفاده می‌کند.
    """
    # ایمپورت تأخیری برای جلوگیری از Circular Import بین core.broker و audit_logs.services
    from main_api.modules.audit_logs.services import send_audit_log

    payload_extra = extra_data or {}
    if kwargs:
        payload_extra.update(kwargs)

    action = payload_extra.pop("action", "SYSTEM_EVENT")

    await send_audit_log(
        action=action,
        success=level.upper() not in ("ERROR", "CRITICAL"),
        severity=level.upper(),
        service_name=service,
        description=message,
        **payload_extra
    )
