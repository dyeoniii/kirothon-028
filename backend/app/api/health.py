from __future__ import annotations

from fastapi import APIRouter

from app.api import adapters
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/adapters")
def adapters_status() -> dict[str, str]:
    """통합 점검용: 각 연결 함수가 real(실제 모듈)인지 stub인지 표시."""
    return adapters.adapter_status()
