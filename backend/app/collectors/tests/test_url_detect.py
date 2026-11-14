import pytest

from app.collectors.url_detect import InvalidURLError, detect_platform_and_id

VID = "dQw4w9WgXcQ"  # 형식 검증용 11자 ID


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?feature=share&v={VID}&t=10",
        f"http://m.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://youtube.com/shorts/{VID}?feature=share",
        f"https://www.youtube.com/live/{VID}",
        f"  https://WWW.YOUTUBE.COM/watch?v={VID}  ",
    ],
)
def test_youtube_urls(url):
    r = detect_platform_and_id(url)
    assert r == {
        "platform": "youtube",
        "video_id": VID,
        "normalized_url": f"https://www.youtube.com/watch?v={VID}",
    }


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@somechannel",
        "https://www.youtube.com/watch?v=short",
        "https://www.instagram.com/p/EXAMPLE/",
        "https://x.com/example/status/1",
    ],
)
def test_url_only(url):
    r = detect_platform_and_id(url)
    assert r["platform"] == "url_only"
    assert r["video_id"] is None
    assert r["normalized_url"].startswith("https://")


def test_url_only_drops_fragment_keeps_query():
    r = detect_platform_and_id("https://Example.com/post?id=1#frag")
    assert r["normalized_url"] == "https://example.com/post?id=1"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "javascript:alert(1)",
        "ftp://example.com/a",
        "file:///etc/passwd",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "https://",
        "https://user:pw@example.com/",
        "https://exa mple.com/",
        "https://example.com:99999/",
        "https://" + "a" * 2050 + ".com",
        None,
    ],
)
def test_invalid(url):
    with pytest.raises(InvalidURLError):
        detect_platform_and_id(url)


def test_invalid_is_value_error():
    assert issubclass(InvalidURLError, ValueError)
