"""사건의 판독 안 된 댓글 전체를 백그라운드로 자동 판독한다.

- 50개 단위 배치, 동시에 최대 3개 배치.
- 속도 제한(429)은 대기 후 재시도한다. 그 밖의 배치 실패는 건너뛰고 ``failed``에 센다
  (다시 실행하면 판독 안 된 댓글만 다시 시도).
- 진행 상황의 개수는 DB의 실제 판독 결과에서 센다. 실행 여부·실패 수·안내만 메모리에 둔다
  (로컬 단일 사용자 시연용이므로 서버를 재시작하면 실행 중 상태는 사라진다).
- 외부 AI에는 판독에 필요한 최소 정보(id, 본문, 게시글 맥락)만 전달한다.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import adapters
from app.api.analysis import save_analysis
from app.api.common import get_case_or_404
from app.api.errors import safe_message
from app.db import SessionLocal, get_db
from app.models import Analysis, Case, Comment, Source, utcnow
from app.schemas import AnalysisResult, AnalyzeAllStatus, LevelCounts

logger = logging.getLogger("akpleguard.api")
router = APIRouter(tags=["analysis"])

BATCH_SIZE = 15
MAX_CONCURRENT_BATCHES = 2
# 429 재시도 대기(초). 소진되면 해당 배치는 실패로 처리한다.
RATE_LIMIT_WAITS: tuple[float, ...] = (5, 10, 20, 40, 60, 60)
_FATAL_CODES = {"LLM_CONFIG_ERROR"}


def _sleep(seconds: float, stop_event: threading.Event) -> None:  # 테스트에서 교체
    stop_event.wait(seconds)  # 중단 요청이 오면 바로 깨어난다


@dataclass
class _Job:
    running: bool = False
    failed: int = 0
    error: str | None = None
    waiting: int = 0  # 429 대기 중인 배치 수
    force: bool = False  # 이미 판독된 댓글도 다시 판독
    run_total: int = 0  # 이번 실행의 대상 수
    run_done: int = 0  # 이번 실행에서 저장된 수
    abort: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)  # 사용자 중단 요청
    stopped: bool = False  # 중단 요청으로 끝났는지
    lock: threading.Lock = field(default_factory=threading.Lock)


_jobs: dict[str, _Job] = {}
_jobs_lock = threading.Lock()


def _is_rate_limited(exc: BaseException) -> bool:
    if getattr(exc, "http_status", None) == 429 or getattr(exc, "code", None) in ("LLM_RATE_LIMITED", 429):
        return True
    return "RESOURCE_EXHAUSTED" in str(exc)


class _FatalError(Exception):
    pass


class _Stopped(Exception):
    """사용자가 중단을 요청해 아직 시작하지 않은 배치를 건너뜀(실패로 세지 않는다)."""


def _analyze_batch(job: _Job, batch: list[tuple[str, str, str | None]]) -> list[AnalysisResult]:
    """한 배치를 판독하고 검증된 결과를 반환한다. 429는 대기 후 재시도, 형식 오류는 한 번만 재시도."""
    payload = [{"comment_id": cid, "content": content} for cid, content, _ in batch]
    allowed = {cid for cid, _, _ in batch}
    contexts = list(dict.fromkeys(ctx for _, _, ctx in batch if ctx))
    context = "\n\n".join(contexts) if contexts else None

    rate_waits = list(RATE_LIMIT_WAITS)
    format_retries = 1
    while True:
        if job.stop_event.is_set():
            raise _Stopped()
        if job.abort:
            raise _FatalError("중단됨")
        try:
            raw = adapters.analyze_comments(payload, context)
            if not isinstance(raw, list):
                raise ValueError("판독 결과가 list가 아닙니다.")
            results = [AnalysisResult.model_validate(r) for r in raw]
            results = [r for r in results if r.comment_id in allowed]
            if not results:
                raise ValueError("판독 결과가 비어 있습니다.")
            return results
        except adapters.ModuleNotConnectedError as exc:
            job.abort = True
            raise _FatalError(str(exc)) from exc
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            if format_retries <= 0:
                raise
            format_retries -= 1
            logger.warning("analyze-all batch format error, retrying once: %s", type(exc).__name__)
        except Exception as exc:
            if getattr(exc, "code", None) in _FATAL_CODES:
                job.abort = True
                raise _FatalError(safe_message(exc)) from exc
            if _is_rate_limited(exc) and rate_waits:
                wait = rate_waits.pop(0)
                with job.lock:
                    job.waiting += 1
                try:
                    _sleep(wait, job.stop_event)
                finally:
                    with job.lock:
                        job.waiting -= 1
                continue
            raise


def _run(case_id: str, job: _Job, items: list[tuple[str, str, str | None]]) -> None:
    db = SessionLocal()
    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES, thread_name_prefix="analyze-all")
    try:
        batches = [items[i : i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
        futures: dict[Future, list[tuple[str, str, str | None]]] = {
            executor.submit(_analyze_batch, job, b): b for b in batches
        }
        for fut in as_completed(futures):
            batch = futures[fut]
            try:
                results = fut.result()
            except _Stopped:
                continue
            except _FatalError as exc:
                job.failed += len(batch)
                job.error = job.error or str(exc)
                continue
            except Exception as exc:
                job.failed += len(batch)
                job.error = job.error or f"AI 판독 실패: {safe_message(exc)}"
                logger.warning("analyze-all batch failed: %s", safe_message(exc))
                continue
            try:
                if db.get(Case, case_id) is None:  # 판독 중 사건이 삭제됨
                    job.abort = True
                    for f in futures:
                        f.cancel()
                    break
                now = utcnow()
                comments = {
                    c.id: c
                    for c in db.scalars(select(Comment).where(Comment.id.in_([r.comment_id for r in results])))
                }
                for r in results:
                    if r.comment_id in comments:
                        save_analysis(comments[r.comment_id], r, now)
                db.commit()
                saved = {r.comment_id for r in results if r.comment_id in comments}
                job.run_done += len(saved)
                job.failed += len([cid for cid, _, _ in batch if cid not in saved])
            except Exception as exc:
                db.rollback()
                job.failed += len(batch)
                job.error = job.error or f"판독 결과 저장 실패: {safe_message(exc)}"
                logger.warning("analyze-all save failed: %s", safe_message(exc))
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        db.close()
        job.stopped = job.stop_event.is_set()
        job.running = False


def _status(db: Session, case_id: str) -> AnalyzeAllStatus:
    total = db.scalar(select(func.count()).select_from(Comment).where(Comment.case_id == case_id)) or 0
    rows = db.execute(
        select(Analysis.level, func.count())
        .join(Comment, Comment.id == Analysis.comment_id)
        .where(Comment.case_id == case_id)
        .group_by(Analysis.level)
    ).all()
    counts = LevelCounts(**{level: n for level, n in rows if level in LevelCounts.model_fields})
    analyzed = counts.legal_review + counts.needs_context + counts.low_risk
    job = _jobs.get(case_id)
    running = bool(job and job.running)
    pending = max(total - analyzed, 0)
    # 이후 수동 판독 등으로 처리된 댓글은 제외. 다시 판독(force) 실행은 이전 결과가 남아 있으므로 그대로 센다.
    failed = (job.failed if job.force else min(job.failed, pending)) if job else 0
    message = None
    if job:
        if not running and failed and job.force:
            message = f"{failed:,}개는 다시 판독하지 못했습니다. 이전 판독 결과는 그대로 남아 있습니다."
        elif running and job.stop_event.is_set():
            message = "진행 중인 배치를 마무리하고 중단합니다."
        elif not running and job.stopped:
            message = (
                f"판독을 중단했습니다. 남은 {pending:,}개는 이어서 판독할 수 있습니다."
                if pending
                else "판독을 중단했습니다."
            )
        elif running and job.waiting:
            message = "AI 사용량 제한으로 잠시 기다린 뒤 다시 시도하고 있습니다."
        elif not running and failed:
            message = f"{failed:,}개는 판독하지 못했습니다. 다시 실행하면 남은 댓글만 판독합니다."
    return AnalyzeAllStatus(
        case_id=case_id,
        running=running,
        stopping=bool(running and job and job.stop_event.is_set()),
        total=total,
        analyzed=analyzed,
        pending=pending,
        failed=failed,
        run_total=job.run_total if job else 0,
        run_done=job.run_done if job else 0,
        counts=counts,
        message=message,
        error=job.error if job and not running else None,
    )


@router.post("/cases/{case_id}/analyze-all", response_model=AnalyzeAllStatus, status_code=202)
def analyze_all(case_id: str, force: bool = False, db: Session = Depends(get_db)) -> AnalyzeAllStatus:
    """아직 판독되지 않은 댓글 전체를 백그라운드로 판독한다. 이미 실행 중이면 현재 상태만 반환.

    ``force=true``면 이미 판독된 댓글도 다시 판독한다(새 판독 기준 적용). 새 결과가 저장될 때까지 이전 결과는 유지된다.
    """
    get_case_or_404(db, case_id)
    query = (
        select(Comment.id, Comment.content, Source.context)
        .join(Source, Source.id == Comment.source_id)
        .where(Comment.case_id == case_id)
        .order_by(Comment.seq)
    )
    if not force:
        query = query.where(~Comment.analysis.has())
    rows = db.execute(query).all()
    items = [(cid, content, ctx) for cid, content, ctx in rows]
    with _jobs_lock:
        existing = _jobs.get(case_id)
        if items and not (existing and existing.running):
            job = _Job(running=True, force=force, run_total=len(items))
            _jobs[case_id] = job
            threading.Thread(target=_run, args=(case_id, job, items), name=f"analyze-all-{case_id}", daemon=True).start()
    return _status(db, case_id)


@router.post("/cases/{case_id}/analyze-all/stop", response_model=AnalyzeAllStatus)
def analyze_all_stop(case_id: str, db: Session = Depends(get_db)) -> AnalyzeAllStatus:
    """진행 중인 배치는 마무리하고 새 배치는 시작하지 않는다. 이미 저장된 판독 결과는 유지된다.
    실행 중이 아니면 아무 일도 하지 않고 현재 상태를 반환한다."""
    get_case_or_404(db, case_id)
    job = _jobs.get(case_id)
    if job and job.running:
        job.stop_event.set()
    return _status(db, case_id)


@router.get("/cases/{case_id}/analyze-all/status", response_model=AnalyzeAllStatus)
def analyze_all_status(case_id: str, db: Session = Depends(get_db)) -> AnalyzeAllStatus:
    get_case_or_404(db, case_id)
    return _status(db, case_id)
