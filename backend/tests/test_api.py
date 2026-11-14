"""S3 [API] 최소 테스트. 모든 데이터는 가상. 다른 세션 함수는 fake로 대체."""
import hashlib
import os
from pathlib import Path

import pytest

from app.api import adapters

PNG = b"\x89PNG\r\n\x1a\n" + b"virtual-image-bytes" * 10
PDF = b"%PDF-1.4\n%fake\n"


def mk_case(client, title="가상 사건"):
    r = client.post("/api/cases", json={"title": title, "description": "시연용 가상 사건"})
    assert r.status_code == 201
    return r.json()["id"]


def add_text(client, case_id, text="그 사람은 사기꾼이다\n오늘 날씨 좋다", **extra):
    r = client.post(f"/api/cases/{case_id}/inputs/text", json={"text": text, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def fake_analyze(comments, context=None):
    return [
        {"comment_id": c["comment_id"], "level": "needs_context", "issues": ["명예훼손(사실 적시)"],
         "flagged_phrases": ["사기꾼"], "reason": "가상 판독", "check_points": ["대상 특정 여부"]}
        for c in comments
    ]


# ---------------------------------------------------------------- health / cases
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    status = client.get("/api/health/adapters").json()
    assert set(status) >= {"analyze_comments", "generate_statement_pdf"}


def test_case_crud_and_errors(client):
    cid = mk_case(client)
    assert client.get(f"/api/cases/{cid}").json()["sources"] == []
    listing = client.get("/api/cases").json()
    assert listing[0]["id"] == cid and listing[0]["saved_count"] == 0
    r = client.get("/api/cases/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    r = client.post("/api/cases", json={"title": "  "})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = client.post("/api/cases", json={})
    assert r.status_code == 400


# ---------------------------------------------------------------- text input / patch
def test_text_input_keeps_original_and_patch_cannot_edit_content(client):
    cid = mk_case(client)
    data = add_text(client, cid, source_url="https://example.com/post/1", context="가상 게시글")
    assert data["source"]["type"] == "text" and data["source"]["url"] == "https://example.com/post/1"
    assert [c["content"] for c in data["comments"]] == ["그 사람은 사기꾼이다", "오늘 날씨 좋다"]
    assert data["comments"][0]["author"] is None and data["comments"][0]["posted_at"] is None
    assert data["source"]["collected_at"].endswith("Z")

    comment_id = data["comments"][0]["id"]
    r = client.patch(f"/api/comments/{comment_id}", json={"content": "변조"})
    assert r.status_code == 400
    r = client.patch(f"/api/comments/{comment_id}", json={})
    assert r.status_code == 400
    r = client.patch(f"/api/comments/{comment_id}", json={"saved": True, "user_note": "메모", "user_confirmed": True})
    body = r.json()
    assert body["saved"] and body["user_note"] == "메모" and body["user_confirmed"]
    assert body["content"] == "그 사람은 사기꾼이다"
    assert client.get("/api/cases").json()[0]["saved_count"] == 1


def test_text_input_validation(client):
    cid = mk_case(client)
    assert client.post(f"/api/cases/{cid}/inputs/text", json={"text": " \n \n"}).status_code == 400
    r = client.post(f"/api/cases/{cid}/inputs/text", json={"text": "a", "source_url": "javascript:alert(1)"})
    assert r.status_code == 400
    assert client.post("/api/cases/nope/inputs/text", json={"text": "a"}).status_code == 404


# ---------------------------------------------------------------- URL parsing
def test_url_non_youtube_is_url_only(client):
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://www.instagram.com/p/abc/"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["type"] == "url_only" and body["source"]["needs_manual_input"] is True
    assert body["comments"] == []


@pytest.mark.parametrize("bad", ["ftp://x.com/a", "not a url", "javascript:alert(1)", "https://www.youtube.com/watch?v=bad"])
def test_url_invalid(client, bad):
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": bad})
    assert r.status_code == 400, bad
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "url",
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/shorts/dQw4w9WgXcQ"],
)
def test_url_youtube_variants_call_collector(client, monkeypatch, url):
    seen = {}

    def fake_fetch(video_id, limit=200):
        seen["args"] = (video_id, limit)
        return [{"content": "가상 댓글", "author": "예시계정", "posted_at": "2026-01-01T00:00:00Z",
                 "comment_url": None, "parent_id": None, "like_count": 3}]

    monkeypatch.setattr(adapters, "fetch_youtube_comments", fake_fetch)
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": url})
    assert r.status_code == 200
    assert seen["args"] == ("dQw4w9WgXcQ", 10000)  # 기본 YOUTUBE_MAX_COMMENTS
    body = r.json()
    assert body["source"]["type"] == "youtube" and body["comments"][0]["platform"] == "youtube"
    assert body["comments"][0]["like_count"] == 3


def test_youtube_failure_is_503_and_hides_key(client, monkeypatch):
    def boom(video_id, limit=200):
        raise RuntimeError("quotaExceeded https://x/y?key=SECRETKEY123&a=1")

    monkeypatch.setattr(adapters, "fetch_youtube_comments", boom)
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 503
    assert "SECRETKEY123" not in r.text and "직접 입력" in r.json()["error"]["message"]
    assert client.get(f"/api/cases/{cid}").json()["sources"] == []


def test_unconnected_modules_return_503_not_fake_data(client):
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "MODULE_NOT_CONNECTED"


# ---------------------------------------------------------------- image
def test_image_upload_sha256_original_saved_and_deleted(client, monkeypatch):
    monkeypatch.setattr(
        adapters, "extract_comments_from_image",
        lambda b, m: [{"content": "가상 댓글", "author": None, "posted_at": None}],
    )
    cid = mk_case(client)
    r = client.post(
        f"/api/cases/{cid}/inputs/image",
        files={"file": ("shot.png", PNG, "image/png")},
        data={"context": "가상 맥락"},
    )
    assert r.status_code == 200, r.text
    src = r.json()["source"]
    assert src["type"] == "image" and src["file_sha256"] == hashlib.sha256(PNG).hexdigest()
    assert src["collected_at"].endswith("Z")
    assert r.json()["comments"][0]["author"] is None

    stored = list((Path(os.environ["STORAGE_DIR"]) / cid).glob("*"))
    assert len(stored) == 1 and stored[0].read_bytes() == PNG  # 원본 무변경

    assert client.delete(f"/api/cases/{cid}").status_code == 204
    assert not (Path(os.environ["STORAGE_DIR"]) / cid).exists()
    assert client.get(f"/api/cases/{cid}").status_code == 404


def test_image_validation(client, monkeypatch):
    monkeypatch.setattr(adapters, "extract_comments_from_image", lambda b, m: [])
    cid = mk_case(client)
    url = f"/api/cases/{cid}/inputs/image"
    assert client.post(url, files={"file": ("a.gif", b"GIF89a", "image/gif")}).status_code == 400
    assert client.post(url, files={"file": ("a.png", b"not an image", "image/png")}).status_code == 400
    assert client.post(url, files={"file": ("a.png", b"", "image/png")}).status_code == 400
    big = PNG + b"0" * (10 * 1024 * 1024)
    r = client.post(url, files={"file": ("a.png", big, "image/png")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert client.post(url).status_code == 400
    # 실패한 업로드는 파일/소스를 남기지 않음
    assert client.get(f"/api/cases/{cid}").json()["sources"] == []
    # 추출 0건: 소스는 저장하되 수동 입력 안내
    ok = client.post(url, files={"file": ("a.webp", b"RIFF\x00\x00\x00\x00WEBPxx", "image/webp")})
    assert ok.status_code == 200 and ok.json()["source"]["needs_manual_input"] is True


# ---------------------------------------------------------------- analyze
def test_analyze_stores_and_validates(client, monkeypatch):
    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)
    cid = mk_case(client)
    comments = add_text(client, cid)["comments"]
    ids = [c["id"] for c in comments]
    r = client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": ids})
    assert r.status_code == 200
    res = r.json()["results"]
    assert res[0]["level_label"] == "추가 맥락 확인 필요"
    assert res[0]["disclaimer"] == "AI 분석은 법률 자문이 아닙니다."
    detail = client.get(f"/api/cases/{cid}").json()
    assert detail["comments"][0]["analysis"]["level"] == "needs_context"
    assert detail["comments"][0]["content"] == "그 사람은 사기꾼이다"


def test_analyze_passes_only_minimum_fields(client, monkeypatch):
    captured = {}

    def spy(comments, context=None):
        captured["comments"], captured["context"] = comments, context
        return fake_analyze(comments)

    monkeypatch.setattr(adapters, "analyze_comments", spy)
    cid = mk_case(client)
    data = add_text(client, cid, context="가상 게시글")
    client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [data["comments"][0]["id"]]})
    assert set(captured["comments"][0]) == {"comment_id", "content"}
    assert captured["context"] == "가상 게시글"


def test_analyze_retries_once_on_invalid_json(client, monkeypatch):
    calls = {"n": 0}

    def flaky(comments, context=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"comment_id": comments[0]["comment_id"], "level": "criminal"}]  # 잘못된 level
        return fake_analyze(comments)

    monkeypatch.setattr(adapters, "analyze_comments", flaky)
    cid = mk_case(client)
    cmt = add_text(client, cid)["comments"][0]["id"]
    assert client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [cmt]}).status_code == 200
    assert calls["n"] == 2


def test_analyze_fails_after_second_invalid(client, monkeypatch):
    calls = {"n": 0}

    def bad(comments, context=None):
        calls["n"] += 1
        return [{"nonsense": True}]

    monkeypatch.setattr(adapters, "analyze_comments", bad)
    cid = mk_case(client)
    cmt = add_text(client, cid)["comments"][0]["id"]
    r = client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [cmt]})
    assert r.status_code == 502 and r.json()["error"]["code"] == "ANALYSIS_INVALID"
    assert calls["n"] == 2


def test_analyze_request_validation(client, monkeypatch):
    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)
    cid = mk_case(client)
    other = mk_case(client, "다른 사건")
    other_cmt = add_text(client, other)["comments"][0]["id"]
    assert client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": []}).status_code == 400
    assert client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [f"c{i}" for i in range(21)]}).status_code == 400
    assert client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [other_cmt]}).status_code == 404


# ---------------------------------------------------------------- agent
def test_agent_review_and_answers(client):
    cid = mk_case(client)
    ids = [c["id"] for c in add_text(client, cid, source_url="https://example.com/p")["comments"]]
    client.patch(f"/api/comments/{ids[0]}", json={"saved": True})
    review = client.post(f"/api/cases/{cid}/agent/review").json()
    assert 0 <= review["completeness"] <= 100
    assert {q["id"] for q in review["questions"]} == {"q1", "q2", "q3"}
    assert any(c["item"] == "댓글 작성자" and c["status"] == "missing" for c in review["checklist"])

    r = client.post(f"/api/cases/{cid}/agent/answers", json={"answers": [{"question_id": "q1", "answer": "가상 피해"}]})
    assert r.status_code == 200
    assert "q1" not in {q["id"] for q in r.json()["questions"]}
    assert r.json()["completeness"] >= review["completeness"]
    # 덮어쓰기 + 상세 반영
    client.post(f"/api/cases/{cid}/agent/answers", json={"answers": [{"question_id": "q1", "answer": "수정"}]})
    answers = client.get(f"/api/cases/{cid}").json()["answers"]
    assert len(answers) == 1 and answers[0]["answer"] == "수정"
    assert client.post(f"/api/cases/{cid}/agent/answers", json={"answers": []}).status_code == 400


# ---------------------------------------------------------------- documents
def test_documents_use_only_saved_real_fields(client, monkeypatch):
    captured = {}

    def fake_statement(case_data):
        captured["statement"] = case_data
        return PDF

    monkeypatch.setattr(adapters, "generate_statement_pdf", fake_statement)
    monkeypatch.setattr(adapters, "generate_evidence_list_pdf", lambda d: PDF)
    cid = mk_case(client)
    assert client.get(f"/api/cases/{cid}/documents/statement.pdf").status_code == 400  # 증거 없음

    ids = [c["id"] for c in add_text(client, cid, source_url="https://example.com/p")["comments"]]
    client.patch(f"/api/comments/{ids[0]}", json={"saved": True, "user_note": "메모"})
    client.post(f"/api/cases/{cid}/agent/answers", json={"answers": [{"question_id": "q1", "answer": "가상 피해"}]})

    r = client.get(f"/api/cases/{cid}/documents/statement.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"] and r.content == PDF
    data = captured["statement"]
    assert [c["id"] for c in data["comments"]] == [ids[0]]  # 저장된 증거만
    assert data["comments"][0]["content"] == "그 사람은 사기꾼이다"
    assert data["comments"][0]["user_note"] == "메모"
    assert data["sources"][0]["url"] == "https://example.com/p"
    assert data["answers"][0]["answer"] == "가상 피해"
    assert client.get(f"/api/cases/{cid}/documents/evidence-list.pdf").status_code == 200


def test_documents_not_connected_and_invalid_pdf(client, monkeypatch):
    cid = mk_case(client)
    cmt = add_text(client, cid)["comments"][0]["id"]
    client.patch(f"/api/comments/{cmt}", json={"saved": True})
    r = client.get(f"/api/cases/{cid}/documents/statement.pdf")
    assert r.status_code == 503 and r.json()["error"]["code"] == "MODULE_NOT_CONNECTED"
    monkeypatch.setattr(adapters, "generate_statement_pdf", lambda d: b"nope")
    assert client.get(f"/api/cases/{cid}/documents/statement.pdf").status_code == 500


# ---------------------------------------------------------------- delete
def test_delete_removes_related_rows(client, monkeypatch):
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Analysis, Answer, Comment, Source

    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)
    cid = mk_case(client)
    cmt = add_text(client, cid)["comments"][0]["id"]
    client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [cmt]})
    client.post(f"/api/cases/{cid}/agent/answers", json={"answers": [{"question_id": "q1", "answer": "a"}]})
    assert client.delete(f"/api/cases/{cid}").status_code == 204
    with SessionLocal() as db:
        for model in (Source, Comment, Analysis, Answer):
            assert db.scalar(select(func.count()).select_from(model)) == 0
    assert client.delete(f"/api/cases/{cid}").status_code == 404
