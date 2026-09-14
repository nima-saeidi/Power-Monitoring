import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

import pandas as pd
from fastapi import HTTPException, status

# ایمپورت RabbitMQPublisher (با مسیردهی استاندارد پروژه)
try:
    from main_api.common.message_broker import RabbitMQPublisher
except ImportError:
    from main_api.core.broker import RabbitMQPublisher

from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.schemas import (
    CampusWithSubsectionsCreate,
    CommandRequest,
    FeederCreate,
    FeederUpdate,
    LinkCreate,
    LinkUpdate,
    LocationCreate,
    LocationUpdate,
    PostCreate,
    PostUpdate,
)


class DeviceService:

    def __init__(self, repo: DeviceRepository, broker: RabbitMQPublisher):
        """
        DeviceService requires a MessageBroker instance for publishing events.
        """
        self.repo = repo
        self.broker = broker

    async def _publish(self, entity: str, action: str, data: dict, filters: Optional[dict] = None):
        """
        A helper method to publish events to RabbitMQ.
        Automatically adds routing_key, event_id, timestamp, and entity name.
        """
        # Pydantic models have .model_dump(), SQLAlchemy objects don't.
        # This safely converts any object to a dictionary.
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, '_asdict'):  # for SQLAlchemy results / namedtuples
            data_dict = data._asdict()
        elif hasattr(data, '__dict__'):  # for SQLAlchemy ORM objects
            data_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        else:
            data_dict = data

        event_body = {
            "entity": entity,
            "action": action,
            "data": data_dict,
            "filters": filters if filters else {},
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # ساخت روتینگ کی استاندارد بر اساس entity و action (مثلاً: location.create)
        routing_key = f"{entity}.{action}"

        # ارسال routing_key اجباری به همراه پیام
        await self.broker.publish_event(routing_key=routing_key, message=event_body)

    # =========================================================
    # LOCATION SERVICES
    # =========================================================
    async def create_location(self, data: LocationCreate):
        # بررسی وجود والد در صورت ارسال parent_id
        if data.parent_id:
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent location with id {data.parent_id} not found."
                )

        new_location_obj = await self.repo.create_location(data)
        # دریافت شیء کامل جهت انتشار رویداد
        full_new_location = await self.repo.get_location_by_id(new_location_obj.id)

        await self._publish("location", "create", data=full_new_location)
        return full_new_location

    async def update_location(self, location_id: int, data: LocationUpdate):
        existing_location = await self.repo.get_location_by_id(location_id)
        if not existing_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with id {location_id} not found."
            )

        if data.parent_id is not None:
            if data.parent_id == location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A location cannot be its own parent."
                )
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent location with id {data.parent_id} not found."
                )

        updated_location = await self.repo.update_location(location_id, data)
        if not updated_location:
            raise HTTPException(status_code=404, detail="Location not found")

        update_data = data.model_dump(exclude_unset=True)
        await self._publish("location", "update", data=update_data, filters={"id": location_id})

        return updated_location

    async def delete_location(self, location_id: int):
        is_deleted = await self.repo.delete_location(location_id)
        if not is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

        await self._publish("location", "delete", data={}, filters={"id": location_id})
        return {"message": "Location deleted successfully."}

    async def get_locations_flat(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_locations_flat(skip=skip, limit=limit)

    async def get_locations(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_locations(skip=skip, limit=limit)

    async def get_location(self, location_id: int):
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        return location

    # =========================================================
    # POST SERVICES
    # =========================================================
    async def create_post(self, data: PostCreate):
        new_post = await self.repo.create_post(data)
        await self._publish("post", "create", data=new_post)
        return new_post

    async def update_post(self, post_id: int, data: PostUpdate):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        updated_post = await self.repo.update_post(post, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("post", "update", data=update_data, filters={"id": post_id})
        return updated_post

    async def delete_post(self, post_id: int):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        await self.repo.delete_post(post)
        await self._publish("post", "delete", data={}, filters={"id": post_id})
        return {"message": "Post deleted successfully."}

    async def get_posts(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_posts(skip=skip, limit=limit)

    async def get_post(self, post_id: int):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        return post

    # =========================================================
    # FEEDER SERVICES
    # =========================================================
    async def create_feeders(self, data_input: Union[List[FeederCreate], FeederCreate]):
        if not isinstance(data_input, list):
            data_list = [data_input]
        else:
            data_list = data_input

        created_feeders = []
        for data in data_list:
            new_feeder = await self.repo.create_feeder(data)
            await self._publish("feeder", "create", data=new_feeder)
            created_feeders.append(new_feeder)

        return created_feeders[0] if not isinstance(data_input, list) else created_feeders

    async def update_feeder(self, feeder_id: int, data: FeederUpdate):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")

        updated_feeder = await self.repo.update_feeder(feeder, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("feeder", "update", data=update_data, filters={"id": feeder_id})
        return updated_feeder

    async def delete_feeder(self, feeder_id: int):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")

        await self.repo.delete_feeder(feeder)
        await self._publish("feeder", "delete", data={}, filters={"id": feeder_id})
        return {"message": "Feeder deleted successfully."}

    async def get_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_feeders(post_id=post_id, skip=skip, limit=limit)

    async def get_feeder(self, feeder_id: int):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")
        return feeder

    # =========================================================
    # LINK SERVICES
    # =========================================================
    async def create_link(self, data: LinkCreate):
        new_link = await self.repo.create_link(data)
        await self._publish("link", "create", data=new_link)
        return new_link

    async def update_link(self, link_id: int, data: LinkUpdate):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

        updated_link = await self.repo.update_link(link, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("link", "update", data=update_data, filters={"id": link_id})
        return updated_link

    async def delete_link(self, link_id: int):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

        await self.repo.delete_link(link)
        await self._publish("link", "delete", data={}, filters={"id": link_id})
        return {"message": "Link deleted successfully."}

    async def get_links(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_links(skip=skip, limit=limit)

    async def get_link(self, link_id: int):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")
        return link
