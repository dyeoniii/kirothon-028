"""입력 → 댓글 추출 (텍스트 / 이미지 / URL)."""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import adapters
from app.api.common import get_case_or_404
from app.api.errors import AppError, safe_message
from app.db import get_db, get_storage_dir
from app.models import Case, Comment, Source, new_id, utcnow
from app.schemas import InputResponse, TextInput, UrlInput

logger = logging.getLogger("akpleguard.api")
router = APIRouter(prefix="/cases/{case_id}/inputs", tags=["inputs"])

DEFAULT_YOUTUBE_MAX_COMMENTS = 10000
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MANUAL_HINT = "텍스트 붙여넣기 또는 스크린샷 업로드로 직접 입력해 주세요."


# ---------------------------------------------------------------- helpers
def _max_upload_bytes() -> int:
    try:
        mb = float(os.getenv("MAX_UPLOAD_MB", "10"))
    except ValueError:
        mb = 10.0
    return int(mb * 1024 * 1024)


def youtube_limit() -> int:
    """환경변수 YOUTUBE_MAX_COMMENTS. 기본 10000, 0이면 무제한(0)."""
    raw = (os.getenv("YOUTUBE_MAX_COMMENTS") or "").strip()
    if not raw:
        return DEFAULT_YOUTUBE_MAX_COMMENTS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_YOUTUBE_MAX_COMMENTS
    return value if value >= 0 else DEFAULT_YOUTUBE_MAX_COMMENTS


def _sniff_image(data: bytes) -> tuple[str, str] | None:
    """(mime, ext). 확장자/Content-Type이 아니라 실제 바이트로 판별."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def _clean_url(url: str | None) -> str | None:
    """선택 입력 URL 검증(http/https). 비어 있으면 None."""
    if url is None or not url.strip():
        return None
    try:
        adapters.detect_platform_and_id(url.strip())
    except ValueError as exc:
        raise AppError(400, "VALIDATION_ERROR", f"올바른 URL이 아닙니다: {exc}") from exc
    except Exception as exc:
        raise AppError(503, "MODULE_ERROR", f"URL 검사 모듈 오류: {safe_message(exc)}") from exc
    return url.strip()


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value)
    return text if text.strip() else None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _next_seq(db: Session, case_id: str) -> int:
    current = db.scalar(select(func.max(Comment.seq)).where(Comment.case_id == case_id))
    return (current or 0) + 1


def _persist(
    db: Session,
    case: Case,
    source: Source,
    items: list[dict],
    platform: str,
) -> InputResponse:
    """원문(content)은 그대로 저장한다. content가 비었거나 문자열이 아닌 항목은 제외."""
    source.case_id = case.id
    db.add(source)
    db.flush()
    seq = _next_seq(db, case.id)
    comments: list[Comment] = []
    for item in items:
        content = item.get("content") if isinstance(item, dict) else None
        if not isinstance(content, str) or not content.strip():
            continue
        comment = Comment(
            case_id=case.id,
            source_id=source.id,
            seq=seq,
            author=_str_or_none(item.get("author")),
            content=content,
            posted_at=_str_or_none(item.get("posted_at")),
            comment_url=_str_or_none(item.get("comment_url")),
            platform=platform,
            like_count=_int_or_none(item.get("like_count")),
            parent_id=_str_or_none(item.get("parent_id")),
        )
        seq += 1
        db.add(comment)
        comments.append(comment)
    db.commit()
    return InputResponse.model_validate({"source": source, "comments": comments}, from_attributes=True)


# ---------------------------------------------------------------- text
@router.post("/text", response_model=InputResponse)
def input_text(case_id: str, body: TextInput, db: Session = Depends(get_db)) -> InputResponse:
    case = get_case_or_404(db, case_id)
    source_url = _clean_url(body.source_url)
    lines = [ln.strip() for ln in body.text.splitlines() if ln.strip()]
    if not lines:
        raise AppError(400, "VALIDATION_ERROR", "댓글로 분리할 텍스트가 없습니다.")
    source = Source(
        type="text",
        url=source_url,
        context=body.context.strip() if body.context and body.context.strip() else None,
        collected_at=utcnow(),
    )
    return _persist(db, case, source, [{"content": ln} for ln in lines], platform="text")


# ---------------------------------------------------------------- image
@router.post("/image", response_model=InputResponse)
async def input_image(
    case_id: str,
    file: UploadFile = File(...),
    source_url: str | None = Form(default=None),
    context: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> InputResponse:
    case = get_case_or_404(db, case_id)
    if context and len(context) > 5000:
        raise AppError(400, "VALIDATION_ERROR", "context는 5000자 이하여야 합니다.")
    clean_url = _clean_url(source_url)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXTS:
        raise AppError(400, "VALIDATION_ERROR", "png, jpg, jpeg, webp 이미지만 업로드할 수 있습니다.")
    limit = _max_upload_bytes()
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "FILE_TOO_LARGE", f"이미지는 {limit // (1024 * 1024)}MB 이하여야 합니다.")
    if not data:
        raise AppError(400, "VALIDATION_ERROR", "빈 파일입니다.")
    sniffed = _sniff_image(data)
    if sniffed is None:
        raise AppError(400, "VALIDATION_ERROR", "이미지 형식(png, jpg, webp)을 확인할 수 없습니다.")
    mime, store_ext = sniffed

    sha256 = hashlib.sha256(data).hexdigest()
    collected_at = utcnow()

    try:
        extracted = adapters.extract_comments_from_image(data, mime)
    except adapters.ModuleNotConnectedError as exc:
        raise AppError(503, "MODULE_NOT_CONNECTED", f"{exc} {MANUAL_HINT}") from exc
    except Exception as exc:
        raise AppError(503, "EXTRACTION_FAILED", f"이미지에서 댓글을 추출하지 못했습니다. ({safe_message(exc)}) {MANUAL_HINT}") from exc
    if not isinstance(extracted, list):
        raise AppError(502, "EXTRACTION_INVALID", "이미지 추출 결과 형식이 올바르지 않습니다.")

    source = Source(
        type="image",
        url=clean_url,
        file_sha256=sha256,
        mime_type=mime,
        context=context.strip() if context and context.strip() else None,
        collected_at=collected_at,
    )
    source.id = new_id("src")
    rel_path = f"{case.id}/{source.id}{store_ext}"
    target = get_storage_dir() / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)  # 원본 그대로 저장
    source.file_path = rel_path
    try:
        result = _persist(db, case, source, extracted, platform="image")
    except Exception:
        db.rollback()
        target.unlink(missing_ok=True)
        raise
    if not result.comments:
        source.needs_manual_input = True
        source.message = "이미지에서 댓글을 찾지 못했습니다. " + MANUAL_HINT
        db.commit()
        result = InputResponse.model_validate({"source": source, "comments": []}, from_attributes=True)
    return result


# ---------------------------------------------------------------- url
@router.post("/url", response_model=InputResponse)
def input_url(case_id: str, body: UrlInput, db: Session = Depends(get_db)) -> InputResponse:
    case = get_case_or_404(db, case_id)
    url = body.url.strip()
    try:
        info = adapters.detect_platform_and_id(url)
    except ValueError as exc:
        raise AppError(400, "VALIDATION_ERROR", f"올바른 http/https URL이 아닙니다. ({exc})") from exc
    except Exception as exc:
        raise AppError(503, "MODULE_ERROR", f"URL 검사 모듈 오류: {safe_message(exc)}") from exc

    video_id = info.get("video_id") if isinstance(info, dict) else None
    if not (isinstance(info, dict) and info.get("platform") == "youtube" and video_id):
        # 그 외 플랫폼은 스크래핑 없이 출처 URL만 저장
        source = Source(
            type="url_only",
            url=url,
            needs_manual_input=True,
            message="이 플랫폼은 자동 수집을 지원하지 않아 출처 URL만 저장했습니다. " + MANUAL_HINT,
            collected_at=utcnow(),
        )
        return _persist(db, case, source, [], platform="url_only")

    limit = youtube_limit()
    total_available: int | None = None
    try:
        total_available = adapters.fetch_youtube_comment_count(video_id)
    except Exception as exc:  # 개수 조회 실패는 수집을 막지 않는다(수집 단계에서 같은 원인이면 오류가 난다).
        logger.warning("YouTube commentCount lookup failed: %s", safe_message(exc))
    if not isinstance(total_available, int) or isinstance(total_available, bool) or total_available < 0:
        total_available = None
    try:
        fetched = adapters.fetch_youtube_comments(video_id, limit)
    except adapters.ModuleNotConnectedError as exc:
        raise AppError(503, "MODULE_NOT_CONNECTED", f"{exc} {MANUAL_HINT}") from exc
    except Exception as exc:
        raise AppError(503, "YOUTUBE_UNAVAILABLE", f"YouTube 댓글을 가져오지 못했습니다. ({safe_message(exc)}) {MANUAL_HINT}") from exc
    if not isinstance(fetched, list):
        raise AppError(502, "COLLECTOR_INVALID", "YouTube 수집 결과 형식이 올바르지 않습니다.")

    notice = None
    if limit > 0 and total_available is not None and total_available > limit:
        notice = f"댓글이 {total_available:,}개라 최근 {limit:,}개만 분석합니다"
    source = Source(type="youtube", url=url, collected_at=utcnow(), message=notice)
    result = _persist(db, case, source, fetched if limit == 0 else fetched[:limit], platform="youtube")
    result.total_available = total_available
    result.notice = notice
    if not result.comments:
        source.needs_manual_input = True
        source.message = "가져온 댓글이 없습니다(댓글 없음 또는 비공개). " + MANUAL_HINT
        db.commit()
        result = InputResponse.model_validate(
            {"source": source, "comments": [], "total_available": total_available, "notice": None},
            from_attributes=True,
        )
    return result
