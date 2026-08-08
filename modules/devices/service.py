from fastapi import HTTPException, status
from typing import List, Optional
from modules.devices.repository import DeviceRepository
from modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, LocationResponse
)

class DeviceService:
    def __init__(self, repo: DeviceRepository):
        self.repo = repo

    # ----- Location Service Methods -----
    async def create_location(self, data: LocationCreate) -> LocationResponse:
        if data.parent_id:
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مکان والد یافت نشد.")
        return await self.repo.create_location(data)

    async def get_locations(self, skip: int = 0, limit: int = 100) -> List[LocationResponse]:
        return await self.repo.get_all_locations(skip=skip, limit=limit)

    async def get_root_locations(self) -> List[LocationResponse]:
        return await self.repo.get_root_locations()

    async def get_location(self, location_id: int) -> LocationResponse:
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مکان مورد نظر یافت نشد.")
        return location

    async def update_location(self, location_id: int, data: LocationUpdate) -> LocationResponse:
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مکان مورد نظر یافت نشد.")

        if data.parent_id:
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مکان والد یافت نشد.")
            if data.parent_id == location_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="یک مکان نمی‌تواند والد خودش باشد.")

        return await self.repo.update_location(location, data)

    async def delete_location(self, location_id: int) -> dict:
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مکان مورد نظر یافت نشد.")
        await self.repo.delete_location(location)
        return {"message": "مکان با موفقیت حذف شد."}

    # ----- Post Service Methods -----
    async def create_post(self, data: PostCreate) -> PostResponse:
        if data.location_id:
            loc = await self.repo.get_location_by_id(data.location_id)
            if not loc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="مکان (لوکیشن) اختصاص یافته به پست یافت نشد.")
        return await self.repo.create_post(data)

    async def get_posts(self, skip: int = 0, limit: int = 100) -> List[PostResponse]:
        return await self.repo.get_all_posts(skip=skip, limit=limit)

    async def get_post(self, post_id: int) -> PostResponse:
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مورد نظر یافت نشد.")
        return post

    async def update_post(self, post_id: int, data: PostUpdate) -> PostResponse:
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مورد نظر یافت نشد.")

        if data.location_id:
            loc = await self.repo.get_location_by_id(data.location_id)
            if not loc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="مکان (لوکیشن) جدید اختصاص یافته یافت نشد.")

        return await self.repo.update_post(post, data)

    async def delete_post(self, post_id: int) -> dict:
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مورد نظر یافت نشد.")
        await self.repo.delete_post(post)
        return {"message": "پست و تمام فیدرهای متصل به آن با موفقیت حذف شدند."}

    # ----- Feeder Service Methods -----
    async def create_feeder(self, data: FeederCreate) -> FeederResponse:
        post = await self.repo.get_post_by_id(data.post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مربوط به این فیدر یافت نشد.")
        return await self.repo.create_feeder(data)

    async def get_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[FeederResponse]:
        return await self.repo.get_all_feeders(post_id=post_id, skip=skip, limit=limit)

    async def get_feeder(self, feeder_id: int) -> FeederResponse:
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="فیدر مورد نظر یافت نشد.")
        return feeder

    async def update_feeder(self, feeder_id: int, data: FeederUpdate) -> FeederResponse:
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="فیدر مورد نظر یافت نشد.")
        return await self.repo.update_feeder(feeder, data)

    async def delete_feeder(self, feeder_id: int) -> dict:
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="فیدر مورد نظر یافت نشد.")
        await self.repo.delete_feeder(feeder)
        return {"message": "فیدر با موفقیت حذف شد."}

    # ----- Link Service Methods -----
    async def create_link(self, data: LinkCreate) -> LinkResponse:
        from_post = await self.repo.get_post_by_id(data.from_post_id)
        if not from_post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مبدأ یافت نشد.")

        to_post = await self.repo.get_post_by_id(data.to_post_id)
        if not to_post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پست مقصد یافت نشد.")

        return await self.repo.create_link(data)

    async def get_links(self, skip: int = 0, limit: int = 100) -> List[LinkResponse]:
        return await self.repo.get_all_links(skip=skip, limit=limit)

    async def get_link(self, link_id: int) -> LinkResponse:
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لینک مورد نظر یافت نشد.")
        return link

    async def update_link(self, link_id: int, data: LinkUpdate) -> LinkResponse:
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لینک مورد نظر یافت نشد.")
        return await self.repo.update_link(link, data)

    async def delete_link(self, link_id: int) -> dict:
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لینک مورد نظر یافت نشد.")
        await self.repo.delete_link(link)
        return {"message": "لینک با موفقیت حذف شد."}
