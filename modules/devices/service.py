from fastapi import HTTPException, status
from typing import List, Optional
from modules.devices.repository import DeviceRepository
from modules.devices.schemas import PostCreate, PostUpdate, PostResponse, FeederCreate, FeederUpdate, FeederResponse

class DeviceService:
    def __init__(self, repo: DeviceRepository):
        self.repo = repo

    # ----- Post Service Methods -----
    async def create_post(self, data: PostCreate) -> PostResponse:
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
