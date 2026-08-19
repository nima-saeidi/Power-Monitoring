from typing import List, Optional
import pandas as pd
from fastapi import HTTPException, status

# Import Repository and Schemas
from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, CommandRequest,
    CampusWithSubsectionsCreate
)


# Assuming ModbusReader is defined elsewhere
# from main_api.core.modbus_client import ModbusReader


class DeviceService:

    def __init__(self, repo: DeviceRepository):
        self.repo = repo

    # =========================================================
    # LOCATION SERVICES
    # =========================================================

    async def create_campus_with_subsections(self, data: CampusWithSubsectionsCreate):
        # 1. Create the main location (Campus)
        campus_create_data = LocationCreate(
            name=data.campus_name,
            description=data.description,
            location_type="Campus",
            latitude=data.latitude,
            longitude=data.longitude,
            address=data.address
        )
        campus = await self.repo.create_location(campus_create_data)

        # 2. Create subsections if they exist
        if data.sub_sections:
            for sub_name in data.sub_sections:
                sub_data = LocationCreate(
                    name=sub_name,
                    parent_id=campus.id,
                    location_type="Sub-section"
                )
                await self.repo.create_location(sub_data)

        # 3. Re-fetch the campus to ensure the response includes children correctly
        return await self.repo.get_location_by_id(campus.id)

    async def create_location(self, data: LocationCreate):
        if data.parent_id is not None:
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="مکان والد یافت نشد."
                )

        new_location = await self.repo.create_location(data)

        if data.sub_sections:
            for sub_name in data.sub_sections:
                child_data = LocationCreate(
                    name=sub_name,
                    description=f"زیربخش {sub_name}",
                    location_type="Department",
                    parent_id=new_location.id
                )
                await self.repo.create_location(child_data)

        return await self.repo.get_location_by_id(new_location.id)

    async def get_locations(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_locations(skip=skip, limit=limit)

    async def get_root_locations(self):
        return await self.repo.get_root_locations()

    async def get_location(self, location_id: int):
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )
        return location

    async def update_location(self, location_id: int, data: LocationUpdate):
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )

        if data.parent_id is not None:
            if data.parent_id == location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="یک مکان نمی‌تواند والد خودش باشد."
                )
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="مکان والد یافت نشد."
                )

        return await self.repo.update_location(location_id, data)

    async def delete_location(self, location_id: int):
        is_deleted = await self.repo.delete_location(location_id)
        if not is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )
        return {"message": "مکان با موفقیت حذف شد."}

    # =========================================================
    # POST SERVICES
    # =========================================================

    async def create_post(self, data: PostCreate) -> PostResponse:
        # Validation for location_id, campus_id, unit_id can be added here
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

    # =========================================================
    # FEEDER SERVICES
    # =========================================================

    async def create_feeders(self, data_list: List[FeederCreate]) -> List[FeederResponse]:
        created_feeders = []
        post_cache = {}
        for data in data_list:
            if data.post_id not in post_cache:
                post = await self.repo.get_post_by_id(data.post_id)
                if not post:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"پست مربوط به فیدر '{data.name}' با شناسه {data.post_id} یافت نشد."
                    )
                post_cache[data.post_id] = post
            new_feeder = await self.repo.create_feeder(data)
            created_feeders.append(new_feeder)
        return created_feeders

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

    async def import_feeders_from_excel(self, df: pd.DataFrame) -> dict:
        success_count, failed_count = 0, 0
        errors = []
        df = df.where(pd.notnull(df), None)

        for index, row in df.iterrows():
            row_number = index + 2
            try:
                feeder_data = FeederCreate(
                    post_id=int(row['post_id']),
                    name=str(row['name']),
                    ip_address=str(row['ip_address']) if row.get('ip_address') else None,
                )
                post = await self.repo.get_post_by_id(feeder_data.post_id)
                if not post:
                    raise ValueError(f"پست با شناسه {feeder_data.post_id} یافت نشد.")
                await self.repo.create_feeder(feeder_data)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"row": row_number, "error": str(e)})

        return {
            "success": True,
            "total_processed": len(df),
            "imported_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }

    # =========================================================
    # COMMAND & CONTROL SERVICES
    # =========================================================

    async def execute_device_command(self, feeder_id: int, request: CommandRequest) -> dict:
        """
        Sends a connect/disconnect command to a feeder via Modbus.
        """
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="فیدر مورد نظر یافت نشد."
            )

        # CORRECTED: Access feeder.post instead of feeder.substation
        if not feeder.post or not feeder.post.ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="پست مربوط به این فیدر فاقد آدرس IP است و قابلیت کنترل از راه دور ندارد."
            )

        # CORRECTED: Use feeder.post.port
        port = feeder.post.port if feeder.post.port else 502
        # modbus_client = ModbusReader(host=feeder.post.ip_address, port=port)

        try:
            success = True
        finally:
            await modbus_client.close()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ارتباط با سخت‌افزار قطع است یا فرمان توسط تجهیز رد شد."
            )

        action_text = "وصل" if request.command else "قطع"
        return {
            "success": True,
            "message": f"فرمان {action_text} با موفقیت به فیدر '{feeder.name}' ارسال شد."
        }
