"""판독 중단, 증거함 일괄 저장, 작성자 가리기(PDF) 테스트. 모든 데이터는 가상."""
import threading
import time

import pytest

from app.api import adapters
from app.api.common import mask_author
from tests.test_analyze_all import fake_analyze, make_lines, wait_done
from tests.test_api import PDF, add_text, mk_case


# ---------------------------------------------------------------- B-1 stop
def test_stop_finishes_running_batches_and_skips_the_rest_then_resumes(client, monkeypatch):
    gate = threading.Event()
    lock = threading.Lock()
    state = {"calls": 0}

    def analyzer(comments, context=None):
        with lock:
            state["calls"] += 1
        gate.wait(10)
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(250))  # 15개 배치 17개, 동시 2개
    client.post(f"/api/cases/{cid}/analyze-all")
    deadline = time.time() + 5
    while state["calls"] < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert state["calls"] == 2

    r = client.post(f"/api/cases/{cid}/analyze-all/stop")
    assert r.status_code == 200 and r.json()["running"] is True and r.json()["stopping"] is True
    gate.set()
    s = wait_done(client, cid)
    assert state["calls"] == 2  # 새 배치는 시작하지 않음
    assert s["analyzed"] == 30 and s["pending"] == 220 and s["failed"] == 0 and s["stopping"] is False
    assert "중단" in s["message"] and "220" in s["message"]

    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)  # 이어서 판독
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["analyzed"] == 250 and s["pending"] == 0 and s["message"] is None


def test_stop_when_idle_or_unknown_case(client):
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/analyze-all/stop")
    assert r.status_code == 200 and r.json()["running"] is False and r.json()["stopping"] is False
    assert client.post("/api/cases/nope/analyze-all/stop").status_code == 404


# ---------------------------------------------------------------- B-2 bulk save
def analyzed_case(client, monkeypatch, n=6):
    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)
    cid = mk_case(client)
    comments = add_text(client, cid, make_lines(n))["comments"]  # i%3: 0 legal, 1 needs_context, 2 low
    client.post(f"/api/cases/{cid}/analyze-all")
    wait_done(client, cid)
    return cid, comments


def saved_ids(client, cid):
    return {c["id"] for c in client.get(f"/api/cases/{cid}").json()["comments"] if c["saved"]}


def test_bulk_save_by_level_keeps_confirmation_state(client, monkeypatch):
    cid, comments = analyzed_case(client, monkeypatch)
    legal = [c["id"] for i, c in enumerate(comments) if i % 3 == 0]
    client.patch(f"/api/comments/{legal[0]}", json={"user_confirmed": True, "user_note": "내가 확인"})

    r = client.patch("/api/comments/bulk", json={"case_id": cid, "level": "legal_review", "saved": True})
    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == 2 and sorted(body["comment_ids"]) == sorted(legal) and body["missing"] == []
    assert saved_ids(client, cid) == set(legal)

    detail = {c["id"]: c for c in client.get(f"/api/cases/{cid}").json()["comments"]}
    assert detail[legal[0]]["user_confirmed"] is True and detail[legal[0]]["user_note"] == "내가 확인"  # 그대로
    assert detail[legal[1]]["user_confirmed"] is False  # 일괄 저장은 '사용자 확인 전' 상태
    assert detail[legal[1]]["content"] == comments[3]["content"]  # 원문 불변
    assert client.get("/api/cases").json()[0]["saved_count"] == 2


def test_bulk_save_by_ids_reports_missing_and_can_unsave(client, monkeypatch):
    cid, comments = analyzed_case(client, monkeypatch)
    ids = [comments[0]["id"], comments[4]["id"]]
    r = client.patch("/api/comments/bulk", json={"comment_ids": ids + ["cmt_nope"], "saved": True}).json()
    assert r["updated"] == 2 and r["missing"] == ["cmt_nope"]
    assert saved_ids(client, cid) == set(ids)
    r = client.patch("/api/comments/bulk", json={"comment_ids": ids, "saved": False, "case_id": cid}).json()
    assert r["updated"] == 2 and saved_ids(client, cid) == set()


def test_bulk_save_scoped_to_case_and_large_lists(client, monkeypatch):
    cid, comments = analyzed_case(client, monkeypatch, n=3)
    other = mk_case(client, "다른 사건")
    r = client.patch("/api/comments/bulk", json={"comment_ids": [c["id"] for c in comments], "case_id": other, "saved": True}).json()
    assert r["updated"] == 0 and len(r["missing"]) == 3 and saved_ids(client, cid) == set()
    many = [f"cmt_x{i}" for i in range(1200)] + [comments[0]["id"]]  # IN 절 분할 확인
    r = client.patch("/api/comments/bulk", json={"comment_ids": many, "saved": True}).json()
    assert r["updated"] == 1 and len(r["missing"]) == 1200


@pytest.mark.parametrize(
    "body",
    [
        {"saved": True},
        {"saved": True, "comment_ids": ["a"], "level": "legal_review", "case_id": "x"},
        {"saved": True, "level": "legal_review"},
        {"saved": True, "comment_ids": []},
        {"saved": True, "level": "guilty", "case_id": "x"},
        {"comment_ids": ["a"]},
        {"saved": True, "comment_ids": ["a"], "content": "변조"},
    ],
)
def test_bulk_save_validation(client, body):
    r = client.patch("/api/comments/bulk", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_bulk_save_unknown_case_404_and_single_patch_still_works(client, monkeypatch):
    assert client.patch("/api/comments/bulk", json={"case_id": "nope", "level": "low_risk", "saved": True}).status_code == 404
    cid, comments = analyzed_case(client, monkeypatch, n=2)
    r = client.patch(f"/api/comments/{comments[0]['id']}", json={"saved": True})
    assert r.status_code == 200 and r.json()["saved"] is True


# ---------------------------------------------------------------- B-4 mask author
def test_mask_author_rule():
    assert mask_author("@정수진") == "@정**"
    assert mask_author("정수진") == "정**"
    assert mask_author("A") == "A**"
    assert mask_author("😀user") == "😀**"
    assert mask_author("@") == "@"
    assert mask_author(None) is None and mask_author("  ") == "  "


def test_pdf_mask_author_only_when_requested_and_db_untouched(client, monkeypatch):
    captured = []

    def fake_pdf(case_data):
        captured.append([c["author"] for c in case_data["comments"]])
        return PDF

    monkeypatch.setattr(adapters, "generate_statement_pdf", fake_pdf)
    monkeypatch.setattr(adapters, "generate_evidence_list_pdf", fake_pdf)
    monkeypatch.setattr(
        adapters,
        "fetch_youtube_comments",
        lambda vid, limit=None: [
            {"content": "가상 댓글 1", "author": "@정수진", "posted_at": None, "comment_url": None, "parent_id": None, "like_count": None},
            {"content": "가상 댓글 2", "author": None, "posted_at": None, "comment_url": None, "parent_id": None, "like_count": None},
        ],
    )
    cid = mk_case(client)
    comments = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()["comments"]
    client.patch("/api/comments/bulk", json={"comment_ids": [c["id"] for c in comments], "saved": True})

    for kind in ("statement", "evidence-list"):
        captured.clear()
        assert client.get(f"/api/cases/{cid}/documents/{kind}.pdf").status_code == 200
        assert captured == [["@정수진", None]]  # 기본은 원본
        assert client.get(f"/api/cases/{cid}/documents/{kind}.pdf?mask_author=true").status_code == 200
        assert captured[-1] == ["@정**", None]
    assert [c["author"] for c in client.get(f"/api/cases/{cid}").json()["comments"]] == ["@정수진", None]
