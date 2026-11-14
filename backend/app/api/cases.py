from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.common import get_case_or_404
from app.api.errors import AppError
from app.db import get_db, get_storage_dir
from app.models import Case, Comment
from app.schemas import CaseCreate, CaseDetail, CaseOut, CaseSummary

logger = logging.getLogger("akpleguard.api")
router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreate, db: Session = Depends(get_db)) -> Case:
    case = Case(title=body.title, description=body.description)
    db.add(case)
    db.commit()
    return case


@router.get("", response_model=list[CaseSummary])
def list_cases(db: Session = Depends(get_db)) -> list[dict]:
    cases = db.scalars(select(Case).order_by(Case.created_at.desc(), Case.id)).all()
    counts = dict(
        db.execute(
            select(Comment.case_id, func.count()).where(Comment.saved.is_(True)).group_by(Comment.case_id)
        ).all()
    )
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at, "saved_count": counts.get(c.id, 0)}
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db)) -> Case:
    get_case_or_404(db, case_id)
    # 댓글이 수천 개여도 댓글마다 판독을 따로 조회하지 않도록 한 번에 불러온다.
    return db.scalars(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.sources),
            selectinload(Case.comments).selectinload(Comment.analysis),
            selectinload(Case.answers),
        )
    ).one()


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str, db: Session = Depends(get_db)) -> Response:
    """사건과 연관 소스/댓글/판독/답변, 서버에 저장된 원본 이미지까지 삭제."""
    case = get_case_or_404(db, case_id)
    case_dir = get_storage_dir() / case.id
    db.delete(case)
    db.commit()
    try:
        if case_dir.exists():
            shutil.rmtree(case_dir)
    except OSError as exc:
        logger.error("원본 파일 삭제 실패: %s (%s)", case_dir, type(exc).__name__)
        raise AppError(500, "STORAGE_ERROR", "사건은 삭제되었으나 저장된 원본 파일 삭제에 실패했습니다.") from exc
    return Response(status_code=204)
