"""YouTube 수집기 테스트: 실제 네트워크 없이 httpx.MockTransport + 가상 데이터."""
import httpx
import pytest

from app.collectors import youtube as yt

VID = "AAAAAAAAAAA"
FAKE_KEY = "test-key-not-real"


def _c(cid, text, author="가상계정", likes=0):
    return {
        "id": cid,
        "snippet": {
            "textOriginal": text,
            "textDisplay": text,
            "authorDisplayName": author,
            "publishedAt": "2026-11-14T03:00:00Z",
            "likeCount": likes,
        },
    }


def _thread(tid, text, replies=(), total=None):
    t = {"id": tid, "snippet": {"topLevelComment": _c(tid, text), "totalReplyCount": len(replies) if total is None else total}}
    if replies:
        t["replies"] = {"comments": list(replies)}
    return t


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_KEY)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_paginates_and_includes_replies():
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        assert req.headers["X-Goog-Api-Key"] == FAKE_KEY
        assert "key" not in req.url.params  # 키는 URL에 넣지 않음
        p = req.url.params
        if req.url.path.endswith("/commentThreads"):
            if p.get("pageToken") == "P2":
                return httpx.Response(200, json={"items": [_thread("T3", "세 번째 가상 댓글")]})
            return httpx.Response(
                200,
                json={
                    "items": [
                        _thread("T1", "첫 가상 댓글", replies=[_c("T1.r1", "가상 답글")]),
                        _thread("T2", "둘째 가상 댓글", replies=[_c("T2.r1", "일부 답글")], total=3),
                    ],
                    "nextPageToken": "P2",
                },
            )
        assert req.url.path.endswith("/comments")
        assert p["parentId"] == "T2"
        return httpx.Response(
            200, json={"items": [_c("T2.r1", "답글1"), _c("T2.r2", "답글2"), _c("T2.r3", "답글3")]}
        )

    out = yt.fetch_youtube_comments(VID, client=_client(handler))
    assert [c["content"] for c in out] == [
        "첫 가상 댓글", "가상 답글", "둘째 가상 댓글", "답글1", "답글2", "답글3", "세 번째 가상 댓글",
    ]
    assert out[0]["parent_id"] is None and out[1]["parent_id"] == "T1"
    assert out[3]["parent_id"] == "T2"
    assert out[0]["comment_url"] == f"https://www.youtube.com/watch?v={VID}&lc=T1"
    assert set(out[0]) >= {"content", "author", "posted_at", "comment_url", "parent_id", "like_count"}
    assert out[0]["posted_at"] == "2026-11-14T03:00:00Z"


def test_limit_counts_replies():
    def handler(req):
        if req.url.path.endswith("/commentThreads"):
            items = [_thread(f"T{i}", f"가상 {i}", replies=[_c(f"T{i}.r", "답")]) for i in range(100)]
            return httpx.Response(200, json={"items": items, "nextPageToken": "more"})
        raise AssertionError("unexpected")

    out = yt.fetch_youtube_comments(VID, limit=5, client=_client(handler))
    assert len(out) == 5
    big = yt.fetch_youtube_comments(VID, limit=1000, client=_client(handler))
    assert len(big) == 1000  # 예전 200 상한 없음


@pytest.mark.parametrize(
    "status,reason,exc",
    [
        (403, "quotaExceeded", yt.YouTubeQuotaError),
        (429, "rateLimitExceeded", yt.YouTubeQuotaError),
        (403, "commentsDisabled", yt.YouTubeCommentsDisabledError),
        (404, "videoNotFound", yt.YouTubeNotFoundError),
        (400, "keyInvalid", yt.YouTubeConfigError),
        (403, "forbidden", yt.YouTubeForbiddenError),
        (500, "backendError", yt.YouTubeUpstreamError),
    ],
)
def test_error_mapping(status, reason, exc):
    def handler(req):
        return httpx.Response(status, json={"error": {"code": status, "message": "x", "errors": [{"reason": reason}]}})

    with pytest.raises(exc) as ei:
        yt.fetch_youtube_comments(VID, client=_client(handler))
    assert FAKE_KEY not in ei.value.message
    assert ei.value.code.startswith("YOUTUBE_")


def test_network_error_hides_details():
    def handler(req):
        raise httpx.ConnectError("boom " + str(req.url))

    with pytest.raises(yt.YouTubeUpstreamError) as ei:
        yt.fetch_youtube_comments(VID, client=_client(handler))
    assert FAKE_KEY not in str(ei.value)


def test_missing_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(yt.YouTubeConfigError):
        yt.fetch_youtube_comments(VID)


@pytest.mark.parametrize("bad", ["", "short", "../../etc", None])
def test_bad_video_id(bad):
    with pytest.raises(ValueError):
        yt.fetch_youtube_comments(bad)


def test_default_limit_from_env(monkeypatch):
    def handler(req):
        items = [_thread(f"T{i}", f"가상 {i}") for i in range(100)]
        return httpx.Response(200, json={"items": items, "nextPageToken": "more"})

    monkeypatch.delenv("YOUTUBE_MAX_COMMENTS", raising=False)
    assert yt.get_max_comments() == 10000
    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "250")
    assert yt.get_max_comments() == 250
    assert len(yt.fetch_youtube_comments(VID, client=_client(handler))) == 250
    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "abc")
    assert yt.get_max_comments() == 10000


def test_zero_means_unlimited(monkeypatch):
    pages = {"n": 0}

    def handler(req):
        pages["n"] += 1
        items = [_thread(f"P{pages['n']}T{i}", f"가상 {i}") for i in range(100)]
        body = {"items": items}
        if pages["n"] < 30:  # 100개씩 30페이지 = 3,000개
            body["nextPageToken"] = "more"
        return httpx.Response(200, json=body)

    monkeypatch.setenv("YOUTUBE_MAX_COMMENTS", "0")
    assert yt.get_max_comments() == 0
    assert len(yt.fetch_youtube_comments(VID, client=_client(handler))) == 3000
    pages["n"] = 0
    assert len(yt.fetch_youtube_comments(VID, limit=0, client=_client(handler))) == 3000


def test_comment_count_uses_videos_statistics():
    seen = {}

    def handler(req):
        seen["path"], seen["params"] = req.url.path, dict(req.url.params)
        assert req.headers["X-Goog-Api-Key"] == FAKE_KEY
        return httpx.Response(200, json={"items": [{"id": VID, "statistics": {"commentCount": "4000"}}]})

    assert yt.fetch_youtube_comment_count(VID, client=_client(handler)) == 4000
    assert seen["path"].endswith("/videos")
    assert seen["params"] == {"part": "statistics", "id": VID}


def test_comment_count_missing_or_video_not_found():
    no_count = lambda req: httpx.Response(200, json={"items": [{"id": VID, "statistics": {}}]})
    assert yt.fetch_youtube_comment_count(VID, client=_client(no_count)) is None
    empty = lambda req: httpx.Response(200, json={"items": []})
    with pytest.raises(yt.YouTubeNotFoundError):
        yt.fetch_youtube_comment_count(VID, client=_client(empty))
