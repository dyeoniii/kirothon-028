from app.analysis.agent_review import BASE_QUESTIONS, review_evidence

FULL = {
    "id": "cmt_1",
    "content": "가상 댓글",
    "author": "가상계정",
    "posted_at": "2026-11-14T03:00:00Z",
    "comment_url": "https://www.youtube.com/watch?v=AAAAAAAAAAA&lc=x",
    "user_confirmed": True,
    "analysis": {"level": "legal_review"},
    "source": {"type": "youtube", "url": "https://www.youtube.com/watch?v=AAAAAAAAAAA", "collected_at": "2026-11-14T03:05:00Z"},
}
BARE = {
    "id": "cmt_2",
    "content": "가상 스크린샷 댓글",
    "author": None,
    "posted_at": None,
    "comment_url": None,
    "user_confirmed": False,
    "analysis": None,
    "source": {"type": "image", "url": None, "collected_at": "2026-11-14T03:06:00Z", "file_sha256": None},
}


def _item(res, name):
    return next(c for c in res["checklist"] if c["item"] == name)


def test_shape_and_no_evidence():
    r = review_evidence([], [])
    assert set(r) == {"completeness", "checklist", "questions"}
    assert r["completeness"] == 0
    assert _item(r, "저장된 증거")["status"] == "missing"
    assert {q["id"] for q in r["questions"]} == {q[0] for q in BASE_QUESTIONS}
    for c in r["checklist"]:
        assert set(c) == {"item", "status", "detail"} and c["status"] in ("ok", "partial", "missing")


def test_partial_counts():
    r = review_evidence([FULL, BARE], [])
    assert _item(r, "작성자 정보") == {"item": "작성자 정보", "status": "partial", "detail": "2건 중 1건 작성자 미확인"}
    assert _item(r, "원본 게시글 URL")["status"] == "partial"
    assert _item(r, "수집 시각·원본 해시")["status"] == "partial"  # 이미지인데 SHA 없음
    ids = {q["id"] for q in r["questions"]}
    assert {"q6", "q7"} <= ids


def test_answers_raise_completeness_and_remove_questions():
    before = review_evidence([FULL], [])
    answers = [{"question_id": q[0], "answer": "가상 답변"} for q in BASE_QUESTIONS]
    after = review_evidence([FULL], answers)
    assert after["completeness"] == 100 > before["completeness"]
    assert after["questions"] == []


def test_flat_api_evidence_shape():
    """S3 api/agent.py가 보내는 평면 dict 형식."""
    flat = {
        "comment_id": "cmt_9", "source_type": "image", "source_url": None, "file_sha256": "ab" * 32,
        "collected_at": "2026-11-14T03:06:00Z", "platform": "image", "author": None, "content": "가상",
        "posted_at": None, "comment_url": None, "user_confirmed": True, "analysis": None,
    }
    r = review_evidence([flat], [])
    assert _item(r, "수집 시각·원본 해시")["status"] == "ok"
    assert _item(r, "원본 게시글 URL")["status"] == "missing"


def test_matches_api_schema_if_available():
    import pytest

    schemas = pytest.importorskip("app.schemas")
    r = review_evidence([FULL, BARE], [{"question_id": "q1", "answer": "가상"}])
    schemas.ReviewResponse.model_validate(r)


def test_blank_and_unknown_answers_ignored():
    r = review_evidence([FULL], [{"question_id": "q1", "answer": "  "}, {"question_id": "zz", "answer": "x"}, "bad"])
    assert "q1" in {q["id"] for q in r["questions"]}
    assert 0 <= r["completeness"] <= 100
