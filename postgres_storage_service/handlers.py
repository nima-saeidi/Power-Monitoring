import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import delete, update, inspect
from core.database import AsyncSessionLocal
from models import Location, Post, Feeder, Link

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
}


def sanitize_data_for_model(model_class, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    فیلتر کردن کلیدهای نامعتبر و تصحیح فیلدهای خاص مثل metadata و datetime
    """
    if not isinstance(data, dict):
        return {}

    sanitized = {}

    # فیلدهای معتبر تعریف شده روی مدل
    mapper = inspect(model_class)
    valid_columns = {col.key for col in mapper.column_attrs}

    # نگاشت نام فیلد در صورتی که دیتابیس با نام پایتون تفاوت داشته باشد
    payload_copy = data.copy()
    if "metadata" in payload_copy and "metadata_info" in valid_columns:
        payload_copy["metadata_info"] = payload_copy.pop("metadata")

    for key, value in payload_copy.items():
        if key in valid_columns:
            # تبدیل خودکار رشته تاریخ ISO به شیء datetime در صورت نیاز
            col_type = mapper.column_attrs[key].columns[0].type.python_type
            if col_type is datetime and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    pass
            sanitized[key] = value

    return sanitized


async def handle_db_write_event(payload: Dict[str, Any]):
    """
    پردازش انواع عملیات نوشتنی روی دیتابیس بر اساس پیلود پیام
    """
    entity_name = payload.get("entity", "").lower()
    action = payload.get("action", "").lower()
    data = payload.get("data")
    filters = payload.get("filters", {})

    model = MODEL_MAPPING.get(entity_name)
    if not model:
        logger.error(f"Unknown entity: '{entity_name}'")
        return

    async with AsyncSessionLocal() as session:
        try:
            if action == "create":
                clean_data = sanitize_data_for_model(model, data)
                # حذف id در create تا خود دیتابیس auto-increment را اعمال کند
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
                item_id = filters.get("id") or (data.get("id") if isinstance(data, dict) else None)
                if not item_id:
                    logger.warning(f"Update operation requires an ID for {entity_name}.")
                    return

                clean_data = sanitize_data_for_model(model, data)
                clean_data.pop("id", None)  # جلوگیری از آپدیت کلید اصلی

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
                item_id = filters.get("id")
                if not item_id:
                    logger.warning(f"Delete operation requires an ID for {entity_name}.")
                    return

                stmt = delete(model).where(model.id == item_id)
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Deleted {entity_name} with id={item_id}.")

            else:
                logger.warning(f"Unsupported action '{action}' on entity '{entity_name}'")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to execute DB operation for {entity_name} ({action}): {e}", exc_info=True)
            raise e
