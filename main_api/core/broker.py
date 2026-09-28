import asyncio
import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from main_api.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None
        self._declared_queues: set = set()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._closing = False

    @property
    def is_connected(self) -> bool:
        return bool(
            self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    async def connect(self):
        rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            self._declared_queues = set()

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

    async def start_with_retry(self, max_initial_attempts: int = 5, initial_delay: float = 2.0):
        """Connect with a bounded backoff at startup, then - if RabbitMQ is still
        unreachable - keep retrying in the background instead of leaving the
        publisher permanently disconnected until someone restarts the process.
        Without this, a RabbitMQ that comes up a few seconds after main_api (a
        common docker-compose race) silently drops every event forever."""
        self._closing = False
        delay = initial_delay
        for attempt in range(1, max_initial_attempts + 1):
            await self.connect()
            if self.is_connected:
                return
            if attempt < max_initial_attempts:
                logger.warning(
                    f"RabbitMQ connect attempt {attempt}/{max_initial_attempts} failed; "
                    f"retrying in {delay:.0f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

        logger.error(
            "Could not connect to RabbitMQ after initial retries. Events will be "
            "dropped until a connection is established; retrying in the background."
        )
        self._reconnect_task = asyncio.create_task(self._background_reconnect_loop())

    async def _background_reconnect_loop(self, interval: float = 15.0):
        while not self._closing and not self.is_connected:
            await asyncio.sleep(interval)
            if self._closing:
                return
            logger.info("Retrying RabbitMQ connection...")
            await self.connect()
            if self.is_connected:
                logger.info("✅ Reconnected to RabbitMQ.")
                return

    async def close(self):
        self._closing = True
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish_event(self, routing_key: str, message: Dict[str, Any]):
        if not self.exchange or not self.is_connected:
            logger.warning(f"RabbitMQ is not connected. Cannot publish event to routing_key '{routing_key}'.")
            return

        try:
            body = json.dumps(message, default=str).encode("utf-8")
            pika_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await self.exchange.publish(pika_message, routing_key=routing_key)
            logger.debug(f"Event published to exchange 'power_monitoring_events' with routing_key: '{routing_key}'")
        except Exception as e:
            logger.error(f"Error publishing event with routing_key '{routing_key}': {e}")

    async def publish_to_queue(self, queue_name: str, message: Dict[str, Any]) -> bool:
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
            logger.error(
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


message_broker = RabbitMQPublisher()

MessageBroker = RabbitMQPublisher


def get_rabbitmq_publisher() -> RabbitMQPublisher:
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
