"""증거 보완 체크리스트·질문 (S4 [AI]).

P0는 템플릿 기반(LLM 호출 없음, 키 불필요, provider와 무관하게 동일 결과).
``completeness``는 서비스 체크 항목 중 '완료(ok)' 비율(0~100 정수)이며
법적 충분성·소송 결과와 무관하다.
"""
from __future__ import annotations

__all__ = ["review_evidence", "BASE_QUESTIONS"]

# 사용자 사실 확인 질문(고정 ID). 답변은 API가 저장하고 다음 호출 때 answers로 전달.
BASE_QUESTIONS: list[tuple[str, str, str]] = [
    ("q1", "피해 내용", "이 댓글들로 실제 어떤 피해(정신적 고통, 업무·생활 지장 등)가 있었나요?"),
    ("q2", "대상 특정 여부", "댓글이 본인을 가리킨다는 것을 다른 사람이 알 수 있는 근거(이름, 사진, 계정 언급 등)가 있나요?"),
    ("q3", "공개 범위", "댓글이 달린 게시물은 누가 볼 수 있었나요? (전체 공개, 팔로워 한정 등)"),
    ("q4", "최초 인지 시점", "이 댓글을 처음 알게 된 날짜와 경위를 알려주세요."),
    ("q5", "작성자와의 관계·반복 여부", "작성자와 아는 사이인가요? 같은 작성자가 다른 곳에도 반복해서 글을 남겼나요?"),
]
_Q_AUTHOR = ("q6", "작성자 정보 보완", "작성자 정보가 없는 증거가 있습니다. 작성자 계정명이나 프로필 주소를 확인할 수 있나요?")
_Q_URL = ("q7", "원본 URL 보완", "원본 게시물 URL이 없는 증거가 있습니다. 게시물 주소를 알고 있다면 알려주세요.")


def _get(ev: dict, key: str):
    """증거 dict 또는 중첩 source dict에서 값을 찾는다."""
    if ev.get(key) not in (None, ""):
        return ev.get(key)
    src = ev.get("source")
    if isinstance(src, dict) and src.get(key) not in (None, ""):
        return src.get(key)
    return None


def _count_item(name: str, evidence: list[dict], has, missing_hint: str) -> dict:
    total = len(evidence)
    ok = sum(1 for e in evidence if has(e))
    if total == 0:
        return {"item": name, "status": "missing", "detail": "저장된 증거가 없습니다."}
    if ok == total:
        return {"item": name, "status": "ok", "detail": f"{total}건 모두 기록됨"}
    status = "partial" if ok else "missing"
    return {"item": name, "status": status, "detail": f"{total}건 중 {total - ok}건 {missing_hint}"}


def _answer_map(answers: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        qid = a.get("question_id")
        text = a.get("answer")
        if isinstance(qid, str) and isinstance(text, str) and text.strip():
            out[qid] = text.strip()
    return out


def review_evidence(evidence: list[dict], answers: list[dict]) -> dict:
    """저장된 증거와 사용자 답변으로 체크리스트·추가 질문·작성률을 만든다.

    ``evidence``: 저장(saved=true)된 댓글 dict 목록. 사용하는 키(없으면 미기입 처리):
    ``author``, ``posted_at``(또는 ``posted_at_text``), ``comment_url``, ``analysis``,
    ``user_confirmed``, ``source_type``/``platform``, 그리고
    ``source_url``/``collected_at``/``file_sha256``/``type``(최상위 또는 ``source`` 하위 dict).
    checklist status는 ``ok | partial | missing``.
    ``answers``: ``[{"question_id": "q1", "answer": "..."}]``.
    반환: ``{"completeness": int, "checklist": [...], "questions": [{"id", "question"}]}``
    ``questions``에는 아직 답하지 않은 질문만 포함된다.
    """
    evidence = [e for e in (evidence or []) if isinstance(e, dict)]
    answered = _answer_map(answers)

    def has_url(e: dict) -> bool:
        return bool(e.get("comment_url") or e.get("source_url") or _get(e, "url"))

    def has_record(e: dict) -> bool:
        if not _get(e, "collected_at"):
            return False
        if "image" in (_get(e, "type"), e.get("source_type"), e.get("platform")):
            return bool(_get(e, "file_sha256"))
        return True

    checklist: list[dict] = [
        {
            "item": "저장된 증거",
            "status": "ok" if evidence else "missing",
            "detail": f"{len(evidence)}건 저장됨" if evidence else "증거함에 저장된 댓글이 없습니다.",
        },
        _count_item("작성자 정보", evidence, lambda e: bool(e.get("author")), "작성자 미확인"),
        _count_item(
            "작성 시각", evidence, lambda e: bool(e.get("posted_at") or e.get("posted_at_text")), "작성 시각 미확인"
        ),
        _count_item("원본 게시글 URL", evidence, has_url, "누락"),
        _count_item("수집 시각·원본 해시", evidence, has_record, "수집 기록 누락"),
        _count_item("사용자 내용 확인", evidence, lambda e: bool(e.get("user_confirmed")), "미확인"),
        _count_item("AI 판독", evidence, lambda e: bool(e.get("analysis")), "판독 전"),
    ]

    questions = list(BASE_QUESTIONS)
    if evidence and any(not e.get("author") for e in evidence):
        questions.append(_Q_AUTHOR)
    if evidence and any(not has_url(e) for e in evidence):
        questions.append(_Q_URL)

    for qid, item, _ in BASE_QUESTIONS:
        checklist.append(
            {
                "item": item,
                "status": "ok" if qid in answered else "missing",
                "detail": "답변 작성됨" if qid in answered else "답변 필요",
            }
        )

    done = sum(1 for c in checklist if c["status"] == "ok")
    completeness = round(100 * done / len(checklist)) if checklist else 0

    return {
        "completeness": completeness,
        "checklist": checklist,
        "questions": [{"id": qid, "question": q} for qid, _, q in questions if qid not in answered],
    }
