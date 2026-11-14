"""LLM 단일 호출 지점 (S4 [AI]).

- ``LLM_PROVIDER=gemini|mock`` (기본 gemini). mock이면 키 없이 호출자가 준 고정 결과를 반환.
- Gemini는 ``google-genai`` SDK, 모델은 ``LLM_MODEL``(미지정 시 ``DEFAULT_MODEL``).
- 응답은 JSON 모드로 받고 Pydantic으로 검증한다. JSON/검증 실패·일시적 서버 오류는
  **한 번만** 재시도한다. 429/quota는 재시도하지 않는다.
- 모든 실패는 :class:`LLMError` 하위 예외(``code``, ``http_status``, ``message``)로 올린다.
  메시지에는 API 키나 모델 원문 응답을 담지 않는다.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

__all__ = [
    "DEFAULT_MODEL",
    "LLMError",
    "LLMConfigError",
    "LLMRateLimitError",
    "LLMUpstreamError",
    "LLMResponseError",
    "get_provider",
    "get_model_name",
    "generate_json",
]

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
_TIMEOUT_MS = 60_000
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    code = "LLM_ERROR"
    http_status = 502
    default_message = "AI 분석 중 오류가 발생했습니다."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class LLMConfigError(LLMError):
    code = "LLM_CONFIG_ERROR"
    http_status = 503
    default_message = "AI 분석 설정(API 키·모델)이 올바르지 않습니다. 관리자에게 확인해 주세요."


class LLMRateLimitError(LLMError):
    code = "LLM_RATE_LIMITED"
    http_status = 429
    default_message = "AI 사용 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."


class LLMUpstreamError(LLMError):
    code = "LLM_UNAVAILABLE"
    http_status = 503
    default_message = "AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."


class LLMResponseError(LLMError):
    code = "LLM_INVALID_RESPONSE"
    http_status = 502
    default_message = "AI 응답 형식이 올바르지 않아 결과를 만들지 못했습니다. 다시 시도해 주세요."


def get_provider() -> str:
    provider = (os.environ.get("LLM_PROVIDER") or "gemini").strip().lower()
    if provider not in ("gemini", "mock"):
        raise LLMConfigError("LLM_PROVIDER는 gemini 또는 mock이어야 합니다.")
    return provider


def get_model_name() -> str:
    return (os.environ.get("LLM_MODEL") or "").strip() or DEFAULT_MODEL


def _call_gemini(
    prompt: str,
    system_instruction: str,
    image_bytes: bytes | None,
    mime_type: str | None,
) -> str:
    """Gemini 원시 호출. JSON 문자열을 반환. 테스트에서 monkeypatch 대상."""
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise LLMConfigError("서버에 GEMINI_API_KEY가 설정되지 않았습니다.")
    try:
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - 설치 문제
        raise LLMConfigError("google-genai 패키지가 설치되어 있지 않습니다.") from exc

    contents: list[Any] = []
    if image_bytes is not None:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/png"))
    contents.append(prompt)

    try:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=_TIMEOUT_MS))
        response = client.models.generate_content(
            model=get_model_name(),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except genai_errors.APIError as exc:
        status = getattr(exc, "code", None)
        log.warning("Gemini API error status=%s", status)
        if status == 429:
            raise LLMRateLimitError() from exc
        if status in (400, 401, 403):
            msg = str(getattr(exc, "message", "") or "")
            if "API key" in msg or "API_KEY" in msg or status in (401, 403):
                raise LLMConfigError("Gemini API 키가 유효하지 않거나 권한이 없습니다.") from exc
            raise LLMResponseError("AI 요청이 거부되었습니다(입력 형식 또는 안전 정책).") from exc
        if status == 404:
            raise LLMConfigError("설정된 Gemini 모델을 찾을 수 없습니다(LLM_MODEL 확인).") from exc
        raise LLMUpstreamError() from exc
    except LLMError:
        raise
    except Exception as exc:  # 네트워크/타임아웃 등. 원본 메시지 비노출
        log.warning("Gemini call failed: %s", type(exc).__name__)
        raise LLMUpstreamError() from exc

    text = getattr(response, "text", None)
    if not text:
        raise LLMResponseError("AI가 빈 응답을 반환했습니다(안전 정책 차단 가능).")
    return text


def _parse(text: str, response_model: type[T]) -> T:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return response_model.model_validate(json.loads(cleaned))


def generate_json(
    prompt: str,
    response_model: type[T],
    *,
    system_instruction: str,
    mock_factory: Callable[[], dict],
    image_bytes: bytes | None = None,
    mime_type: str | None = None,
    validator: Callable[[T], None] | None = None,
) -> T:
    """프롬프트를 보내 ``response_model``로 검증된 결과를 반환한다.

    ``validator``는 추가 의미 검증(예: 모든 comment_id 포함)이며 ``ValueError``를
    던지면 검증 실패로 보고 한 번 재시도한다.
    mock 모드에서는 ``mock_factory()`` 결과를 같은 검증 경로로 통과시킨다.
    """
    if get_provider() == "mock":
        result = response_model.model_validate(mock_factory())
        if validator:
            validator(result)
        return result

    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            text = _call_gemini(prompt, system_instruction, image_bytes, mime_type)
            result = _parse(text, response_model)
            if validator:
                validator(result)
            return result
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            log.warning("LLM response validation failed (attempt %d): %s", attempt + 1, type(exc).__name__)
            last_exc = exc
        except LLMUpstreamError as exc:
            last_exc = exc
            if attempt == 1:
                raise
    if isinstance(last_exc, LLMError):
        raise last_exc
    raise LLMResponseError() from last_exc
