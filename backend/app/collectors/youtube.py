"""YouTube Data API v3 공개 댓글 수집 (S4 [AI]).

- 공식 API(commentThreads.list, comments.list)만 사용한다. 스크래핑 없음.
- 최상위 댓글 + 가져올 수 있는 답글을 합산해 최대 ``limit``개(최신순). 기본 한도는 환경변수
  ``YOUTUBE_MAX_COMMENTS``(기본 10000, 0이면 무제한).
- API 키는 환경변수 ``YOUTUBE_API_KEY``에서 읽고 ``X-Goog-Api-Key`` 헤더로만 보낸다
  (URL/로그/예외 메시지에 키가 포함되지 않도록).
- 실패는 :class:`YouTubeError` 하위 예외로 올린다. ``code``/``http_status``/``message``를
  API 세션이 ``{"error": {...}}`` 응답으로 그대로 매핑할 수 있다.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any

import httpx

__all__ = [
    "YouTubeError",
    "YouTubeConfigError",
    "YouTubeQuotaError",
    "YouTubeCommentsDisabledError",
    "YouTubeNotFoundError",
    "YouTubeForbiddenError",
    "YouTubeUpstreamError",
    "fetch_youtube_comments",
    "fetch_youtube_comment_count",
    "get_max_comments",
    "DEFAULT_MAX_COMMENTS",
]

API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_MAX_COMMENTS = 10000
_PAGE_SIZE = 100
_TIMEOUT = httpx.Timeout(15.0)
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def get_max_comments() -> int:
    """환경변수 ``YOUTUBE_MAX_COMMENTS``. 기본 10000, 0이면 무제한(0 반환). 잘못된 값은 기본값."""
    raw = (os.environ.get("YOUTUBE_MAX_COMMENTS") or "").strip()
    if not raw:
        return DEFAULT_MAX_COMMENTS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_COMMENTS
    return value if value >= 0 else DEFAULT_MAX_COMMENTS


class YouTubeError(Exception):
    code = "YOUTUBE_API_ERROR"
    http_status = 502
    default_message = "YouTube 댓글을 가져오지 못했습니다."

    def __init__(self, message: str | None = None):
        # 수동 입력 안내 문구는 API 세션(inputs.py)이 덧붙인다.
        self.message = message or self.default_message
        super().__init__(self.message)


class YouTubeConfigError(YouTubeError):
    code = "YOUTUBE_API_KEY_INVALID"
    http_status = 503
    default_message = "서버의 YouTube API 키가 없거나 유효하지 않습니다."


class YouTubeQuotaError(YouTubeError):
    code = "YOUTUBE_QUOTA_EXCEEDED"
    http_status = 503
    default_message = "YouTube API 사용 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."


class YouTubeCommentsDisabledError(YouTubeError):
    code = "YOUTUBE_COMMENTS_DISABLED"
    http_status = 422
    default_message = "이 영상은 댓글이 비활성화되어 있습니다."


class YouTubeNotFoundError(YouTubeError):
    code = "YOUTUBE_VIDEO_NOT_FOUND"
    http_status = 404
    default_message = "영상을 찾을 수 없거나 비공개 상태입니다."


class YouTubeForbiddenError(YouTubeError):
    code = "YOUTUBE_FORBIDDEN"
    http_status = 403
    default_message = "이 영상의 댓글에 접근할 권한이 없습니다(비공개·연령 제한 등)."


class YouTubeUpstreamError(YouTubeError):
    code = "YOUTUBE_UNAVAILABLE"
    http_status = 503
    default_message = "YouTube API에 연결하지 못했습니다."


_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded"}
_KEY_REASONS = {"keyInvalid", "keyExpired", "accessNotConfigured", "ipRefererBlocked", "forbiddenByApiKey"}


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    reasons: set[str] = set()
    message = ""
    try:
        err = resp.json().get("error", {})
        message = str(err.get("message", ""))
        reasons = {e.get("reason", "") for e in err.get("errors", []) if isinstance(e, dict)}
        for d in err.get("details", []) or []:
            if isinstance(d, dict) and d.get("reason"):
                reasons.add(d["reason"])
    except (ValueError, AttributeError):
        pass
    status = resp.status_code
    if reasons & _QUOTA_REASONS or status == 429:
        raise YouTubeQuotaError()
    if "commentsDisabled" in reasons:
        raise YouTubeCommentsDisabledError()
    if reasons & {"videoNotFound", "commentThreadNotFound", "parentCommentNotFound"} or status == 404:
        raise YouTubeNotFoundError()
    if reasons & _KEY_REASONS or "API_KEY" in message or "API key" in message:
        raise YouTubeConfigError()
    if status == 403:
        raise YouTubeForbiddenError()
    if status >= 500:
        raise YouTubeUpstreamError()
    raise YouTubeError()


def _get(client: httpx.Client, path: str, params: dict[str, Any], api_key: str) -> dict:
    try:
        resp = client.get(f"{API_BASE}/{path}", params=params, headers={"X-Goog-Api-Key": api_key})
    except httpx.HTTPError as exc:  # 네트워크/타임아웃. 원본 메시지는 노출하지 않음
        raise YouTubeUpstreamError() from exc
    _raise_for_response(resp)
    try:
        return resp.json()
    except ValueError as exc:
        raise YouTubeUpstreamError("YouTube API 응답을 해석하지 못했습니다.") from exc


def _to_comment(item: dict, video_id: str, parent_external_id: str | None) -> dict | None:
    snippet = item.get("snippet") or {}
    content = snippet.get("textOriginal")
    if content is None:
        content = snippet.get("textDisplay")
    if not content:
        return None
    external_id = item.get("id")
    like = snippet.get("likeCount")
    return {
        "content": content,  # 원문 그대로, 가공하지 않음
        "author": snippet.get("authorDisplayName") or None,
        "posted_at": snippet.get("publishedAt") or None,
        "comment_url": (
            f"https://www.youtube.com/watch?v={video_id}&lc={external_id}" if external_id else None
        ),
        "platform": "youtube",
        "like_count": like if isinstance(like, int) else None,
        "external_id": external_id,
        "parent_id": parent_external_id,  # YouTube 상위 댓글 ID(최상위면 None)
    }


def fetch_youtube_comments(
    video_id: str,
    limit: int | None = None,
    *,
    client: httpx.Client | None = None,
) -> list[dict]:
    """공개 댓글을 최상위→해당 답글 순서로 최대 ``limit``개 반환한다.

    ``limit``이 None이면 ``YOUTUBE_MAX_COMMENTS``, 0이면 무제한이다.
    commentThreads 기본 정렬이 최신순이라 한도가 있으면 최근 댓글부터 채워진다.

    각 항목: ``content, author, posted_at, comment_url, parent_id, like_count``
    (+ ``platform="youtube"``, ``external_id``).
    ``parent_id``/``external_id``는 YouTube 댓글 ID다. API 세션이 DB의 ``cmt_*`` ID로
    변환해야 한다. ``client``는 테스트용 주입 인자다.
    """
    if not isinstance(video_id, str) or not _VIDEO_ID_RE.match(video_id):
        raise ValueError("유효한 YouTube 영상 ID가 아닙니다.")
    if limit is None:
        limit = get_max_comments()
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit은 0(무제한) 이상의 정수여야 합니다.")
    if limit == 0:
        limit = sys.maxsize

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise YouTubeConfigError("서버에 YouTube API 키가 설정되지 않았습니다.")

    own_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    results: list[dict] = []
    try:
        page_token: str | None = None
        while len(results) < limit:
            params: dict[str, Any] = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": _PAGE_SIZE,
                "textFormat": "plainText",
            }
            if page_token:
                params["pageToken"] = page_token
            data = _get(http, "commentThreads", params, api_key)

            for thread in data.get("items", []) or []:
                if len(results) >= limit:
                    break
                top = (thread.get("snippet") or {}).get("topLevelComment") or {}
                top_comment = _to_comment(top, video_id, None)
                if top_comment is None:
                    continue
                results.append(top_comment)
                top_id = top.get("id")
                total_replies = (thread.get("snippet") or {}).get("totalReplyCount") or 0
                included = ((thread.get("replies") or {}).get("comments")) or []
                if not top_id or total_replies <= 0 or len(results) >= limit:
                    continue
                if len(included) >= total_replies:
                    for reply in included:
                        if len(results) >= limit:
                            break
                        c = _to_comment(reply, video_id, top_id)
                        if c:
                            results.append(c)
                else:
                    _fetch_replies(http, api_key, video_id, top_id, results, limit)

            page_token = data.get("nextPageToken")
            if not page_token:
                break
    finally:
        if own_client:
            http.close()
    return results


def _fetch_replies(
    http: httpx.Client, api_key: str, video_id: str, parent_id: str, results: list[dict], limit: int
) -> None:
    page_token: str | None = None
    while len(results) < limit:
        params: dict[str, Any] = {
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": _PAGE_SIZE,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        data = _get(http, "comments", params, api_key)
        for item in data.get("items", []) or []:
            if len(results) >= limit:
                return
            c = _to_comment(item, video_id, parent_id)
            if c:
                results.append(c)
        page_token = data.get("nextPageToken")
        if not page_token:
            return


def fetch_youtube_comment_count(video_id: str, *, client: httpx.Client | None = None) -> int | None:
    """videos.list(part=statistics)로 영상의 전체 댓글 수(commentCount, 답글 포함)를 조회한다.

    통계에 값이 없으면(댓글 비활성화 등) None. 실패는 YouTubeError로 올린다.
    """
    if not isinstance(video_id, str) or not _VIDEO_ID_RE.match(video_id):
        raise ValueError("유효한 YouTube 영상 ID가 아닙니다.")
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise YouTubeConfigError("서버에 YouTube API 키가 설정되지 않았습니다.")
    own_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    try:
        data = _get(http, "videos", {"part": "statistics", "id": video_id}, api_key)
    finally:
        if own_client:
            http.close()
    items = data.get("items") or []
    if not items:
        raise YouTubeNotFoundError()
    raw = (items[0].get("statistics") or {}).get("commentCount")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
