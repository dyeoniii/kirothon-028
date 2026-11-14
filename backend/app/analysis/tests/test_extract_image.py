import json

import pytest

from app.analysis import extract_image as ex
from app.analysis import llm

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # 형식 시그니처만 갖춘 가상 바이트
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.parametrize("data,mime", [(PNG, "image/png"), (JPG, "image/jpeg"), (JPG, "image/jpg"), (WEBP, "image/webp")])
def test_mock_extract(mock_mode, data, mime):
    out = ex.extract_comments_from_image(data, mime)
    assert out and all(c["content"] for c in out)
    for c in out:
        assert c["author"] is None and c["posted_at"] is None
        assert set(c) == {"content", "author", "posted_at", "posted_at_text"}


@pytest.mark.parametrize(
    "data,mime",
    [(b"", "image/png"), (PNG, "image/gif"), (PNG, "application/pdf"), (JPG, "image/png"), (b"GIF89a....", "image/png")],
)
def test_invalid_images(mock_mode, data, mime):
    with pytest.raises(ex.ImageValidationError):
        ex.extract_comments_from_image(data, mime)


def test_too_large(mock_mode):
    with pytest.raises(ex.ImageValidationError) as ei:
        ex.extract_comments_from_image(PNG + b"\x00" * ex.MAX_IMAGE_BYTES, "image/png")
    assert ei.value.http_status == 413


def test_gemini_nulls_and_dates(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    payload = {
        "comments": [
            {"content": " 가상 댓글 하나 ", "author": "unknown", "posted_at_text": "3일 전", "posted_at": "2026-11-11"},
            {"content": "가상 댓글 둘", "author": "가상닉네임", "posted_at_text": None, "posted_at": "2026-11-14T12:00:00+09:00"},
            {"content": "   ", "author": None},
        ]
    }
    seen = {}

    def fake(prompt, system_instruction, image_bytes, mime_type):
        seen["mime"] = mime_type
        seen["bytes"] = image_bytes
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(llm, "_call_gemini", fake)
    out = ex.extract_comments_from_image(PNG, "image/png")
    assert seen == {"mime": "image/png", "bytes": PNG}
    assert len(out) == 2
    assert out[0] == {"content": "가상 댓글 하나", "author": None, "posted_at": None, "posted_at_text": "3일 전"}
    assert out[1]["author"] == "가상닉네임"
    assert out[1]["posted_at"] == "2026-11-14T03:00:00Z"


def test_gemini_missing_content_retries_then_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    n = {"c": 0}

    def fake(*a):
        n["c"] += 1
        return json.dumps({"comments": [{"author": "x"}]})

    monkeypatch.setattr(llm, "_call_gemini", fake)
    with pytest.raises(llm.LLMResponseError):
        ex.extract_comments_from_image(PNG, "image/png")
    assert n["c"] == 2
