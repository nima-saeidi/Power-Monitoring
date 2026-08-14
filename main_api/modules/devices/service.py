from fastapi import HTTPException, status
from typing import List, Optional
from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, LocationResponse,
    CommandRequest, CampusWithSubsectionsCreate
)
import pandas as pd
from telemetry_service.modbus_client import ModbusReader


class DeviceService:
    def __init__(self, repo: DeviceRepository):
        self.repo = repo

    # ----- Location Service Methods -----

    async def create_campus_with_subsections(self, data: CampusWithSubsectionsCreate) -> LocationResponse:
        # ۱. بررسی وجود ریشه (دانشگاه تبریز)
        root_name = "دانشگاه تبریز"
        root = await self.repo.get_location_by_name(name=root_name, parent_id=None)

        # اگر نبود، می‌سازیم
        if not root:
            root_data = LocationCreate(name=root_name, location_type="Root", parent_id=None)
            root = await self.repo.create_location(root_data)

        # ۲. ایجاد پردیس و وصل کردن آن به ریشه (دانشگاه تبریز)
        campus_data = LocationCreate(
            name=data.campus_name,
            location_type="Campus",
            parent_id=root.id,
            description=data.description
        )
        campus = await self.repo.create_location(campus_data)

        # ۳. حلقه روی زیربخش‌ها و ثبت آن‌ها زیرمجموعه‌ی پردیس جدید
        for sub_name in data.sub_sections:
            sub_data = LocationCreate(
                name=sub_name,
                location_type="SubSection",
                parent_id=campus.id
            )
            await self.repo.create_location(sub_data)

        # ۴. فراخوانی مجدد پردیس از دیتابیس تا زیرمجموعه‌ها (sub_locations) را برای فرانت‌‌اند لود کند
        return await self.repo.get_location_by_id(campus.id)

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

    async def import_feeders_from_excel(self, df: pd.DataFrame) -> dict:
        success_count = 0
        failed_count = 0
        errors = []

        # جایگزینی مقادیر خالی (NaN) با None
        df = df.where(pd.notnull(df), None)

        # بررسی یا ایجاد ریشه اصلی
        root_name = "دانشگاه تبریز"
        root = await self.repo.get_location_by_name(name=root_name, parent_id=None)
        if not root:
            root = await self.repo.create_location(LocationCreate(name=root_name, location_type="Root", parent_id=None))

        for index, row in df.iterrows():
            row_number = index + 2  # ردیف در فایل اکسل
            try:
                # ۱. پردازش پردیس (Campus)
                campus_name = str(row.get('campus_name', '')).strip() or "پردیس نامشخص"
                campus = await self.repo.get_location_by_name(name=campus_name, parent_id=root.id)
                if not campus:
                    campus = await self.repo.create_location(
                        LocationCreate(name=campus_name, location_type="Campus", parent_id=root.id))

                # ۲. پردازش واحد (Unit)
                unit_name = str(row.get('unit_name', '')).strip()
                unit_id = None
                if unit_name and unit_name.lower() != "none":
                    unit = await self.repo.get_location_by_name(name=unit_name, parent_id=campus.id)
                    if not unit:
                        unit = await self.repo.create_location(
                            LocationCreate(name=unit_name, location_type="SubSection", parent_id=campus.id))
                    unit_id = unit.id

                # ۳. پردازش پست (Post)
                post_name = str(row.get('post_name', '')).strip()
                if not post_name or post_name.lower() == "none":
                    raise ValueError("نام پست (post_name) الزامی است.")

                post_data = PostCreate(
                    name=post_name,
                    campus_id=campus.id,
                    unit_id=unit_id,
                    location_id=unit_id if unit_id else campus.id,
                    supply_source=row.get('supply_source'),
                    transformer_specs=row.get('transformer_specs'),
                    ip_address=row.get('ip_address'),
                    port=int(row.get('port')) if row.get('port') else 502,
                    latitude=float(row.get('latitude')) if row.get('latitude') else None,
                    longitude=float(row.get('longitude')) if row.get('longitude') else None
                )
                # در سناریوی واقعی بهتر است در اینجا پست جستجو شود، فرض ما ایجاد است
                post = await self.repo.create_post(post_data)

                # ۴. پردازش فیدر (Feeder)
                metadata = {}
                if row.get('description'):
                    metadata['description'] = str(row.get('description'))

                feeder_name = str(row.get('feeder_name', '')).strip()
                if feeder_name and feeder_name.lower() != "none":
                    feeder_data = FeederCreate(
                        post_id=post.id,
                        name=feeder_name,
                        feeder_type=str(row.get('feeder_type')) if row.get('feeder_type') else None,
                        max_current=float(row.get('max_current')) if row.get('max_current') else None,
                        cable_type=str(row.get('cable_type')) if row.get('cable_type') else None,
                        modbus_address=int(row.get('modbus_address')) if row.get('modbus_address') else None,
                        metadata_info=metadata if metadata else None
                    )
                    await self.repo.create_feeder(feeder_data)

                success_count += 1

            except Exception as e:
                failed_count += 1
                errors.append({"row": row_number, "error": str(e)})

        return {
            "success": True,
            "total_processed": success_count + failed_count,
            "imported_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }

    # ----- Command & Control Service Methods -----
    async def execute_device_command(self, feeder_id: int, request: CommandRequest) -> dict:
        """
        ارسال فرمان قطع و وصل به یک فیدر از طریق پروتکل مدباس
        """
        # ۱. بررسی وجود فیدر به همراه اطلاعات پست در دیتابیس
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="فیدر مورد نظر یافت نشد."
            )

        # ۲. بررسی اینکه آیا پستِ مربوط به این فیدر IP برای ارتباط دارد یا خیر (جایگزینی substation با post)
        if not feeder.post or not feeder.post.ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="پست مربوط به این فیدر فاقد آدرس IP است و قابلیت کنترل از راه دور ندارد."
            )

        port = feeder.post.port if feeder.post.port else 502
        modbus_client = ModbusReader(host=feeder.post.ip_address, port=port)

        try:
            # ۴. ارسال فرمان ناهمگام (async)
            success = await modbus_client.write_coil(
                address=request.register_address,
                value=request.command
            )
        finally:
            # ۵. اطمینان از بسته شدن کانکشن در هر شرایطی
            await modbus_client.close()

        # ۶. بررسی نتیجه
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
