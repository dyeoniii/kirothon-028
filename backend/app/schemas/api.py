"""Pydantic v2 스키마. 형식은 docs/api-contract.md 기준."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

DISCLAIMER = "AI 분석은 법률 자문이 아닙니다."

Level = Literal["legal_review", "needs_context", "low_risk"]
LEVEL_LABELS: dict[str, str] = {
    "legal_review": "법적 검토 필요",
    "needs_context": "추가 맥락 확인 필요",
    "low_risk": "낮은 위험 신호",
}


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_z, return_type=str, when_used="json")]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- 오류 ----------
class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------- 사건 ----------
class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title은 비워 둘 수 없습니다.")
        return v


class CaseOut(ORMModel):
    id: str
    title: str
    description: str | None
    created_at: UtcDatetime


class CaseSummary(BaseModel):
    id: str
    title: str
    created_at: UtcDatetime
    saved_count: int


# ---------- 분석 ----------
STATEMENT_TYPES = ("의견 표명", "사실 적시", "허위사실 의심", "해당 없음")
MAX_RELATED_LAWS = 2


class AnalysisBrief(ORMModel):
    level: Level
    level_label: str
    issues: list[str]
    flagged_phrases: list[str]
    reason: str
    check_points: list[str]
    disclaimer: str
    # 선택·참고용. 이전에 판독한 댓글에는 null.
    statement_type: str | None = None
    related_laws: list[str] | None = None


class AnalysisResult(BaseModel):
    """AI 판독 함수 반환값 검증용 + 응답 항목."""

    model_config = ConfigDict(extra="ignore")

    comment_id: str
    level: Level
    level_label: str = ""
    issues: list[str] = Field(default_factory=list)
    flagged_phrases: list[str] = Field(default_factory=list)
    reason: str = ""
    check_points: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    statement_type: str | None = None
    related_laws: list[str] | None = None

    @field_validator("statement_type", mode="before")
    @classmethod
    def _known_statement_type(cls, v):
        return v if isinstance(v, str) and v.strip() in STATEMENT_TYPES else None

    @field_validator("related_laws", mode="before")
    @classmethod
    def _laws_list(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            return None
        return [x.strip() for x in v if isinstance(x, str) and x.strip()][:MAX_RELATED_LAWS]

    @model_validator(mode="after")
    def _normalize(self) -> "AnalysisResult":
        if not self.level_label:
            self.level_label = LEVEL_LABELS[self.level]
        self.disclaimer = DISCLAIMER  # 고지는 서버에서 고정
        return self


class AnalyzeRequest(BaseModel):
    comment_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("comment_ids")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class AnalyzeResponse(BaseModel):
    results: list[AnalysisResult]


class LevelCounts(BaseModel):
    legal_review: int = 0
    needs_context: int = 0
    low_risk: int = 0


class AnalyzeAllStatus(BaseModel):
    """전체 자동 판독 진행 상황. 개수는 DB의 실제 판독 결과에서 센다."""

    case_id: str
    running: bool
    stopping: bool = False  # 중단 요청을 받고 진행 중인 배치를 마무리하는 중
    total: int
    analyzed: int
    pending: int
    failed: int = 0  # 이번 실행에서 판독하지 못한 댓글 수(다시 실행하면 재시도)
    run_total: int = 0  # 가장 최근 실행의 대상 수(force 실행이면 이미 판독된 댓글 포함)
    run_done: int = 0  # 가장 최근 실행에서 결과가 저장된 수
    counts: LevelCounts
    message: str | None = None  # 속도 제한 대기·실패 안내
    error: str | None = None


# ---------- 소스/댓글 ----------
class SourceOut(ORMModel):
    id: str
    type: Literal["youtube", "text", "image", "url_only"]
    url: str | None
    file_sha256: str | None
    collected_at: UtcDatetime
    needs_manual_input: bool
    message: str | None
    context: str | None = None


class CommentOut(ORMModel):
    id: str
    source_id: str
    author: str | None
    content: str
    posted_at: str | None
    comment_url: str | None
    platform: str
    like_count: int | None
    parent_id: str | None
    saved: bool
    user_note: str | None
    user_confirmed: bool
    analysis: AnalysisBrief | None = None


class CommentPatch(BaseModel):
    """content 등 원문 필드는 받지 않는다(extra=forbid)."""

    model_config = ConfigDict(extra="forbid")

    saved: bool | None = None
    user_note: str | None = Field(default=None, max_length=5000)
    user_confirmed: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "CommentPatch":
        if not self.model_fields_set:
            raise ValueError("saved, user_note, user_confirmed 중 하나 이상이 필요합니다.")
        return self


class BulkCommentPatch(BaseModel):
    """여러 댓글의 증거함 저장 상태를 한 번에 바꾼다. user_confirmed·메모는 건드리지 않는다.

    대상은 ``comment_ids`` 또는 (``case_id`` + ``level``) 중 하나로 지정한다.
    """

    model_config = ConfigDict(extra="forbid")
    saved: bool
    comment_ids: list[str] | None = Field(default=None, min_length=1, max_length=20000)
    case_id: str | None = Field(default=None, max_length=64)
    level: Level | None = None

    @model_validator(mode="after")
    def _one_target(self) -> "BulkCommentPatch":
        by_ids = self.comment_ids is not None
        by_level = self.level is not None
        if by_ids == by_level:
            raise ValueError("comment_ids 또는 level(+case_id) 중 하나만 지정해야 합니다.")
        if by_level and not self.case_id:
            raise ValueError("level로 지정할 때는 case_id가 필요합니다.")
        if by_ids:
            self.comment_ids = list(dict.fromkeys(self.comment_ids or []))
        return self


class BulkCommentResult(BaseModel):
    saved: bool
    updated: int
    comment_ids: list[str]
    missing: list[str] = Field(default_factory=list)


# ---------- 입력 ----------
class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    source_url: str | None = Field(default=None, max_length=2048)
    context: str | None = Field(default=None, max_length=5000)


class UrlInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class InputResponse(BaseModel):
    source: SourceOut
    comments: list[CommentOut]
    # YouTube 입력에서만 채워짐. 전체 댓글 수(videos.list commentCount)와 한도 초과 안내.
    total_available: int | None = None
    notice: str | None = None


# ---------- 사건 상세 ----------
class AnswerOut(ORMModel):
    question_id: str
    answer: str
    updated_at: UtcDatetime


class CaseDetail(ORMModel):
    id: str
    title: str
    description: str | None
    created_at: UtcDatetime
    sources: list[SourceOut]
    comments: list[CommentOut]
    answers: list[AnswerOut]


# ---------- 증거 보완 ----------
class AnswerIn(BaseModel):
    question_id: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=5000)

    @field_validator("question_id")
    @classmethod
    def _strip_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question_id는 비워 둘 수 없습니다.")
        return v


class AnswersRequest(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1, max_length=50)


class ChecklistItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item: str
    status: Literal["ok", "partial", "missing"]
    detail: str | None = None


class ReviewQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    question: str


class ReviewResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    completeness: int = Field(ge=0, le=100)
    checklist: list[ChecklistItem]
    questions: list[ReviewQuestion]


class HealthResponse(BaseModel):
    status: str = "ok"
