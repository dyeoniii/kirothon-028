"""URL 판별 (S4 [AI]).

YouTube watch / shorts / youtu.be / live / embed URL에서 영상 ID를 추출한다.
그 외 http(s) URL은 스크래핑하지 않고 `url_only`로 표시한다(출처 보관 + 수동 입력).
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

__all__ = ["InvalidURLError", "detect_platform_and_id"]

MAX_URL_LENGTH = 2048
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_YOUTU_BE_HOSTS = {"youtu.be", "www.youtu.be"}
_PATH_ID_PREFIXES = ("shorts", "live", "embed", "v")


class InvalidURLError(ValueError):
    """허용되지 않거나 형식이 잘못된 URL. API에서 400 VALIDATION_ERROR로 매핑."""

    code = "INVALID_URL"
    http_status = 400


def _valid_id(candidate: str | None) -> str | None:
    if candidate and _VIDEO_ID_RE.match(candidate):
        return candidate
    return None


def _youtube_video_id(host: str, path: str, query: str) -> str | None:
    segments = [s for s in path.split("/") if s]
    if host in _YOUTU_BE_HOSTS:
        return _valid_id(segments[0]) if segments else None
    if segments and segments[0] == "watch":
        return _valid_id((parse_qs(query).get("v") or [None])[0])
    if len(segments) >= 2 and segments[0] in _PATH_ID_PREFIXES:
        return _valid_id(segments[1])
    return None


def detect_platform_and_id(url: str) -> dict:
    """URL을 판별한다.

    반환: ``{"platform": "youtube" | "url_only", "video_id": str | None,
    "normalized_url": str}``.
    YouTube 도메인이라도 영상 ID를 찾지 못하면(채널/검색 페이지 등) ``url_only``.
    http/https 이외 스킴, 호스트 없음, 계정정보 포함, 공백/제어문자, 2048자 초과는
    :class:`InvalidURLError`.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL은 문자열이어야 합니다.")
    raw = url.strip()
    if not raw:
        raise InvalidURLError("URL을 입력해 주세요.")
    if len(raw) > MAX_URL_LENGTH:
        raise InvalidURLError("URL이 너무 깁니다.")
    if any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in raw):
        raise InvalidURLError("URL에 공백이나 제어 문자가 포함되어 있습니다.")

    try:
        parts = urlsplit(raw)
        port = parts.port  # 잘못된 포트면 ValueError
    except ValueError as exc:
        raise InvalidURLError("URL 형식이 올바르지 않습니다.") from exc

    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidURLError("http 또는 https URL만 지원합니다.")
    if parts.username is not None or parts.password is not None:
        raise InvalidURLError("계정 정보가 포함된 URL은 지원하지 않습니다.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or ("." not in host and host != "localhost"):
        raise InvalidURLError("URL의 도메인을 확인할 수 없습니다.")

    if host in _YOUTUBE_HOSTS or host in _YOUTU_BE_HOSTS:
        video_id = _youtube_video_id(host, parts.path, parts.query)
        if video_id:
            return {
                "platform": "youtube",
                "video_id": video_id,
                "normalized_url": f"https://www.youtube.com/watch?v={video_id}",
            }

    netloc = host if port is None else f"{host}:{port}"
    normalized = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    return {"platform": "url_only", "video_id": None, "normalized_url": normalized}
