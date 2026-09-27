import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import delete, update, inspect
from core.database import AsyncSessionLocal

from models import Location, Post, Feeder, Link, User

logger = logging.getLogger("postgres_storage")

MODEL_MAPPING = {
    "location": Location,
    "locations": Location,
    "post": Post,
    "posts": Post,
    "feeder": Feeder,
    "feeders": Feeder,
    "link": Link,
    "links": Link,
    "user": User,
    "users": User,
}


def sanitize_data_for_model(model_class, data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    sanitized = {}

    mapper = inspect(model_class)
    valid_columns = {col.key for col in mapper.column_attrs}

    payload_copy = data.copy()
    if "metadata" in payload_copy and "metadata_info" in valid_columns:
        payload_copy["metadata_info"] = payload_copy.pop("metadata")

    for key, value in payload_copy.items():
        if key in valid_columns:
            col_type = mapper.column_attrs[key].columns[0].type.python_type
            if col_type is datetime and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    pass
            sanitized[key] = value

    return sanitized


def _extract_id(payload: Dict[str, Any], filters: Dict[str, Any], data: Any):
    for source in (filters or {}, data if isinstance(data, dict) else {}, payload):
        for key in ("id", "user_id"):
            if source.get(key):
                return source[key]
    return None


async def handle_db_write_event(payload: Dict[str, Any]):
    entity_name = str(payload.get("entity", "")).lower().strip()
    raw_action = str(payload.get("action", "")).lower().strip()
    data = payload.get("data")
    filters = payload.get("filters", {})

    model = MODEL_MAPPING.get(entity_name)
    if not model:
        logger.error(f"Unknown entity: '{entity_name}'")
        return

    if "bulk" in raw_action:
        action = "bulk_create"
    elif "create" in raw_action:
        action = "create"
    elif "update" in raw_action:
        action = "update"
    elif "delete" in raw_action:
        action = "delete"
    else:
        action = raw_action

    async with AsyncSessionLocal() as session:
        try:
            if action == "create":
                clean_data = sanitize_data_for_model(model, data)
                clean_data.pop("id", None)

                instance = model(**clean_data)
                session.add(instance)
                await session.commit()
                logger.info(f"Created {entity_name} successfully.")

            elif action == "bulk_create":
                if isinstance(data, list):
                    instances = []
                    for item in data:
                        clean_item = sanitize_data_for_model(model, item)
                        clean_item.pop("id", None)
                        instances.append(model(**clean_item))

                    session.add_all(instances)
                    await session.commit()
                    logger.info(f"Bulk created {len(instances)} items for {entity_name}.")

            elif action == "update":
                item_id = _extract_id(payload, filters, data)

                if not item_id:
                    logger.warning(f"Update operation requires an ID for {entity_name}.")
                    return

                clean_data = sanitize_data_for_model(model, data)
                clean_data.pop("id", None)

                if not clean_data:
                    logger.warning(f"No valid fields to update for {entity_name} id={item_id}.")
                    return

                stmt = (
                    update(model)
                    .where(model.id == item_id)
                    .values(**clean_data)
                )
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Updated {entity_name} with id={item_id}.")

            elif action == "delete":
                item_id = _extract_id(payload, filters, data)

                if not item_id:
                    logger.warning(f"Delete operation requires an ID for {entity_name}.")
                    return

                stmt = delete(model).where(model.id == item_id)
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Deleted {entity_name} with id={item_id}.")

            else:
                logger.warning(f"Unsupported action '{action}' (raw: '{raw_action}') on entity '{entity_name}'")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to execute DB operation for {entity_name} ({action}): {e}", exc_info=True)
            raise e
