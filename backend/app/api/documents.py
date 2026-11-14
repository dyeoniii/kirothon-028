"""PDF 다운로드. PDF 바이트 생성은 [DOC] 함수가 담당(DB 접근 없음)."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api import adapters
from app.api.common import case_detail_dict, get_case_or_404
from app.api.errors import AppError, safe_message
from app.db import get_db

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


def _pdf_response(case_id: str, db: Session, func_name: str, filename: str, mask_author: bool = False) -> Response:
    case = get_case_or_404(db, case_id)
    case_data = case_detail_dict(case, saved_only=True, mask_authors=mask_author)
    if not case_data["comments"]:
        raise AppError(400, "NO_EVIDENCE", "저장된 증거가 없습니다. 댓글을 증거함에 저장한 뒤 다시 시도해 주세요.")
    generator: Callable[[dict], bytes] = getattr(adapters, func_name)
    try:
        pdf = generator(case_data)
    except adapters.ModuleNotConnectedError as exc:
        raise AppError(503, "MODULE_NOT_CONNECTED", str(exc)) from exc
    except Exception as exc:
        raise AppError(500, "PDF_FAILED", f"PDF 생성에 실패했습니다. ({safe_message(exc)})") from exc
    if not isinstance(pdf, (bytes, bytearray)) or not bytes(pdf).startswith(b"%PDF"):
        raise AppError(500, "PDF_INVALID", "생성된 PDF 형식이 올바르지 않습니다.")
    return Response(
        content=bytes(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}_{case.id}.pdf"'},
    )


@router.get("/statement.pdf")
def statement_pdf(case_id: str, mask_author: bool = False, db: Session = Depends(get_db)) -> Response:
    """mask_author=true면 작성자를 앞 1글자 + '**'로 가려 출력한다(기본은 원본)."""
    return _pdf_response(case_id, db, "generate_statement_pdf", "statement", mask_author)


@router.get("/evidence-list.pdf")
def evidence_list_pdf(case_id: str, mask_author: bool = False, db: Session = Depends(get_db)) -> Response:
    return _pdf_response(case_id, db, "generate_evidence_list_pdf", "evidence-list", mask_author)
