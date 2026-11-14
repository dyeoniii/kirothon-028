"""PDF 생성 테스트. 실행: cd backend && pytest app/documents/tests -q"""
import copy
import os
import json
import re
from io import BytesIO
from pathlib import Path

import pytest

from app.documents import pdf as mod
from app.documents.pdf import (DocumentDataError, generate_evidence_list_pdf,
                               generate_statement_pdf)

SAMPLE = Path(__file__).resolve().parents[4] / "samples" / "sample_case.json"


@pytest.fixture(scope="module")
def case():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def _text(data: bytes) -> str:
    pypdf = pytest.importorskip("pypdf")
    r = pypdf.PdfReader(BytesIO(data))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def test_both_pdfs_are_valid_bytes(case):
    for fn in (generate_statement_pdf, generate_evidence_list_pdf):
        data = fn(case)
        assert data.startswith(b"%PDF") and len(data) > 2000


def test_korean_text_and_fields_in_pdf(case):
    s = _text(generate_statement_pdf(case))
    assert "사건 경위서" in s and "AI 분석은 법률 자문이 아닙니다" in s
    assert "그 사람은 사기꾼이다" in s            # 저장된 원문
    assert "AI 분석 추정" in s and "확인된 사실" in s
    assert "미확인" in s                           # null → 미확인
    e = _text(generate_evidence_list_pdf(case))
    assert "증거 목록" in e and case["sources"][1]["file_sha256"][:16] in e


def test_ref_text_has_reference_label_and_handles_missing():
    t = mod._ref_text({"statement_type": "의견 표명", "related_laws": ["형법 제311조(모욕)"]})
    assert t.count("[참고]") == 2 and "의견 표명" in t and "형법 제311조(모욕)" in t and "성립 여부를 뜻하지 않음" in t
    assert mod._ref_text(None) == mod.UNKNOWN
    assert mod._ref_text({"level": "low_risk"}) == mod.UNKNOWN
    assert "[참고] 발언 유형: 의견 표명" in mod._ref_text({"statement_type": "의견 표명", "related_laws": []})


def test_reference_fields_shown_with_reference_label(case):
    c = copy.deepcopy(case)
    saved = [x for x in c["comments"] if x.get("saved")]
    saved[0]["analysis"] = {"level": "needs_context", "level_label": "추가 맥락 확인 필요", "issues": [],
                            "flagged_phrases": [], "reason": "가상", "check_points": [],
                            "statement_type": "사실 적시", "related_laws": ["형법 제307조(명예훼손)"]}
    for fn in (generate_statement_pdf, generate_evidence_list_pdf):
        data = fn(c)
        assert data.startswith(b"%PDF")
    s = _text(generate_statement_pdf(c))
    e = _text(generate_evidence_list_pdf(c))
    for text in (s, e):
        assert "[참고]" in text and "사실 적시" in text and "형법 제307조" in text
    assert "AI 참고" in e


def test_only_saved_comments_included(case):
    e = _text(generate_evidence_list_pdf(case))
    assert "오늘 영상 편집 진짜 깔끔하네요" not in e  # saved=False
    assert "그 사람은 사기꾼이다" in e                  # saved=True


def test_no_saved_evidence_raises(case):
    c = copy.deepcopy(case)
    for x in c["comments"]:
        x["saved"] = False
    with pytest.raises(DocumentDataError):
        generate_statement_pdf(c)
    with pytest.raises(DocumentDataError):
        generate_evidence_list_pdf(c)


def test_missing_optional_keys_and_markup_safe(case):
    c = {"id": "case_x", "title": "<b>제목</b> & 특수", "comments": [
        {"id": "c1", "content": "<script>x</script> 줄1\n줄2", "saved": True}]}
    assert generate_statement_pdf(c).startswith(b"%PDF")
    assert generate_evidence_list_pdf(c).startswith(b"%PDF")


def test_does_not_mutate_input(case):
    before = copy.deepcopy(case)
    generate_statement_pdf(case); generate_evidence_list_pdf(case)
    assert case == before


def test_font_registered(case):
    generate_statement_pdf(case)
    assert mod._font_cache in {"KoreanBody", "HYSMyeongJo-Medium"}


def test_write_samples_for_visual_check(case, tmp_path):
    OUT = Path(os.environ.get("PDF_TEST_OUT", tmp_path))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "statement.pdf").write_bytes(generate_statement_pdf(case))
    (OUT / "evidence-list.pdf").write_bytes(generate_evidence_list_pdf(case))
