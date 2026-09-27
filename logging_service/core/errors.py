import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def api_error(status_code: int, error_code: str, message: str, **extra: Any) -> HTTPException:
    detail: dict = {"error_code": error_code, "message": message}
    if extra:
        detail["extra"] = extra
    return HTTPException(status_code=status_code, detail=detail)


def _split_detail(exc: StarletteHTTPException) -> tuple[Any, str]:
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        return detail["message"], detail.get("error_code") or f"HTTP_{exc.status_code}"
    return detail, f"HTTP_{exc.status_code}"


def install_error_handlers(app: FastAPI, logger: Optional[logging.Logger] = None) -> None:
    log = logger or logging.getLogger("logging_service")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            {"field": " -> ".join(str(p) for p in e.get("loc", []) if p != "body"), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "پارامترهای درخواست نامعتبر است.",
                "error_code": "VALIDATION_ERROR",
                "details": details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        message, error_code = _split_detail(exc)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": message, "error_code": error_code},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "خطای داخلی سرویس لاگ رخ داده است.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )
