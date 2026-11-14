"""판독(analyze)과 댓글 증거 상태 변경(PATCH)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api import adapters
from app.api.common import get_case_or_404, get_comment_or_404
from app.api.errors import AppError, safe_message
from app.db import get_db
from app.models import Analysis, Comment, utcnow
from app.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    AnalyzeResponse,
    BulkCommentPatch,
    BulkCommentResult,
    CommentOut,
    CommentPatch,
)

router = APIRouter(tags=["analysis"])


def save_analysis(comment: Comment, result: AnalysisResult, analyzed_at) -> None:
    """판독 결과를 댓글의 Analysis 행에 저장(없으면 생성, 있으면 덮어쓰기). 원문 content는 건드리지 않는다."""
    data = dict(
        level=result.level,
        level_label=result.level_label,
        issues=result.issues,
        flagged_phrases=result.flagged_phrases,
        reason=result.reason,
        check_points=result.check_points,
        disclaimer=result.disclaimer,
        statement_type=result.statement_type,
        related_laws=result.related_laws,
        analyzed_at=analyzed_at,
    )
    if comment.analysis is None:
        comment.analysis = Analysis(**data)
    else:
        for key, value in data.items():
            setattr(comment.analysis, key, value)


def _call_and_validate(payload: list[dict], context: str | None, allowed_ids: set[str]) -> list[AnalysisResult]:
    raw = adapters.analyze_comments(payload, context)
    if not isinstance(raw, list):
        raise ValueError("판독 결과가 list가 아닙니다.")
    results = [AnalysisResult.model_validate(r) for r in raw]
    return [r for r in results if r.comment_id in allowed_ids]


@router.post("/cases/{case_id}/analyze", response_model=AnalyzeResponse)
def analyze(case_id: str, body: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    case = get_case_or_404(db, case_id)
    comments = db.scalars(
        select(Comment).where(Comment.case_id == case.id, Comment.id.in_(body.comment_ids)).order_by(Comment.seq)
    ).all()
    found = {c.id for c in comments}
    missing = [cid for cid in body.comment_ids if cid not in found]
    if missing:
        raise AppError(404, "NOT_FOUND", f"이 사건에 없는 댓글입니다: {', '.join(missing[:5])}")

    # 외부 AI에는 판독에 필요한 최소 정보(id, 본문)만 전달한다.
    payload = [{"comment_id": c.id, "content": c.content} for c in comments]
    contexts = list(dict.fromkeys(c.source.context for c in comments if c.source.context))
    context = "\n\n".join(contexts) if contexts else None

    results: list[AnalysisResult] | None = None
    last_error: Exception | None = None
    for _attempt in range(2):  # 검증 실패 시 한 번만 재시도
        try:
            results = _call_and_validate(payload, context, found)
            break
        except adapters.ModuleNotConnectedError as exc:
            raise AppError(503, "MODULE_NOT_CONNECTED", str(exc)) from exc
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            last_error = exc
        except Exception as exc:
            raise AppError(503, "ANALYSIS_UNAVAILABLE", f"AI 판독을 수행하지 못했습니다. ({safe_message(exc)})") from exc
    if results is None:
        raise AppError(502, "ANALYSIS_INVALID", f"AI 판독 결과 형식이 올바르지 않습니다. ({safe_message(last_error)})")
    if not results:
        raise AppError(502, "ANALYSIS_EMPTY", "AI 판독 결과가 비어 있습니다.")

    by_id = {c.id: c for c in comments}
    now = utcnow()
    for r in results:
        save_analysis(by_id[r.comment_id], r, now)
    db.commit()
    return AnalyzeResponse(results=results)


_CHUNK = 500  # SQLite 변수 개수 제한을 피하기 위한 IN 절 분할


@router.patch("/comments/bulk", response_model=BulkCommentResult)
def bulk_patch_comments(body: BulkCommentPatch, db: Session = Depends(get_db)) -> BulkCommentResult:
    """증거함 일괄 저장/해제. ``/comments/{comment_id}``보다 먼저 선언해야 경로가 겹치지 않는다."""
    missing: list[str] = []
    if body.level is not None:
        get_case_or_404(db, body.case_id or "")
        ids = list(
            db.scalars(
                select(Comment.id)
                .join(Analysis, Analysis.comment_id == Comment.id)
                .where(Comment.case_id == body.case_id, Analysis.level == body.level)
                .order_by(Comment.seq)
            )
        )
    else:
        requested = body.comment_ids or []
        query_ids: set[str] = set()
        for i in range(0, len(requested), _CHUNK):
            q = select(Comment.id).where(Comment.id.in_(requested[i : i + _CHUNK]))
            if body.case_id:
                q = q.where(Comment.case_id == body.case_id)
            query_ids.update(db.scalars(q))
        ids = [cid for cid in requested if cid in query_ids]
        missing = [cid for cid in requested if cid not in query_ids]
    for i in range(0, len(ids), _CHUNK):
        db.execute(update(Comment).where(Comment.id.in_(ids[i : i + _CHUNK])).values(saved=body.saved))
    db.commit()
    return BulkCommentResult(saved=body.saved, updated=len(ids), comment_ids=ids, missing=missing)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def patch_comment(comment_id: str, body: CommentPatch, db: Session = Depends(get_db)) -> Comment:
    comment = get_comment_or_404(db, comment_id)
    for field in body.model_fields_set:
        setattr(comment, field, getattr(body, field))
    db.commit()
    return comment
