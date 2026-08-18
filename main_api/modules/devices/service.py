from fastapi import HTTPException, status
from typing import List, Optional
from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, LocationResponse, CommandRequest
)
import pandas as pd
from typing import List

from fastapi import HTTPException, status

from typing import List

from fastapi import HTTPException, status


class DeviceService:

    def __init__(
            self,
            repo: DeviceRepository
    ):
        self.repo = repo

    async def create_campus_with_subsections(self, data):
        # ۱. ایجاد مکان اصلی (Campus) با استفاده از اسکیما
        campus_create_data = LocationCreate(
            name=data.campus_name,
            description=data.description,
            location_type="Campus"
        )
        campus = await self.repo.create_location(campus_create_data)

        # ۲. ایجاد زیرمجموعه‌ها در صورت وجود
        created_children = []
        if data.sub_sections:
            for sub_name in data.sub_sections:
                sub_data = LocationCreate(
                    name=sub_name,
                    parent_id=campus.id,
                    location_type="Sub-section"
                )
                sub_location = await self.repo.create_location(sub_data)
                created_children.append(sub_location)

        # ۳. انتساب فرزندان به والد برای نمایش درست در خروجی
        campus.children = created_children
        return campus

    async def create_location(
            self,
            data: "LocationCreate"
    ):

        # -----------------------------------------------------
        # بررسی Parent
        # -----------------------------------------------------
        if data.parent_id is not None:
            parent = await self.repo.get_location_by_id(
                data.parent_id
            )
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="مکان والد یافت نشد."
                )

        # -----------------------------------------------------
        # ایجاد Location
        # -----------------------------------------------------
        new_location = await self.repo.create_location(data)

        # -----------------------------------------------------
        # ایجاد Sub Sections
        # -----------------------------------------------------
        if data.sub_sections:
            for sub_name in data.sub_sections:
                child_data = LocationCreate(
                    name=sub_name,
                    description=f"زیربخش {sub_name}",
                    location_type="Department",
                    parent_id=new_location.id
                )
                await self.repo.create_location(child_data)

        # -----------------------------------------------------
        # دریافت مجدد
        # -----------------------------------------------------
        return await self.repo.get_location_by_id(new_location.id)

    # =========================================================
    # GET LOCATIONS
    # =========================================================

    async def get_locations(
            self,
            skip: int = 0,
            limit: int = 100
    ):
        return await self.repo.get_all_locations(
            skip=skip,
            limit=limit
        )

    async def get_root_locations(self):
        return await self.repo.get_root_locations()

    async def get_location(
            self,
            location_id: int
    ):
        location = await self.repo.get_location_by_id(
            location_id
        )

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )

        return location

    # =========================================================
    # UPDATE
    # =========================================================

    async def update_location(
            self,
            location_id: int,
            data: LocationUpdate
    ):

        location = await self.repo.get_location_by_id(
            location_id
        )

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )

        # -----------------------------------------------------
        # Parent
        # -----------------------------------------------------

        if data.parent_id is not None:

            if data.parent_id == location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="یک مکان نمی‌تواند والد خودش باشد."
                )

            parent = await self.repo.get_location_by_id(
                data.parent_id
            )

            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="مکان والد یافت نشد."
                )

        return await self.repo.update_location(
            location,
            data
        )

    # =========================================================
    # DELETE
    # =========================================================

    async def delete_location(
            self,
            location_id: int
    ):

        location = await self.repo.get_location_by_id(
            location_id
        )

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="مکان مورد نظر یافت نشد."
            )

        await self.repo.delete_location(
            location
        )

        return {
            "message": "مکان با موفقیت حذف شد."
        }

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

        # جایگزینی مقادیر خالی (NaN) با None برای جلوگیری از خطای Pydantic
        df = df.where(pd.notnull(df), None)

        for index, row in df.iterrows():
            row_number = index + 2  # ردیف در فایل اکسل (ردیف 1 هدر است)
            try:
                # مپ کردن داده‌های ردیف اکسل به اسکیمای FeederCreate
                # نکته: اگر نام فیلدهای شما در FeederCreate متفاوت است، این بخش را مطابق آن تغییر دهید
                feeder_data = FeederCreate(
                    post_id=int(row.get('post_id')) if row.get('post_id') else None,
                    name=str(row.get('name')),
                    ip_address=str(row.get('ip_address')) if row.get('ip_address') else None,
                    port=int(row.get('port')) if row.get('port') else 502,
                    unit_id=int(row.get('unit_id')) if row.get('unit_id') else 1,
                    capacity_kva=float(row.get('capacity_kva')) if row.get('capacity_kva') else None,
                    description=str(row.get('description')) if row.get('description') else None
                )

                # بررسی وجود پست
                post = await self.repo.get_post_by_id(feeder_data.post_id)
                if not post:
                    raise ValueError(f"پست با شناسه {feeder_data.post_id} یافت نشد.")

                # ثبت فیدر در دیتابیس
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

        # ۲. بررسی اینکه آیا پستِ مربوط به این فیدر IP برای ارتباط دارد یا خیر
        # (با فرض اینکه relation در مدل شما substation نام دارد)
        if not feeder.substation or not feeder.substation.ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="پست مربوط به این فیدر فاقد آدرس IP است و قابلیت کنترل از راه دور ندارد."
            )

        port = feeder.substation.port if feeder.substation.port else 502
        modbus_client = ModbusReader(host=feeder.substation.ip_address, port=port)

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

        # در صورت تمایل می‌توانید در اینجا لاگ/رویداد موفقیت‌آمیز بودن فرمان را نیز در دیتابیس ثبت کنید

        action_text = "وصل" if request.command else "قطع"
        return {
            "success": True,
            "message": f"فرمان {action_text} با موفقیت به فیدر '{feeder.name}' ارسال شد."
        }
