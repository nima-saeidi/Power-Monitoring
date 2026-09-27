import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from main_api.core.database import AsyncSessionLocal
from main_api.core.domain import (
    STATUS_CRITICAL, STATUS_NORMAL, STATUS_UNKNOWN, STATUS_WARNING, normalize_energy_role,
)
from main_api.core.email_templates import build_load_alert_email_html
from main_api.modules.feeders.models import Feeder
from main_api.modules.links.models import Link
from main_api.modules.notifications.alerts import dispatch_alert
from main_api.modules.notifications.models import NotificationPriority, NotificationType
from main_api.modules.settings.service import SettingService
from main_api.modules.telemetry.ws_manager import ws_manager

logger = logging.getLogger(__name__)

META_REFRESH_SECONDS = 60
STALE_AFTER_SECONDS = 60

STATUS_LABELS = {STATUS_NORMAL: "عادی", STATUS_WARNING: "هشدار", STATUS_CRITICAL: "بحرانی", STATUS_UNKNOWN: "نامشخص"}


@dataclass
class _Entity:
    kind: str
    id: int
    name: str
    rated_current: Optional[float]
    load_status: str
    post_id: Optional[int] = None
    role: Optional[str] = None
    feeder_id: Optional[int] = None


@dataclass
class _StatusChange:
    entity: _Entity
    old_status: str
    new_status: str
    load_percent: Optional[float]
    current: Optional[float]


def evaluate_load(current: Optional[float], rated_current: Optional[float],
                  warning_pct: float, critical_pct: float) -> Tuple[str, Optional[float]]:
    if current is None or not rated_current or rated_current <= 0:
        return STATUS_UNKNOWN, None
    percent = round(abs(float(current)) / float(rated_current) * 100, 1)
    if percent >= critical_pct:
        return STATUS_CRITICAL, percent
    if percent >= warning_pct:
        return STATUS_WARNING, percent
    return STATUS_NORMAL, percent


@dataclass
class LiveMonitor:
    feeders: Dict[int, _Entity] = field(default_factory=dict)
    links: Dict[int, _Entity] = field(default_factory=dict)
    links_by_feeder: Dict[int, List[int]] = field(default_factory=lambda: defaultdict(list))
    latest: Dict[int, dict] = field(default_factory=dict)
    warning_pct: float = 75.0
    critical_pct: float = 90.0
    cooldown_seconds: int = 300
    _loaded_at: float = 0.0
    _last_alert: Dict[Tuple[str, int, str], float] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def refresh(self, force: bool = False) -> None:
        if not force and time.monotonic() - self._loaded_at < META_REFRESH_SECONDS:
            return
        async with self._lock:
            if not force and time.monotonic() - self._loaded_at < META_REFRESH_SECONDS:
                return
            async with AsyncSessionLocal() as db:
                feeders = (await db.execute(select(Feeder).options(selectinload(Feeder.post)))).scalars().all()
                links = (await db.execute(select(Link))).scalars().all()
                system_settings = await SettingService.get_or_create_settings(db)

            self.warning_pct = float(system_settings.warning_threshold)
            self.critical_pct = float(system_settings.critical_threshold)
            self.cooldown_seconds = int(system_settings.notification_cooldown_seconds or 0)
            self.feeders = {
                f.id: _Entity("feeder", f.id, f.name, f.max_current, f.load_status or STATUS_UNKNOWN,
                              post_id=f.post_id, role=role_of(f))
                for f in feeders
            }
            self.links = {
                ln.id: _Entity("link", ln.id, ln.name or f"لینک {ln.id}", ln.allowed_current,
                               ln.load_status or STATUS_UNKNOWN, feeder_id=ln.feeder_id)
                for ln in links
            }
            self.links_by_feeder = defaultdict(list)
            for ln in self.links.values():
                if ln.feeder_id:
                    self.links_by_feeder[ln.feeder_id].append(ln.id)
            self._loaded_at = time.monotonic()

    def invalidate(self) -> None:
        self._loaded_at = 0.0

    async def on_metric(self, payload: dict) -> dict:
        feeder_id = int(payload["feeder_id"])
        await self.refresh()
        if feeder_id not in self.feeders:
            await self.refresh(force=True)
        feeder = self.feeders.get(feeder_id)
        current = payload.get("current")

        enriched = dict(payload)
        changes: List[_StatusChange] = []
        if feeder:
            status, percent = evaluate_load(current, feeder.rated_current, self.warning_pct, self.critical_pct)
            enriched.update(load_status=status, load_percent=percent, role=feeder.role, post_id=feeder.post_id)
            if status != feeder.load_status:
                changes.append(_StatusChange(feeder, feeder.load_status, status, percent, current))
            for link_id in self.links_by_feeder.get(feeder_id, []):
                link = self.links[link_id]
                link_status, link_percent = evaluate_load(current, link.rated_current, self.warning_pct, self.critical_pct)
                if link_status != link.load_status:
                    changes.append(_StatusChange(link, link.load_status, link_status, link_percent, current))

        self.latest[feeder_id] = {**enriched, "received_at": datetime.now(timezone.utc).isoformat()}
        for change in changes:
            await self._apply_change(change)
        return enriched

    async def _apply_change(self, change: _StatusChange) -> None:
        entity = change.entity
        entity.load_status = change.new_status
        model = Feeder if entity.kind == "feeder" else Link
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(update(model).where(model.id == entity.id).values(load_status=change.new_status))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist load status of {entity.kind} {entity.id}: {e}")

        await ws_manager.broadcast({"type": "STATUS_CHANGE", "data": {
            "entity": entity.kind, "id": entity.id, "name": entity.name,
            "feeder_id": entity.id if entity.kind == "feeder" else entity.feeder_id,
            "old_status": change.old_status, "new_status": change.new_status,
            "load_percent": change.load_percent, "current": change.current,
        }})
        await self._alert(change)

    async def _alert(self, change: _StatusChange) -> None:
        entity, new = change.entity, change.new_status
        if new == STATUS_UNKNOWN:
            return
        if new == STATUS_NORMAL and change.old_status not in (STATUS_WARNING, STATUS_CRITICAL):
            return
        key = (entity.kind, entity.id, new)
        now = time.monotonic()
        if now - self._last_alert.get(key, -1e9) < self.cooldown_seconds:
            return
        self._last_alert[key] = now

        label = "فیدر" if entity.kind == "feeder" else "لینک"
        percent = f"{change.load_percent}%" if change.load_percent is not None else "-"
        metadata = {"event_type": f"load_{new}", "entity": entity.kind, f"{entity.kind}_id": entity.id,
                    "load_percent": change.load_percent, "current": change.current,
                    "rated_current": entity.rated_current}
        if new == STATUS_NORMAL:
            title, n_type, priority, email_html = (
                f"بازگشت {label} به وضعیت عادی: {entity.name}", NotificationType.SUCCESS, NotificationPriority.MEDIUM, None)
            message = f"بار {label} «{entity.name}» به {percent} جریان مجاز برگشت."
        else:
            critical = new == STATUS_CRITICAL
            title = f"وضعیت {STATUS_LABELS[new]} {label}: {entity.name}"
            message = (f"جریان {label} «{entity.name}» به {change.current} آمپر رسید "
                       f"({percent} جریان مجاز {entity.rated_current} آمپر).")
            n_type = NotificationType.ALERT if critical else NotificationType.WARNING
            priority = NotificationPriority.CRITICAL if critical else NotificationPriority.HIGH
            email_html = build_load_alert_email_html(label, entity.name, STATUS_LABELS[new], critical, [
                f"جریان فعلی: {change.current} آمپر",
                f"جریان مجاز: {entity.rated_current} آمپر",
                f"درصد بار: {percent}",
                f"آستانه‌ها: هشدار {self.warning_pct}% / بحرانی {self.critical_pct}%",
            ])
        async with AsyncSessionLocal() as db:
            await dispatch_alert(db, title=title, message=message, n_type=n_type, priority=priority,
                                 source_type=entity.kind, source_id=entity.id, metadata=metadata,
                                 email_html=email_html)

    def snapshot(self) -> Dict[int, dict]:
        now = datetime.now(timezone.utc)
        result = {}
        for feeder_id, data in self.latest.items():
            age = (now - datetime.fromisoformat(data["received_at"])).total_seconds()
            result[feeder_id] = {**data, "stale": age > STALE_AFTER_SECONDS}
        return result


def role_of(feeder: Feeder) -> Optional[str]:
    for value in (feeder.feeder_type, feeder.post.post_type if feeder.post else None):
        try:
            role = normalize_energy_role(value)
        except ValueError:
            role = None
        if role:
            return role
    return None


live_monitor = LiveMonitor()
