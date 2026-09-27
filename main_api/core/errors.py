from typing import Any, Optional

from fastapi import HTTPException


def api_error(status_code: int, error_code: str, message: str, **extra: Any) -> HTTPException:
    detail: dict = {"error_code": error_code, "message": message}
    if extra:
        detail["extra"] = extra
    return HTTPException(status_code=status_code, detail=detail)


def error_code_of(exc: HTTPException, default: Optional[str] = None) -> str:
    detail = exc.detail
    if isinstance(detail, dict) and detail.get("error_code"):
        return detail["error_code"]
    return default or f"HTTP_{exc.status_code}"


def message_of(exc: HTTPException) -> Any:
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        return detail["message"]
    return detail
