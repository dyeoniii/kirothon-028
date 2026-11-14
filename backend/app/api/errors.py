"""공통 오류: {"error": {"code", "message"}} 형식."""
from __future__ import annotations

import logging
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("akpleguard.api")

_SECRET_PATTERN = re.compile(r"(key|token|api_key|apikey|authorization)=[^&\s'\"]+", re.IGNORECASE)


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def safe_message(exc: BaseException, limit: int = 200) -> str:
    """외부 모듈 예외 메시지에서 키/토큰 형태를 가리고 길이를 제한한다."""
    text = _SECRET_PATTERN.sub(r"\1=***", str(exc)).strip()
    text = text[:limit]
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


_HTTP_CODES = {400: "VALIDATION_ERROR", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "FILE_TOO_LARGE"}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = f"{loc}: {first.get('msg', '')}" if loc else first.get("msg", "")
        return JSONResponse(status_code=400, content=_body("VALIDATION_ERROR", f"요청 형식이 올바르지 않습니다. ({detail})"))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        message = "요청한 리소스를 찾을 수 없습니다." if exc.status_code == 404 else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=_body(code, message))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", safe_message(exc))
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "서버 내부 오류가 발생했습니다."))
