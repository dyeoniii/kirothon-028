"""사건 경위서 / 증거 목록 PDF 생성 (DB·파일 저장과 무관, bytes만 반환).

입력 `case_data`는 `GET /api/cases/{id}` 응답 형태의 dict이다.
선택 키 `answers`: [{"question_id": "q1", "question": "...", "answer": "..."}]
저장된(saved=True) 댓글만 포함하며, 없는 값은 '미확인'으로 표시한다.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DISCLAIMER = "AI 분석은 법률 자문이 아닙니다."
UNKNOWN = "미확인"
KST = timezone(timedelta(hours=9))

_FONT_NAME = "KoreanBody"
_CID_FALLBACK = "HYSMyeongJo-Medium"  # 내장 한글 CID 폰트 (뷰어에 한글 폰트 필요, 임베딩 안 됨)
_font_cache: str | None = None

_FONT_CANDIDATES = [
    # 환경변수 PDF_FONT_PATH 가 가장 먼저 검사된다.
    str(Path(__file__).parent / "fonts" / "NanumGothic.ttf"),
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
]


class DocumentDataError(ValueError):
    """문서를 만들 수 없는 입력(사건/저장된 증거 없음). API에서 400/422로 매핑."""


def _register_font() -> str:
    """한글 폰트 등록. TTF를 찾으면 임베딩, 없으면 CID 폰트로 대체한다."""
    global _font_cache
    if _font_cache:
        return _font_cache
    paths = [os.environ.get("PDF_FONT_PATH", "")] + _FONT_CANDIDATES
    for p in paths:
        if p and Path(p).is_file():
            try:
                pdfmetrics.registerFont(TTFont(_FONT_NAME, p))
                _font_cache = _FONT_NAME
                return _font_cache
            except Exception:  # CFF 기반 OTF/TTC 등 reportlab 미지원 → 다음 후보
                continue
    pdfmetrics.registerFont(UnicodeCIDFont(_CID_FALLBACK))
    _font_cache = _CID_FALLBACK
    return _font_cache


def _styles(font: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=font, wordWrap="CJK", leading=15, fontSize=10)
    return {
        "title": ParagraphStyle("title", **{**base, "fontSize": 20, "leading": 26, "alignment": TA_CENTER}),
        "h": ParagraphStyle("h", **{**base, "fontSize": 13, "leading": 18, "spaceBefore": 10,
                                    "spaceAfter": 4, "textColor": colors.HexColor("#1f3a5f")}),
        "body": ParagraphStyle("body", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 8, "leading": 11}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 8, "leading": 11}),
        "cellh": ParagraphStyle("cellh", **{**base, "fontSize": 8, "leading": 11,
                                            "textColor": colors.white}),
        "note": ParagraphStyle("note", **{**base, "fontSize": 9, "leading": 13,
                                          "backColor": colors.HexColor("#fff4e5"),
                                          "borderPadding": 5, "textColor": colors.HexColor("#7a4b00")}),
    }


# ---------------------------------------------------------------- helpers
def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_txt(text), style)


def _txt(value: Any) -> str:
    """None/빈 값은 '미확인', 그 외는 XML 이스케이프 + 줄바꿈 처리."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return UNKNOWN
    return escape(str(value)).replace("\r\n", "\n").replace("\n", "<br/>")


def _kst(iso: Any) -> str:
    """ISO-8601 UTC 문자열 → 'YYYY-MM-DD HH:MM KST'. 파싱 실패 시 원문 그대로."""
    if not iso:
        return UNKNOWN
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
    except ValueError:
        return str(iso)


def _validate(case_data: dict) -> tuple[list[dict], dict[str, dict]]:
    if not isinstance(case_data, dict) or not case_data.get("id") and not case_data.get("title"):
        raise DocumentDataError("사건 정보가 없습니다.")
    sources = {s.get("id"): s for s in case_data.get("sources") or [] if isinstance(s, dict)}
    saved = [c for c in case_data.get("comments") or [] if isinstance(c, dict) and c.get("saved")]
    if not saved:
        raise DocumentDataError("증거함에 저장된 댓글이 없습니다. 증거를 저장한 뒤 다시 시도해 주세요.")
    return saved, sources


def _build(story: list, pagesize, title: str) -> bytes:
    buf = BytesIO()
    font = _register_font()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.grey)
        w, _ = pagesize
        canvas.drawString(15 * mm, 8 * mm, f"악플가드 · {DISCLAIMER}")
        canvas.drawRightString(w - 15 * mm, 8 * mm, f"{doc.page} 쪽")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=pagesize, title=title, author="악플가드",
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=16 * mm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _grid(rows: list[list], widths: list[float], header: bool = True) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b7c3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")))
    else:
        style.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f6")))
    t.setStyle(TableStyle(style))
    return t


def _list_text(items: Any) -> str:
    if not items:
        return UNKNOWN
    return "\n".join(f"- {i}" for i in items)


def _ref_text(analysis: Any) -> str:
    """AI 판독의 참고용 필드(발언 유형·관련 법조). 값이 없으면 '미확인'. 항상 '참고' 표시를 붙인다."""
    if not isinstance(analysis, dict):
        return UNKNOWN
    st = analysis.get("statement_type")
    laws = analysis.get("related_laws")
    if not st and not laws:
        return UNKNOWN
    lines = [f"[참고] 발언 유형: {st or UNKNOWN}"]
    if laws:
        lines.append("[참고] 관련될 수 있는 법조: " + ", ".join(str(x) for x in laws))
        lines.append("(AI 추정이며 처벌·성립 여부를 뜻하지 않음)")
    return "\n".join(lines)


# ---------------------------------------------------------------- statement
def generate_statement_pdf(case_data: dict) -> bytes:
    """사건 경위서 PDF bytes. 저장된 증거가 없으면 DocumentDataError."""
    saved, sources = _validate(case_data)
    st = _styles(_register_font())
    story: list = [_p("사건 경위서", st["title"]), Spacer(1, 4 * mm),
                   _p(f"※ {DISCLAIMER} 이 문서는 서비스에 저장된 정보만 정리한 것이며, "
                      "고소 성립이나 결과를 보장하지 않습니다.", st["note"]),
                   Spacer(1, 3 * mm)]
    w = A4[0] - 30 * mm

    story.append(_p("1. 사건 개요", st["h"]))
    story.append(_grid([
        [_p("사건 번호", st["cell"]), _p(case_data.get("id"), st["cell"])],
        [_p("사건명", st["cell"]), _p(case_data.get("title"), st["cell"])],
        [_p("사건 설명(사용자 입력)", st["cell"]), _p(case_data.get("description"), st["cell"])],
        [_p("사건 생성 시각", st["cell"]), _p(_kst(case_data.get("created_at")), st["cell"])],
        [_p("저장된 증거 수", st["cell"]), _p(f"{len(saved)}건", st["cell"])],
    ], [35 * mm, w - 35 * mm], header=False))

    story.append(_p("2. 확인된 사실 (저장된 원문·출처 기준)", st["h"]))
    story.append(_p("아래는 수집된 원문과 출처 정보입니다. 값이 없는 항목은 '미확인'으로 표시하며 추측하지 않았습니다.",
                    st["small"]))
    story.append(Spacer(1, 2 * mm))
    for n, c in enumerate(saved, 1):
        src = sources.get(c.get("source_id")) or {}
        url = c.get("comment_url") or src.get("url")
        story.append(KeepTogether([_p(f"증거 {n}", st["body"]), _grid([
            [_p("댓글 원문", st["cell"]), _p(c.get("content"), st["cell"])],
            [_p("작성자", st["cell"]), _p(c.get("author"), st["cell"])],
            [_p("작성 시각", st["cell"]), _p(_kst(c.get("posted_at")), st["cell"])],
            [_p("플랫폼 / 출처 유형", st["cell"]),
             _p(f"{c.get('platform') or UNKNOWN} / {src.get('type') or UNKNOWN}", st["cell"])],
            [_p("출처 URL", st["cell"]), _p(url, st["cell"])],
            [_p("수집 시각", st["cell"]), _p(_kst(src.get("collected_at")), st["cell"])],
            [_p("사용자 확인", st["cell"]),
             _p("내용 확인함 (법적 사실 확정 아님)" if c.get("user_confirmed") else "확인 표시 없음 (사용자 확인 전)", st["cell"])],
            [_p("사용자 메모", st["cell"]), _p(c.get("user_note"), st["cell"])],
        ], [35 * mm, w - 35 * mm], header=False)]))
        story.append(Spacer(1, 3 * mm))

    story.append(_p("3. 사용자 추가 답변", st["h"]))
    answers = [a for a in case_data.get("answers") or [] if isinstance(a, dict)]
    if answers:
        rows = [[_p("질문", st["cellh"]), _p("답변(사용자 입력)", st["cellh"])]]
        for a in answers:
            rows.append([_p(a.get("question") or a.get("question_id"), st["cell"]),
                         _p(a.get("answer"), st["cell"])])
        story.append(_grid(rows, [60 * mm, w - 60 * mm]))
    else:
        story.append(_p("저장된 추가 답변이 없습니다.", st["body"]))

    story.append(_p("4. AI 분석 추정 (참고용)", st["h"]))
    story.append(_p(f"아래 내용은 AI가 생성한 검토 신호이며 사실 확인이 끝난 결과가 아닙니다. {DISCLAIMER}",
                    st["small"]))
    story.append(Spacer(1, 2 * mm))
    rows = [[_p("증거", st["cellh"]), _p("판독 단계", st["cellh"]), _p("검토 쟁점 / 문제 표현", st["cellh"]),
             _p("이유 및 확인할 점", st["cellh"])]]
    for n, c in enumerate(saved, 1):
        a = c.get("analysis")
        if not a:
            rows.append([_p(f"증거 {n}", st["cell"]), _p("분석 없음", st["cell"]),
                         _p(UNKNOWN, st["cell"]), _p(UNKNOWN, st["cell"])])
            continue
        rows.append([
            _p(f"증거 {n}", st["cell"]),
            _p(a.get("level_label") or a.get("level"), st["cell"]),
            _p("쟁점:\n" + _list_text(a.get("issues")) + "\n문제 표현:\n" + _list_text(a.get("flagged_phrases"))
               + "\n" + _ref_text(a), st["cell"]),
            _p((a.get("reason") or UNKNOWN) + "\n확인할 점:\n" + _list_text(a.get("check_points")), st["cell"]),
        ])
    story.append(_grid(rows, [16 * mm, 28 * mm, 55 * mm, w - 99 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(_p(f"※ {DISCLAIMER}", st["note"]))
    return _build(story, A4, f"사건 경위서 - {case_data.get('title') or ''}")


# ---------------------------------------------------------------- evidence list
def generate_evidence_list_pdf(case_data: dict) -> bytes:
    """증거 목록 PDF bytes (가로 A4). 저장된 증거가 없으면 DocumentDataError."""
    saved, sources = _validate(case_data)
    st = _styles(_register_font())
    pagesize = landscape(A4)
    w = pagesize[0] - 30 * mm
    story: list = [_p("증거 목록", st["title"]), Spacer(1, 3 * mm),
                   _p(f"사건: {_txt(case_data.get('title'))} ({_txt(case_data.get('id'))}) · "
                      f"저장된 증거 {len(saved)}건", st["body"]),
                   Spacer(1, 2 * mm),
                   _p(f"※ {DISCLAIMER} 값이 없는 항목은 '미확인'이며, 원문은 수정 없이 기재했습니다.", st["note"]),
                   Spacer(1, 3 * mm)]
    heads = ["번호", "작성자", "댓글 원문", "작성 시각", "출처 URL", "수집 시각", "SHA-256 (원본 파일)",
             "AI 참고 (추정)"]
    widths = [9 * mm, 22 * mm, w * 0.22, 24 * mm, w * 0.14, 24 * mm, w * 0.12, 0]
    widths[-1] = w - sum(widths[:-1])
    rows = [[_p(h, st["cellh"]) for h in heads]]
    for n, c in enumerate(saved, 1):
        src = sources.get(c.get("source_id")) or {}
        rows.append([
            _p(str(n), st["cell"]),
            _p(c.get("author"), st["cell"]),
            _p(c.get("content"), st["cell"]),
            _p(_kst(c.get("posted_at")), st["cell"]),
            _p(c.get("comment_url") or src.get("url"), st["cell"]),
            _p(_kst(src.get("collected_at")), st["cell"]),
            _p(src.get("file_sha256"), st["cell"]),
            _p(_ref_text(c.get("analysis")), st["cell"]),
        ])
    story.append(_grid(rows, widths))
    story.append(Spacer(1, 3 * mm))
    story.append(_p("SHA-256은 업로드된 원본 이미지 파일의 해시입니다. 텍스트/URL 입력은 원본 파일이 없어 '미확인'으로 표시됩니다.",
                    st["small"]))
    return _build(story, pagesize, f"증거 목록 - {case_data.get('title') or ''}")
