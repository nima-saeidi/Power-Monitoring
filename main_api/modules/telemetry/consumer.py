import json
import logging
from typing import Optional

import aio_pika

from main_api.core.config import settings
from main_api.modules.telemetry.live import live_monitor
from main_api.modules.telemetry.ws_manager import ws_manager

logger = logging.getLogger(__name__)

_EVENT_TYPES = {
    "telemetry.metric": "NEW_TELEMETRY",
    "telemetry.alert.device_offline": "DEVICE_ALERT",
}


class TelemetryWebSocketConsumer:

    def __init__(self):
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None

    async def start(self):
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=100)
        exchange = await channel.declare_exchange(
            settings.TELEMETRY_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(exclusive=True, auto_delete=True)
        await queue.bind(exchange, routing_key="telemetry.#")
        await queue.consume(self.handle_message)
        logger.info(f"✅ Telemetry WebSocket consumer listening on exchange '{settings.TELEMETRY_EXCHANGE}'.")

    async def handle_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        async with message.process(requeue=False):
            event_type = _EVENT_TYPES.get(message.routing_key)
            if not event_type:
                return
            try:
                payload = json.loads(message.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning(f"Invalid telemetry payload on '{message.routing_key}'.")
                return
            if event_type == "NEW_TELEMETRY":
                try:
                    payload = await live_monitor.on_metric(payload)
                except Exception as e:
                    logger.error(f"Load status evaluation failed: {e}", exc_info=True)
            await ws_manager.broadcast({"type": event_type, "data": payload})

    async def stop(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


telemetry_ws_consumer = TelemetryWebSocketConsumer()
