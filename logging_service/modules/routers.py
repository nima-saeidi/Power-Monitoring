from fastapi import APIRouter, Depends, Query, HTTPException, status
from modules.logs.schemas import LogFilterRequest, LogListResponse
from modules.logs.services import logging_service_instance

router = APIRouter(prefix="/logs", tags=["Logs & Audits"])

@router.get("", response_model=LogListResponse)
async def fetch_logs(
    query: str = Query(default="*", description="Search query string"),
    range_seconds: int = Query(default=86400, description="Time range in seconds"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """دریافت لاگ‌ها با قابلیت فیلتر زمانی و متنی"""
    try:
        filters = LogFilterRequest(
            query=query,
            range_seconds=range_seconds,
            limit=limit,
            offset=offset
        )
        return await logging_service_instance.get_logs(filters)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching logs from Graylog: {str(e)}"
        )
