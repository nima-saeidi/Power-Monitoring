from typing import List
from datetime import datetime
from core.graylog_client import graylog_client
from modules.schemas import LogFilterRequest, LogListResponse, LogItem


class LoggingService:
    @staticmethod
    async def get_logs(filter_params: LogFilterRequest) -> LogListResponse:
        raw_data = await graylog_client.search_relative(
            query=filter_params.query,
            range_seconds=filter_params.range_seconds,
            limit=filter_params.limit,
            offset=filter_params.offset
        )

        messages = raw_data.get("messages", [])
        total = raw_data.get("total_results", len(messages))

        parsed_items: List[LogItem] = []
        for msg in messages:
            msg_payload = msg.get("message", {})

            log_id = msg_payload.get("_id", "")
            ts_str = msg_payload.get("timestamp", datetime.utcnow().isoformat())
            message_text = msg_payload.get("message", "")
            level = msg_payload.get("level")
            service = msg_payload.get("service_name") or msg_payload.get("facility")
            source = msg_payload.get("source")

            known_keys = {"_id", "timestamp", "message", "level", "service_name", "facility", "source"}
            extra = {k: v for k, v in msg_payload.items() if k not in known_keys}

            parsed_items.append(
                LogItem(
                    id=str(log_id),
                    timestamp=ts_str,
                    message=message_text,
                    level=level,
                    service_name=service,
                    source=source,
                    extra_fields=extra
                )
            )

        return LogListResponse(total=total, items=parsed_items)


logging_service_instance = LoggingService()
