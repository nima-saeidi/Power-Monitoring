from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.database import get_db
from main_api.modules.auth.dependencies import get_current_user, authenticate_websocket
from main_api.modules.users.models import User
from main_api.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationMarkReadRequest,
    NotificationPreferenceUpdateRequest,
    NotificationFilterParams
)
from main_api.modules.notifications.repository import NotificationRepository

from fastapi import WebSocket, WebSocketDisconnect, Query, status
from .websocket import notifier_manager
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
        params: NotificationFilterParams = Depends(),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    notifications, total = await NotificationRepository.get_user_notifications(
        db,
        user_id=current_user.id,
        unread_only=params.unread_only,
        include_dismissed=params.include_dismissed,
        type_filter=params.type,
        priority_filter=params.priority,
        skip=(params.page - 1) * params.page_size,
        limit=params.page_size
    )

    _, unread_count = await NotificationRepository.get_user_notifications(
        db, user_id=current_user.id, unread_only=True
    )

    return {
        "items": notifications,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "unread_count": unread_count
    }


@router.post("/read")
async def mark_notifications_as_read(
        request: NotificationMarkReadRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    for n_id in request.notification_ids:
        await NotificationRepository.mark_as_read(db, n_id, current_user.id)

    return {"message": "Success"}


@router.post("/read-all")
async def mark_all_as_read(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    count = await NotificationRepository.mark_all_as_read(db, current_user.id)
    return {"message": f"{count} notifications marked as read"}


@router.post("/dismiss/{notification_id}")
async def dismiss_notification(
        notification_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    success = await NotificationRepository.dismiss(db, notification_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification dismissed"}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pref = await NotificationRepository.get_preferences(db, current_user.id)

    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return pref


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
        request: NotificationPreferenceUpdateRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    pref = await NotificationRepository.get_preferences(db, current_user.id)

    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)

    await db.commit()
    await db.refresh(pref)

    return pref



@router.websocket("/ws/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int, token: str | None = Query(default=None)):
    user = await authenticate_websocket(token)
    if not user or user.id != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await notifier_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        notifier_manager.disconnect(websocket, user_id)
