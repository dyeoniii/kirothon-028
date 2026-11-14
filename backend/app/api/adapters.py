"""다른 세션([AI] collectors/analysis, [DOC] documents) 함수 연결 지점.

docs/internal-interfaces.md의 import 경로·시그니처를 그대로 사용한다.
해당 모듈이 아직 없으면(ModuleNotFoundError) 이 파일의 stub으로 대체되며,
실제 모듈이 병합되면 코드 수정 없이 자동으로 실제 함수가 호출된다.
없는 사실을 만들어내야 하는 기능(댓글 수집/이미지 추출/AI 판독/PDF)의 stub은
가짜 결과를 반환하지 않고 ModuleNotConnectedError를 발생시킨다.
"""
from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

# name -> (module path, stub). 실제 구현이 있으면 모듈 함수를 사용.
_TARGETS: dict[str, str] = {
    "detect_platform_and_id": "app.collectors.url_detect",
    "fetch_youtube_comments": "app.collectors.youtube",
    "fetch_youtube_comment_count": "app.collectors.youtube",
    "extract_comments_from_image": "app.analysis.extract_image",
    "analyze_comments": "app.analysis.classify",
    "review_evidence": "app.analysis.agent_review",
    "generate_statement_pdf": "app.documents.pdf",
    "generate_evidence_list_pdf": "app.documents.pdf",
}


class ModuleNotConnectedError(RuntimeError):
    """담당 세션 모듈이 아직 연결되지 않음."""


# ---------------------------------------------------------------- stubs
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _stub_detect_platform_and_id(url: str) -> dict:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("http/https URL만 지원합니다.")
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    video_id = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0] or None
    elif host in ("youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            video_id = (parse_qs(parsed.query).get("v") or [None])[0]
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else None
    if video_id is not None and not _YT_ID.match(video_id):
        raise ValueError("올바른 YouTube 영상 ID가 아닙니다.")
    platform = "youtube" if video_id else "other"
    return {"platform": platform, "video_id": video_id, "normalized_url": url.strip()}


def _not_connected(feature: str) -> Callable[..., Any]:
    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise ModuleNotConnectedError(f"{feature} 모듈이 아직 연결되지 않았습니다.")

    return _raise


_REVIEW_QUESTIONS = [
    ("q1", "실제 어떤 피해가 있었나요?"),
    ("q2", "댓글 작성자를 알고 계신가요? 알고 있다면 어떻게 알게 되었나요?"),
    ("q3", "댓글이 삭제되거나 수정된 적이 있나요?"),
]


def _stub_review_evidence(evidence: list[dict], answers: list[dict]) -> dict:
    """실제 저장 데이터로 계산하는 템플릿 체크리스트(서비스 내 기입률)."""
    total = len(evidence)

    def status(count: int) -> str:
        if total == 0 or count == 0:
            return "missing"
        return "ok" if count == total else "partial"

    def row(item: str, count: int) -> dict:
        detail = "저장된 증거 없음" if total == 0 else f"{total}건 중 {count}건 확인"
        return {"item": item, "status": status(count), "detail": detail}

    checklist = [
        row("원본 게시글/출처 URL", sum(1 for e in evidence if e.get("source_url"))),
        row("댓글 작성자", sum(1 for e in evidence if e.get("author"))),
        row("댓글 작성 시각", sum(1 for e in evidence if e.get("posted_at"))),
        row("AI 판독 완료", sum(1 for e in evidence if e.get("analysis"))),
        row("내용 확인(사용자)", sum(1 for e in evidence if e.get("user_confirmed"))),
    ]
    answered = {a["question_id"] for a in answers}
    done = sum(1 for qid, _ in _REVIEW_QUESTIONS if qid in answered)
    checklist.append(
        {
            "item": "추가 질문 답변",
            "status": "ok" if done == len(_REVIEW_QUESTIONS) else ("partial" if done else "missing"),
            "detail": f"{len(_REVIEW_QUESTIONS)}개 중 {done}개 답변",
        }
    )
    completeness = round(100 * sum(1 for c in checklist if c["status"] == "ok") / len(checklist))
    questions = [{"id": qid, "question": q} for qid, q in _REVIEW_QUESTIONS if qid not in answered]
    return {"completeness": completeness, "checklist": checklist, "questions": questions}


_STUBS: dict[str, Callable[..., Any]] = {
    "detect_platform_and_id": _stub_detect_platform_and_id,
    "fetch_youtube_comments": _not_connected("YouTube 댓글 수집"),
    # 전체 댓글 수를 알 수 없으면 None(수를 지어내지 않음)
    "fetch_youtube_comment_count": lambda video_id: None,
    "extract_comments_from_image": _not_connected("이미지 댓글 추출"),
    "analyze_comments": _not_connected("AI 판독"),
    "review_evidence": _stub_review_evidence,
    "generate_statement_pdf": _not_connected("사건 경위서 PDF"),
    "generate_evidence_list_pdf": _not_connected("증거 목록 PDF"),
}


def _resolve(name: str) -> tuple[Callable[..., Any], bool]:
    """(함수, 실제 모듈 여부). 모듈 자체가 없을 때만 stub 사용, 그 외 import 오류는 그대로 노출."""
    module_path = _TARGETS[name]
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        if exc.name and (module_path == exc.name or module_path.startswith(exc.name + ".")):
            return _STUBS[name], False
        raise
    func = getattr(module, name, None)
    if func is None:
        return _STUBS[name], False
    return func, True


def adapter_status() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in _TARGETS:
        try:
            _, real = _resolve(name)
            result[name] = "real" if real else "stub"
        except Exception as exc:  # 실제 모듈 import 오류도 진단에 노출
            result[name] = f"error: {type(exc).__name__}"
    return result


# ------------------------------------------------- internal-interfaces.md 시그니처
def detect_platform_and_id(url: str) -> dict:
    return _resolve("detect_platform_and_id")[0](url)


def fetch_youtube_comments(video_id: str, limit: int | None = None) -> list[dict]:
    """limit: None=환경변수 YOUTUBE_MAX_COMMENTS, 0=무제한."""
    return _resolve("fetch_youtube_comments")[0](video_id, limit)


def fetch_youtube_comment_count(video_id: str) -> int | None:
    return _resolve("fetch_youtube_comment_count")[0](video_id)


def extract_comments_from_image(image_bytes: bytes, mime_type: str) -> list[dict]:
    return _resolve("extract_comments_from_image")[0](image_bytes, mime_type)


def analyze_comments(comments: list[dict], context: str | None = None) -> list[dict]:
    return _resolve("analyze_comments")[0](comments, context)


def review_evidence(evidence: list[dict], answers: list[dict]) -> dict:
    return _resolve("review_evidence")[0](evidence, answers)


def generate_statement_pdf(case_data: dict) -> bytes:
    return _resolve("generate_statement_pdf")[0](case_data)


def generate_evidence_list_pdf(case_data: dict) -> bytes:
    return _resolve("generate_evidence_list_pdf")[0](case_data)
