"""
ورود یکجای ساختار شبکه از فایل اکسل: پردیس ← واحد (دانشکده) ← پست ← فیدر.

- هر ردیف یک فیدر است؛ پردیس/واحد/پست بر اساس نام (و کد پست در صورت وجود) پیدا یا ساخته می‌شوند.
- ردیف تکراری (همان فیدر در همان پست) به‌روزرسانی می‌شود، نه تکرار.
- اول همه‌ی ردیف‌ها اعتبارسنجی می‌شوند؛ اگر حتی یک ردیف خطا داشته باشد هیچ تغییری ذخیره نمی‌شود.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.domain import normalize_energy_role
from main_api.modules.feeders.models import Feeder
from main_api.modules.locations.models import Location
from main_api.modules.posts.models import Post

REQUIRED_COLUMNS = ("campus_name", "post_name", "feeder_name")
REGISTER_COLUMNS = ("active_power_register", "reactive_power_register", "voltage_register",
                    "current_register", "power_factor_register", "control_register")

# ستون‌های فایل نمونه (GET /feeders/download-template) به همراه یک ردیف مثال
TEMPLATE_ROW: Dict[str, Any] = {
    "campus_name": "پردیس اصلی", "campus_code": "C1",
    "unit_name": "دانشکده برق", "unit_code": "U1",
    "post_name": "پست شماره ۱", "post_code": "P1", "post_type": "consumer",
    "ip_address": "192.168.1.10", "port": 502,
    "supply_source": "پست توزیع مرکزی", "transformer_specs": "20kV/400V 800kVA",
    "latitude": 38.068, "longitude": 46.329,
    "feeder_name": "Feeder Output No. 1", "feeder_type": "consumer", "max_current": 630.0,
    "feeder_ip_address": "", "feeder_port": "", "modbus_address": 1,
    "active_power_register": 0, "reactive_power_register": 1, "voltage_register": 2,
    "current_register": 3, "power_factor_register": 4, "control_register": 10,
    "description": "توضیحات تستی ۱",
}


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _as_int(row: dict, key: str, errors: List[str]) -> Optional[int]:
    value = _clean(row.get(key))
    if value is None:
        return None
    try:
        number = float(value)
        if not number.is_integer():
            raise ValueError
        return int(number)
    except (TypeError, ValueError):
        errors.append(f"«{key}» باید عدد صحیح باشد (مقدار: {value})")
        return None


def _as_float(row: dict, key: str, errors: List[str]) -> Optional[float]:
    value = _clean(row.get(key))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"«{key}» باید عدد باشد (مقدار: {value})")
        return None


def _as_role(row: dict, key: str, errors: List[str]) -> Optional[str]:
    try:
        return normalize_energy_role(_clean(row.get(key)))
    except ValueError as e:
        errors.append(f"«{key}»: {e}")
        return None


def _parse_row(row: dict) -> Tuple[dict, List[str]]:
    errors: List[str] = []
    for col in REQUIRED_COLUMNS:
        if _clean(row.get(col)) is None:
            errors.append(f"ستون «{col}» خالی است")
    parsed = {
        "campus_name": _clean(row.get("campus_name")), "campus_code": _clean(row.get("campus_code")),
        "unit_name": _clean(row.get("unit_name")), "unit_code": _clean(row.get("unit_code")),
        "post": {
            "name": _clean(row.get("post_name")), "code": _clean(row.get("post_code")),
            "post_type": _as_role(row, "post_type", errors),
            "ip_address": _clean(row.get("ip_address")), "port": _as_int(row, "port", errors),
            "supply_source": _clean(row.get("supply_source")),
            "transformer_specs": _clean(row.get("transformer_specs")),
            "latitude": _as_float(row, "latitude", errors), "longitude": _as_float(row, "longitude", errors),
        },
        "feeder": {
            "name": _clean(row.get("feeder_name")),
            "feeder_type": _as_role(row, "feeder_type", errors),
            "max_current": _as_float(row, "max_current", errors),
            "ip_address": _clean(row.get("feeder_ip_address")),
            "port": _as_int(row, "feeder_port", errors),
            "modbus_address": _as_int(row, "modbus_address", errors),
            **{col: _as_int(row, col, errors) for col in REGISTER_COLUMNS},
        },
        "description": _clean(row.get("description")),
    }
    for key in ("name", "code", "ip_address", "supply_source", "transformer_specs"):
        if isinstance(parsed["post"][key], (int, float)):
            parsed["post"][key] = str(parsed["post"][key])
    if isinstance(parsed["feeder"]["name"], (int, float)):
        parsed["feeder"]["name"] = str(parsed["feeder"]["name"])
    return parsed, errors


async def _find_or_create_location(db: AsyncSession, cache: dict, stats: dict, name: str, code: Optional[str],
                                   parent_id: Optional[int], location_type: str) -> Location:
    key = (name, parent_id)
    if key in cache:
        return cache[key]
    query = select(Location).where(Location.name == name)
    query = query.where(Location.parent_id.is_(None) if parent_id is None else Location.parent_id == parent_id)
    location = (await db.execute(query)).scalars().first()
    if location is None:
        location = Location(name=name, code=code, parent_id=parent_id, location_type=location_type)
        db.add(location)
        await db.flush()
        stats["locations_created"] += 1
    elif code and not location.code:
        location.code = code
    cache[key] = location
    return location


async def import_hierarchy(db: AsyncSession, df: pd.DataFrame) -> Dict[str, Any]:
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"ستون‌های الزامی در فایل وجود ندارد: {', '.join(missing)}")

    rows, all_errors = [], []
    for index, row in enumerate(df.to_dict(orient="records")):
        parsed, errors = _parse_row(row)
        if errors:
            all_errors.append({"row": index + 2, "errors": errors})  # +2: سطر عنوان و شروع اکسل از ۱
        rows.append(parsed)
    if all_errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"message": "فایل خطا دارد؛ هیچ تغییری ذخیره نشد.", "rows": all_errors})

    stats = {"rows": len(rows), "locations_created": 0, "posts_created": 0, "posts_updated": 0,
             "feeders_created": 0, "feeders_updated": 0}
    location_cache: dict = {}
    created_posts, updated_posts = set(), set()
    try:
        for parsed in rows:
            campus = await _find_or_create_location(db, location_cache, stats, parsed["campus_name"],
                                                    parsed["campus_code"], None, "campus")
            parent = campus
            if parsed["unit_name"]:
                parent = await _find_or_create_location(db, location_cache, stats, parsed["unit_name"],
                                                        parsed["unit_code"], campus.id, "unit")

            post_data = {k: v for k, v in parsed["post"].items() if v is not None}
            post_query = (select(Post).where(Post.code == post_data["code"]) if post_data.get("code")
                          else select(Post).where(Post.name == post_data["name"], Post.location_id == parent.id))
            post = (await db.execute(post_query)).scalars().first()
            if post is None:
                post = Post(location_id=parent.id, **post_data)
                db.add(post)
                await db.flush()
                created_posts.add(post.id)
            else:
                for key, value in post_data.items():
                    setattr(post, key, value)
                post.location_id = parent.id
                if post.id not in created_posts:
                    updated_posts.add(post.id)

            feeder_data = {k: v for k, v in parsed["feeder"].items() if v is not None}
            if parsed["description"]:
                feeder_data["metadata_info"] = {"description": parsed["description"]}
            feeder = (await db.execute(
                select(Feeder).where(Feeder.post_id == post.id, Feeder.name == feeder_data["name"])
            )).scalars().first()
            if feeder is None:
                db.add(Feeder(post_id=post.id, **feeder_data))
                stats["feeders_created"] += 1
            else:
                if "metadata_info" in feeder_data:
                    feeder_data["metadata_info"] = {**(feeder.metadata_info or {}), **feeder_data["metadata_info"]}
                for key, value in feeder_data.items():
                    setattr(feeder, key, value)
                stats["feeders_updated"] += 1
            await db.flush()
        stats["posts_created"], stats["posts_updated"] = len(created_posts), len(updated_posts)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return stats
