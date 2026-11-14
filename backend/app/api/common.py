from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.errors import AppError
from app.models import Case, Comment
from app.schemas import CaseDetail


def get_case_or_404(db: Session, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise AppError(404, "NOT_FOUND", "사건을 찾을 수 없습니다.")
    return case


def get_comment_or_404(db: Session, comment_id: str) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise AppError(404, "NOT_FOUND", "댓글을 찾을 수 없습니다.")
    return comment


def mask_author(name: str | None) -> str | None:
    """작성자 가리기: 앞 1글자 + '**'. 앞의 '@'는 유지한다(예: '@정수진' → '@정**'). 값이 없으면 그대로."""
    if name is None or not name.strip():
        return name
    text = name.strip()
    prefix = "@" if text.startswith("@") else ""
    rest = text[len(prefix):]
    return f"{prefix}{rest[0]}**" if rest else name


def case_detail_dict(case: Case, saved_only: bool = False, mask_authors: bool = False) -> dict:
    """GET /cases/{id} 와 같은 JSON형 dict. saved_only면 저장된 댓글과 해당 소스만 포함."""
    data = CaseDetail.model_validate(case).model_dump(mode="json")
    if saved_only:
        data["comments"] = [c for c in data["comments"] if c["saved"]]
        used = {c["source_id"] for c in data["comments"]}
        data["sources"] = [s for s in data["sources"] if s["id"] in used]
    if mask_authors:  # 출력용 사본만 바꾼다. DB 원본은 그대로.
        for c in data["comments"]:
            c["author"] = mask_author(c["author"])
    return data
