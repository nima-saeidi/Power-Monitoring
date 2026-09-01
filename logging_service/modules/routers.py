from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from modules.schemas import LogFilterRequest, LogListResponse
from modules.services import logging_service_instance

router = APIRouter(prefix="/logs", tags=["Logs & Audits"])


@router.get("", response_model=LogListResponse)
async def fetch_logs(
    service_name: Optional[str] = Query(default=None, description="Filter by service name (e.g. main_api)"),
    action: Optional[str] = Query(default=None, description="Filter by action name"),
    user_id: Optional[int] = Query(default=None, description="Filter by User ID"),
    search: Optional[str] = Query(default=None, description="Search keyword in action/service"),
    limit: int = Query(default=50, ge=1, le=1000, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset")
):
    """دریافت لاگ‌ها از دیتابیس PostgreSQL با امکان فیلتر و صفحه‌بندی"""
    try:
        filters = LogFilterRequest(
            service_name=service_name,
            action=action,
            user_id=user_id,
            search=search,
            limit=limit,
            offset=offset
        )
        return await logging_service_instance.get_logs(filters)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching logs from database: {str(e)}"
        )
