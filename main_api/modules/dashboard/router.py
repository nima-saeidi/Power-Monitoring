from collections import Counter
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.core.database import get_db
from main_api.core.domain import CONSUMER, LOAD_STATUSES, PRODUCER, STATUS_CRITICAL, STATUS_WARNING
from main_api.modules.auth.dependencies import require_page
from main_api.modules.feeders.models import Feeder
from main_api.modules.links.models import Link
from main_api.modules.notifications.repository import NotificationRepository
from main_api.modules.posts.models import Post
from main_api.modules.telemetry.live import live_monitor, role_of

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _status_counts(items) -> Dict[str, int]:
    counts = Counter(item.load_status or "unknown" for item in items)
    return {status: counts.get(status, 0) for status in LOAD_STATUSES}


@router.get("/summary", summary="Network overview for the dashboard page")
async def get_summary(db: AsyncSession = Depends(get_db), current_user=Depends(require_page("dashboard"))):
    posts = (await db.execute(select(Post))).scalars().all()
    feeders = (await db.execute(select(Feeder).options(selectinload(Feeder.post)))).scalars().all()
    links = (await db.execute(select(Link))).scalars().all()
    live = live_monitor.snapshot()

    consumption = production = 0.0
    consumption_reactive = production_reactive = 0.0
    for feeder in feeders:
        data = live.get(feeder.id)
        if not data or data["stale"] or not feeder.is_active:
            continue
        role = role_of(feeder)
        if role == CONSUMER:
            consumption += float(data.get("active_power") or 0)
            consumption_reactive += float(data.get("reactive_power") or 0)
        elif role == PRODUCER:
            production += float(data.get("active_power") or 0)
            production_reactive += float(data.get("reactive_power") or 0)

    alerts: List[dict] = [
        {"entity": "feeder", "id": f.id, "name": f.name, "post_id": f.post_id, "load_status": f.load_status,
         "load_percent": (live.get(f.id) or {}).get("load_percent")}
        for f in feeders if f.load_status in (STATUS_WARNING, STATUS_CRITICAL)
    ] + [
        {"entity": "link", "id": ln.id, "name": ln.name, "feeder_id": ln.feeder_id, "load_status": ln.load_status}
        for ln in links if ln.load_status in (STATUS_WARNING, STATUS_CRITICAL)
    ]
    alerts.sort(key=lambda a: a["load_status"] != STATUS_CRITICAL)

    _, unread = await NotificationRepository.get_user_notifications(db, user_id=current_user.id, unread_only=True)

    return {
        "posts": {"total": len(posts), "active": sum(1 for p in posts if p.is_active),
                  "consumer": sum(1 for p in posts if p.post_type == CONSUMER),
                  "producer": sum(1 for p in posts if p.post_type == PRODUCER)},
        "feeders": {"total": len(feeders), "active": sum(1 for f in feeders if f.is_active),
                    "online": sum(1 for f in feeders if f.is_active and f.is_online),
                    "offline": sum(1 for f in feeders if f.is_active and not f.is_online),
                    "load_status": _status_counts(feeders)},
        "links": {"total": len(links), "load_status": _status_counts(links)},
        "power": {
            "consumption_kw": round(consumption, 3),
            "production_kw": round(production, 3),
            "net_kw": round(consumption - production, 3),
            "consumption_kvar": round(consumption_reactive, 3),
            "production_kvar": round(production_reactive, 3),
            "feeders_reporting": sum(1 for d in live.values() if not d["stale"]),
        },
        "alerts": alerts,
        "unread_notifications": unread,
        "thresholds": {"warning_percent": live_monitor.warning_pct, "critical_percent": live_monitor.critical_pct},
    }


@router.get("/live", summary="Latest reading and status of every feeder (for the map and live list)")
async def get_live(db: AsyncSession = Depends(get_db), current_user=Depends(require_page("dashboard"))):
    feeders = (await db.execute(select(Feeder).options(selectinload(Feeder.post)).order_by(Feeder.id))).scalars().all()
    live = live_monitor.snapshot()
    return [
        {
            "feeder_id": f.id,
            "name": f.name,
            "post_id": f.post_id,
            "post_name": f.post.name if f.post else None,
            "latitude": f.post.latitude if f.post else None,
            "longitude": f.post.longitude if f.post else None,
            "role": role_of(f),
            "is_active": f.is_active,
            "is_online": f.is_online,
            "load_status": f.load_status,
            "max_current": f.max_current,
            "latest": live.get(f.id),
        }
        for f in feeders
    ]
