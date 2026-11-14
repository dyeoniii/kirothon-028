"""전체 자동 판독(analyze-all)과 YouTube 전체 댓글 수 안내 테스트. 모든 데이터는 가상."""
import threading
import time

from app.api import adapters, analyze_all
from tests.test_api import add_text, mk_case


class RateLimited(Exception):
    http_status = 429
    code = "LLM_RATE_LIMITED"


def level_for(content: str) -> str:
    if "죽여" in content:
        return "legal_review"
    if "사기꾼" in content:
        return "needs_context"
    return "low_risk"


def fake_analyze(comments, context=None):
    return [
        {"comment_id": c["comment_id"], "level": level_for(c["content"]), "issues": [],
         "flagged_phrases": [], "reason": "가상 판독", "check_points": []}
        for c in comments
    ]


def make_lines(n: int) -> str:
    kinds = ["죽여버린다 가상{}", "그 사람은 사기꾼 가상{}", "오늘 날씨 좋다 가상{}"]
    return "\n".join(kinds[i % 3].format(i) for i in range(n))


def wait_done(client, case_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = client.get(f"/api/cases/{case_id}/analyze-all/status").json()
        if not s["running"]:
            return s
        time.sleep(0.02)
    raise AssertionError("analyze-all did not finish")


def test_batches_of_15_with_at_most_2_concurrent_and_results_saved(client, monkeypatch):
    lock = threading.Lock()
    state = {"active": 0, "peak": 0, "sizes": []}

    def analyzer(comments, context=None):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
            state["sizes"].append(len(comments))
        time.sleep(0.05)
        with lock:
            state["active"] -= 1
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    originals = add_text(client, cid, make_lines(260))["comments"]

    r = client.post(f"/api/cases/{cid}/analyze-all")
    assert r.status_code == 202
    assert r.json()["total"] == 260
    s = wait_done(client, cid)

    assert sorted(state["sizes"], reverse=True) == [15] * 17 + [5]
    assert state["peak"] == 2
    assert s["total"] == 260 and s["analyzed"] == 260 and s["pending"] == 0 and s["failed"] == 0
    # 가상 줄 i % 3: 0=legal_review, 1=needs_context, 2=low_risk (260개: 87/87/86)
    assert s["counts"] == {"legal_review": 87, "needs_context": 87, "low_risk": 86}

    detail = client.get(f"/api/cases/{cid}").json()
    assert all(c["analysis"] is not None for c in detail["comments"])
    assert [c["content"] for c in detail["comments"]] == [c["content"] for c in originals]  # 원문 불변
    assert detail["comments"][0]["analysis"]["disclaimer"] == "AI 분석은 법률 자문이 아닙니다."


def test_only_unanalyzed_comments_are_sent(client, monkeypatch):
    seen = []

    def analyzer(comments, context=None):
        seen.extend(c["comment_id"] for c in comments)
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    comments = add_text(client, cid, make_lines(6))["comments"]
    manual = [comments[0]["id"], comments[1]["id"]]
    r = client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": manual})  # 기존 선택 판독은 그대로 동작
    assert r.status_code == 200
    seen.clear()

    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert sorted(seen) == sorted(c["id"] for c in comments[2:])
    assert s["analyzed"] == 6

    seen.clear()
    r = client.post(f"/api/cases/{cid}/analyze-all")  # 남은 것이 없으면 호출 없음
    assert r.status_code == 202 and r.json()["running"] is False
    assert seen == []


def test_rate_limit_429_waits_then_retries(client, monkeypatch):
    waits = []
    monkeypatch.setattr(analyze_all, "_sleep", lambda s, ev=None: waits.append(s))
    calls = {"n": 0}

    def analyzer(comments, context=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RateLimited()
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(10))
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["analyzed"] == 10 and s["failed"] == 0 and s["error"] is None
    assert waits == [5, 10]  # 점점 길게 대기


def test_rate_limit_gives_up_and_rerun_picks_up_rest(client, monkeypatch):
    monkeypatch.setattr(analyze_all, "_sleep", lambda s, ev=None: None)
    monkeypatch.setattr(analyze_all, "RATE_LIMIT_WAITS", (1, 1))
    broken = {"on": True}

    def analyzer(comments, context=None):
        if broken["on"]:
            raise RateLimited()
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(8))
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["analyzed"] == 0 and s["failed"] == 8 and s["pending"] == 8
    assert "다시 실행" in s["message"]

    broken["on"] = False
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["analyzed"] == 8 and s["failed"] == 0 and s["message"] is None


def test_module_not_connected_reports_error_without_fake_results(client):
    cid = mk_case(client)  # conftest가 AI 판독을 stub(미연결)으로 고정
    add_text(client, cid, make_lines(5))
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["analyzed"] == 0 and s["failed"] == 5
    assert "연결되지" in s["error"]


def test_invalid_model_output_retried_once_then_counted_failed(client, monkeypatch):
    calls = {"n": 0}

    def analyzer(comments, context=None):
        calls["n"] += 1
        return [{"comment_id": comments[0]["comment_id"], "level": "guilty"}]

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(3))
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert calls["n"] == 2 and s["failed"] == 3 and s["analyzed"] == 0


def reference_analyzer(level, statement_type, laws):
    def analyzer(comments, context=None):
        return [
            {"comment_id": c["comment_id"], "level": level, "issues": [], "flagged_phrases": [], "reason": "가상 판독",
             "check_points": [], "statement_type": statement_type, "related_laws": laws}
            for c in comments
        ]
    return analyzer


def test_force_reanalyzes_already_analyzed_comments(client, monkeypatch):
    cid = mk_case(client)
    add_text(client, cid, make_lines(7))
    monkeypatch.setattr(adapters, "analyze_comments", reference_analyzer("low_risk", None, None))
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid)
    assert s["counts"] == {"legal_review": 0, "needs_context": 0, "low_risk": 7} and s["run_total"] == 7

    new = reference_analyzer("legal_review", "사실 적시", ["형법 제307조(명예훼손)"])
    monkeypatch.setattr(adapters, "analyze_comments", new)
    r = client.post(f"/api/cases/{cid}/analyze-all")  # force 없이는 이미 판독된 댓글을 건드리지 않음
    assert r.status_code == 202 and r.json()["running"] is False
    assert client.get(f"/api/cases/{cid}/analyze-all/status").json()["counts"]["legal_review"] == 0

    r = client.post(f"/api/cases/{cid}/analyze-all?force=true")
    assert r.status_code == 202 and r.json()["running"] is True and r.json()["run_total"] == 7
    s = wait_done(client, cid)
    assert s["counts"] == {"legal_review": 7, "needs_context": 0, "low_risk": 0}
    assert s["run_total"] == 7 and s["run_done"] == 7 and s["failed"] == 0
    a = client.get(f"/api/cases/{cid}").json()["comments"][0]["analysis"]
    assert a["level"] == "legal_review" and a["statement_type"] == "사실 적시"
    assert a["related_laws"] == ["형법 제307조(명예훼손)"]


def test_force_failure_keeps_previous_results(client, monkeypatch):
    cid = mk_case(client)
    add_text(client, cid, make_lines(4))
    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)
    client.post(f"/api/cases/{cid}/analyze-all")
    wait_done(client, cid)

    def boom(comments, context=None):
        raise RuntimeError("down")

    monkeypatch.setattr(adapters, "analyze_comments", boom)
    client.post(f"/api/cases/{cid}/analyze-all?force=true")
    s = wait_done(client, cid)
    assert s["analyzed"] == 4 and s["failed"] == 4 and "이전 판독 결과" in s["message"]


def test_analyze_returns_optional_reference_fields_and_drops_invalid(client, monkeypatch):
    def analyzer(comments, context=None):
        return [{"comment_id": c["comment_id"], "level": "needs_context", "reason": "가상",
                 "statement_type": "유죄", "related_laws": ["a", "b", "c"]} for c in comments]

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    cmt = add_text(client, cid, "그 사람 사기꾼")["comments"][0]["id"]
    r = client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [cmt]}).json()["results"][0]
    assert r["statement_type"] is None and r["related_laws"] == ["a", "b"]  # 허용 값 아니면 null, 최대 2개

    monkeypatch.setattr(adapters, "analyze_comments", fake_analyze)  # 필드 없는 이전 형식도 그대로 동작
    r = client.post(f"/api/cases/{cid}/analyze", json={"comment_ids": [cmt]}).json()["results"][0]
    assert r["statement_type"] is None and r["related_laws"] is None and r["level"] == "needs_context"


def test_existing_db_gets_new_analysis_columns():
    from sqlalchemy import create_engine, inspect, text

    from app.db import _add_missing_columns

    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE analyses (comment_id VARCHAR(32) PRIMARY KEY, level VARCHAR(16))"))
        conn.execute(text("INSERT INTO analyses VALUES ('cmt_old', 'low_risk')"))
    _add_missing_columns(eng)
    _add_missing_columns(eng)  # 두 번 실행해도 안전
    assert {"statement_type", "related_laws"} <= {c["name"] for c in inspect(eng).get_columns("analyses")}
    with eng.connect() as conn:
        assert conn.execute(text("SELECT level, statement_type FROM analyses")).one() == ("low_risk", None)


def test_second_start_while_running_does_not_duplicate(client, monkeypatch):
    gate = threading.Event()
    calls = {"n": 0}

    def analyzer(comments, context=None):
        calls["n"] += 1
        gate.wait(5)
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(10))
    assert client.post(f"/api/cases/{cid}/analyze-all").json()["running"] is True
    assert client.post(f"/api/cases/{cid}/analyze-all").json()["running"] is True
    gate.set()
    wait_done(client, cid)
    assert calls["n"] == 1


def test_case_deleted_during_run_stops_cleanly(client, monkeypatch):
    gate = threading.Event()

    def analyzer(comments, context=None):
        gate.wait(5)
        return fake_analyze(comments, context)

    monkeypatch.setattr(adapters, "analyze_comments", analyzer)
    cid = mk_case(client)
    add_text(client, cid, make_lines(120))
    client.post(f"/api/cases/{cid}/analyze-all")
    assert client.delete(f"/api/cases/{cid}").status_code == 204
    gate.set()
    deadline = time.time() + 10
    while time.time() < deadline and analyze_all._jobs[cid].running:
        time.sleep(0.02)
    assert analyze_all._jobs[cid].running is False
    assert client.get(f"/api/cases/{cid}/analyze-all/status").status_code == 404


def test_unknown_case_is_404(client):
    assert client.post("/api/cases/nope/analyze-all").status_code == 404
    assert client.get("/api/cases/nope/analyze-all/status").status_code == 404


def test_mock_provider_1000_comments_end_to_end(client, monkeypatch):
    """실제 classify(LLM_PROVIDER=mock)로 가상 댓글 1000개를 판독하고 걸린 시간을 확인한다."""
    from app.analysis import classify

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(adapters, "analyze_comments", classify.analyze_comments)
    cid = mk_case(client)
    lines = "\n".join(
        ["죽여버린다 가상{}", "그 사람 사기꾼이다 가상{}", "그 사람 쓰레기 같다 가상{}", "오늘 날씨 좋다 가상{}"][i % 4].format(i)
        for i in range(1000)
    )
    add_text(client, cid, lines)

    t0 = time.perf_counter()
    client.post(f"/api/cases/{cid}/analyze-all")
    s = wait_done(client, cid, timeout=60)
    elapsed = time.perf_counter() - t0
    print(f"\n[perf] mock 1000 comments analyzed in {elapsed:.2f}s")

    assert s["total"] == 1000 and s["analyzed"] == 1000 and s["failed"] == 0
    assert s["counts"] == {"legal_review": 250, "needs_context": 250, "low_risk": 500}
    assert elapsed < 30


# ---------------------------------------------------------------- YouTube 전체 댓글 수 / 한도 안내
def _fake_comments(n):
    return [{"content": f"가상 댓글 {i}", "author": None, "posted_at": None, "comment_url": None,
             "parent_id": None, "like_count": None} for i in range(n)]


def test_youtube_input_reports_total_available_and_limit_notice(client, monkeypatch):
    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "5")
    seen = {}

    def fake_fetch(video_id, limit=None):
        seen["limit"] = limit
        return _fake_comments(5)

    monkeypatch.setattr(adapters, "fetch_youtube_comments", fake_fetch)
    monkeypatch.setattr(adapters, "fetch_youtube_comment_count", lambda vid: 4000)
    cid = mk_case(client)
    r = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    body = r.json()
    assert r.status_code == 200 and seen["limit"] == 5
    assert body["total_available"] == 4000 and len(body["comments"]) == 5
    assert body["notice"] == "댓글이 4,000개라 최근 5개만 분석합니다"
    assert body["source"]["message"] == body["notice"]  # 사건 상세에서도 보이도록 저장


def test_youtube_input_no_notice_when_under_limit_or_unlimited(client, monkeypatch):
    seen = {}

    def fake_fetch(video_id, limit=None):
        seen["limit"] = limit
        return _fake_comments(3)

    monkeypatch.setattr(adapters, "fetch_youtube_comments", fake_fetch)
    monkeypatch.setattr(adapters, "fetch_youtube_comment_count", lambda vid: 3)
    cid = mk_case(client)
    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "10")
    body = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert body["total_available"] == 3 and body["notice"] is None

    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "0")  # 무제한
    monkeypatch.setattr(adapters, "fetch_youtube_comment_count", lambda vid: 99999)
    body = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert seen["limit"] == 0 and body["total_available"] == 99999 and body["notice"] is None


def test_youtube_count_failure_does_not_block_collection(client, monkeypatch):
    def boom(vid):
        raise RuntimeError("quota")

    monkeypatch.setattr(adapters, "fetch_youtube_comment_count", boom)
    monkeypatch.setattr(adapters, "fetch_youtube_comments", lambda vid, limit=None: _fake_comments(2))
    cid = mk_case(client)
    body = client.post(f"/api/cases/{cid}/inputs/url", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert len(body["comments"]) == 2 and body["total_available"] is None and body["notice"] is None
