"""증거 보완: 체크리스트/질문 및 사용자 추가 답변."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api import adapters
from app.api.common import get_case_or_404
from app.api.errors import AppError, safe_message
from app.db import get_db
from app.models import Answer, Case, utcnow
from app.schemas import AnswersRequest, ReviewResponse

router = APIRouter(prefix="/cases/{case_id}/agent", tags=["agent"])


def _build_evidence(case: Case) -> list[dict]:
    """저장된(saved) 댓글만 증거로 전달."""
    evidence = []
    for c in case.comments:
        if not c.saved:
            continue
        a = c.analysis
        evidence.append(
            {
                "comment_id": c.id,
                "source_id": c.source_id,
                "source_type": c.source.type,
                "source_url": c.source.url,
                "file_sha256": c.source.file_sha256,
                "collected_at": c.source.collected_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "platform": c.platform,
                "author": c.author,
                "content": c.content,
                "posted_at": c.posted_at,
                "comment_url": c.comment_url,
                "user_note": c.user_note,
                "user_confirmed": c.user_confirmed,
                "analysis": None
                if a is None
                else {
                    "level": a.level,
                    "level_label": a.level_label,
                    "issues": a.issues,
                    "flagged_phrases": a.flagged_phrases,
                    "reason": a.reason,
                    "check_points": a.check_points,
                },
            }
        )
    return evidence


def _run_review(case: Case) -> ReviewResponse:
    answers = [{"question_id": a.question_id, "answer": a.answer} for a in case.answers]
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            return ReviewResponse.model_validate(adapters.review_evidence(_build_evidence(case), answers))
        except adapters.ModuleNotConnectedError as exc:
            raise AppError(503, "MODULE_NOT_CONNECTED", str(exc)) from exc
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            last_error = exc
        except Exception as exc:
            raise AppError(503, "REVIEW_UNAVAILABLE", f"증거 점검을 수행하지 못했습니다. ({safe_message(exc)})") from exc
    raise AppError(502, "REVIEW_INVALID", f"증거 점검 결과 형식이 올바르지 않습니다. ({safe_message(last_error)})")


@router.post("/review", response_model=ReviewResponse)
def review(case_id: str, db: Session = Depends(get_db)) -> ReviewResponse:
    return _run_review(get_case_or_404(db, case_id))


@router.post("/answers", response_model=ReviewResponse)
def save_answers(case_id: str, body: AnswersRequest, db: Session = Depends(get_db)) -> ReviewResponse:
    case = get_case_or_404(db, case_id)
    existing = {a.question_id: a for a in case.answers}
    now = utcnow()
    for item in body.answers:
        if item.question_id in existing:
            existing[item.question_id].answer = item.answer
            existing[item.question_id].updated_at = now
        else:
            case.answers.append(Answer(question_id=item.question_id, answer=item.answer, updated_at=now))
    db.commit()
    return _run_review(case)
