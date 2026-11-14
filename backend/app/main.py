"""악플가드 API 진입점 (S3 [API])."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import api_router
from app.api.errors import register_error_handlers
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="악플가드 API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(api_router)


# --- 단일 서버 배포: 빌드된 React(SPA) 정적 파일 제공 ---------------------------
# STATIC_DIR(기본 backend/static)에 index.html 이 있을 때만 활성화된다. 개발 환경에는 영향 없음.
_STATIC_DIR = Path(os.getenv("STATIC_DIR") or Path(__file__).resolve().parents[1] / "static")
_RESERVED = ("api", "docs", "redoc", "openapi.json")

if (_STATIC_DIR / "index.html").is_file():

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        first = full_path.split("/", 1)[0]
        if first in _RESERVED:  # 알 수 없는 API 경로는 index.html 이 아니라 404
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and _STATIC_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")
