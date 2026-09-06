import logging
from typing import Dict, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
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


async def handle_db_write_event(payload: Dict[str, Any]):
    """
    پردازش انواع عملیات نوشتنی روی دیتابیس بر اساس پیلود پیام
    فرمت مورد انتظار پیام:
    {
        "entity": "feeders",
        "action": "create" | "update" | "delete" | "bulk_create",
        "data": { ... } | [ { ... } ],
        "filters": { "id": 1 }  # برای update و delete
    }
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
                instance = model(**data)
                session.add(instance)
                await session.commit()
                logger.info(f"Created {entity_name} successfully.")

            elif action == "bulk_create":
                if isinstance(data, list):
                    instances = [model(**item) for item in data]
                    session.add_all(instances)
                    await session.commit()
                    logger.info(f"Bulk created {len(instances)} items for {entity_name}.")

            elif action == "update":
                item_id = filters.get("id") or data.get("id")
                if not item_id:
                    logger.warning(f"Update operation requires an ID for {entity_name}.")
                    return

                stmt = (
                    update(model)
                    .where(model.id == item_id)
                    .values(**{k: v for k, v in data.items() if k != "id"})
                    .execution_options(synchronize_session="fetch")
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
