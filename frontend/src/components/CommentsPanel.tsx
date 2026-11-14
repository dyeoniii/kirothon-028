import { Inbox } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { api } from '../api';
import { errMessage } from '../lib/format';
import type { Analysis, AnalysisResult, AnalyzeAllStatus, BulkSaveRequest, CommentItem, RiskLevel, Source } from '../types';
import CommentCard from './CommentCard';
import { Button, ConfirmModal, Disclaimer, EmptyState, ErrorBox, InfoBox, LevelBadge } from './common';

const MAX_BATCH = 20;
const PAGE = 30;

interface Props {
  caseId: string;
  comments: CommentItem[];
  sources: Source[];
  /** 전체 자동 판독이 진행 중이면 true */
  analyzing: boolean;
  status: AnalyzeAllStatus | null;
  onChange: (comments: CommentItem[]) => void;
  onGoInput: () => void;
  /** 이미 판독된 댓글까지 새 기준으로 다시 판독 */
  onReanalyze: () => void;
}

/** 많은 댓글을 한 번에 그리지 않도록 PAGE개씩 보여줍니다. */
function CardList({ items, render }: { items: CommentItem[]; render: (c: CommentItem) => ReactNode }) {
  const [shown, setShown] = useState(PAGE);
  return (
    <>
      <ul className="panel">{items.slice(0, shown).map(render)}</ul>
      {items.length > shown && (
        <Button variant="ghost" className="w-full" onClick={() => setShown((n) => n + PAGE)}>
          더 보기 ({(items.length - shown).toLocaleString()}개 남음)
        </Button>
      )}
    </>
  );
}

function Group({ level, items, render }: { level: RiskLevel; items: CommentItem[]; render: (c: CommentItem) => ReactNode }) {
  if (!items.length) return null;
  return (
    <section className="space-y-3" aria-label={`${level} 댓글`}>
      <h2 className="flex items-center gap-2 text-base font-bold text-ink-900">
        <LevelBadge level={level} /> {items.length.toLocaleString()}개
      </h2>
      <CardList items={items} render={render} />
    </section>
  );
}

export default function CommentsPanel({ caseId, comments, sources, analyzing, status, onChange, onGoInput, onReanalyze }: Props) {
  const [confirmRe, setConfirmRe] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lowOpen, setLowOpen] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [saveSel, setSaveSel] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [repeatOnly, setRepeatOnly] = useState(false);
  const srcById = new Map(sources.map((s) => [s.id, s]));

  // 같은 사건에서 같은 계정명이 법적 검토 필요·맥락 확인 필요 댓글을 남긴 횟수. 동일인 확정이 아니다.
  const repeatByAuthor = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of comments) {
      const lv = c.analysis?.level;
      const au = c.author?.trim();
      if (au && (lv === 'legal_review' || lv === 'needs_context')) m.set(au, (m.get(au) ?? 0) + 1);
    }
    return m;
  }, [comments]);
  const flaggedRepeat = (c: CommentItem) => {
    const au = c.author?.trim();
    const n = au ? (repeatByAuthor.get(au) ?? 0) : 0;
    return n >= 2 ? n : 0;
  };
  const repeatAuthors = [...repeatByAuthor.values()].filter((n) => n >= 2).length;

  function toggleSave(id: string) {
    setSaveSel((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function bulkSave(req: BulkSaveRequest, label: string) {
    setSaving(true);
    setError(null);
    setSaveMsg(null);
    try {
      const res = await api.bulkSave(req);
      const done = new Set(res.comment_ids);
      onChange(comments.map((c) => (done.has(c.id) ? { ...c, saved: req.saved } : c)));
      setSaveSel(new Set());
      setSaveMsg(`${label} ${res.updated.toLocaleString()}개를 ${req.saved ? '증거함에 저장했습니다. 저장된 증거는 “사용자 확인 전” 상태입니다.' : '증거함에서 뺐습니다.'}`);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setSaving(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function analyze() {
    const ids = [...selected];
    if (!ids.length) return setError('판독할 댓글을 선택해 주세요.');
    if (ids.length > MAX_BATCH) return setError(`한 번에 최대 ${MAX_BATCH}개까지 판독할 수 있습니다.`);
    setBusy(true);
    setError(null);
    try {
      const { results } = await api.analyze(caseId, ids);
      const byId = new Map<string, AnalysisResult>(results.map((r) => [r.comment_id, r]));
      onChange(
        comments.map((c) => {
          const r = byId.get(c.id);
          if (!r) return c;
          const { comment_id: _omit, ...analysis } = r;
          void _omit;
          return { ...c, analysis: analysis as Analysis };
        }),
      );
      setSelected(new Set());
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function patch(id: string, p: Parameters<typeof api.patchComment>[1]) {
    setError(null);
    try {
      const updated = await api.patchComment(id, p);
      onChange(comments.map((c) => (c.id === id ? { ...c, ...updated, analysis: updated.analysis ?? c.analysis } : c)));
    } catch (e) {
      setError(errMessage(e));
    }
  }

  const manual = sources.filter((s) => s.needs_manual_input);
  const notices = sources.filter((s) => !s.needs_manual_input && s.message);
  const byLevel = (lv: RiskLevel) => comments.filter((c) => c.analysis?.level === lv);
  const legal = byLevel('legal_review');
  const context = byLevel('needs_context');
  const low = byLevel('low_risk');
  // "반복 작성자만 보기" 필터는 목록 표시에만 적용한다(상단 요약 숫자는 전체 기준).
  const shown = (list: CommentItem[]) => (repeatOnly ? list.filter((c) => flaggedRepeat(c) >= 2) : list);
  const unsaved = (list: CommentItem[]) => list.filter((c) => !c.saved).length;
  const analyzedCount = legal.length + context.length + low.length;
  const pendingCount = comments.length - analyzedCount;

  const renderReview = (c: CommentItem) => (
    <CommentCard
      key={c.id}
      c={c}
      variant="review"
      source={srcById.get(c.source_id)}
      checked={saveSel.has(c.id)}
      onToggle={() => toggleSave(c.id)}
      checkLabel="증거함에 저장할 댓글 선택"
      repeatCount={c.analysis?.level === 'low_risk' ? 0 : flaggedRepeat(c)}
      onPatch={(p) => patch(c.id, p)}
    />
  );
  const renderManual = (c: CommentItem) => (
    <CommentCard
      key={c.id}
      c={c}
      variant="extract"
      source={srcById.get(c.source_id)}
      checked={selected.has(c.id)}
      onToggle={() => toggle(c.id)}
      onPatch={(p) => patch(c.id, p)}
    />
  );

  return (
    <div className="space-y-4">
      {notices.map((s) => (
        <InfoBox key={s.id}>{s.message}</InfoBox>
      ))}
      {manual.map((s) => (
        <InfoBox key={s.id} tone="warn">
          {s.url ? `${s.url} — ` : ''}
          {s.message ?? '자동 수집이 되지 않았습니다. 텍스트나 스크린샷으로 직접 입력해 주세요.'}
        </InfoBox>
      ))}
      {comments.length === 0 ? (
        <EmptyState
          icon={<Inbox className="h-5 w-5" aria-hidden />}
          title="아직 댓글이 없습니다"
          desc="텍스트, 스크린샷, 게시물 주소 중 하나로 댓글을 넣어 주세요."
          action={<Button onClick={onGoInput}>댓글 입력하러 가기</Button>}
        />
      ) : (
        <>
          <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-card" aria-live="polite">
            <p className="text-base font-bold text-ink-900">
              전체 {comments.length.toLocaleString()}개 중 법적 검토 필요 {legal.length.toLocaleString()}개, 맥락 확인 {context.length.toLocaleString()}개
            </p>
            <p className="mt-1 text-xs text-ink-600">
              위험 신호 낮음 {low.length.toLocaleString()}개
              {pendingCount > 0 && ` · ${analyzing ? '판독 중' : '미판독'} ${pendingCount.toLocaleString()}개`}
            </p>
          </div>

          {(legal.length > 0 || context.length > 0) && (
            <div className="space-y-2 rounded-2xl border border-brand-100 bg-white p-3 shadow-card">
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  className="min-h-10 px-3"
                  busy={saving}
                  busyLabel="저장 중…"
                  disabled={unsaved(legal) === 0}
                  onClick={() => void bulkSave({ saved: true, case_id: caseId, level: 'legal_review' }, '법적 검토 필요')}
                >
                  법적 검토 필요 전체 저장 ({unsaved(legal).toLocaleString()})
                </Button>
                <Button
                  className="min-h-10 px-3"
                  busy={saving}
                  busyLabel="저장 중…"
                  disabled={unsaved(context) === 0}
                  onClick={() => void bulkSave({ saved: true, case_id: caseId, level: 'needs_context' }, '맥락 확인 필요')}
                >
                  맥락 확인 필요 전체 저장 ({unsaved(context).toLocaleString()})
                </Button>
                <Button
                  variant="ghost"
                  className="min-h-10 px-3"
                  busy={saving}
                  busyLabel="저장 중…"
                  disabled={saveSel.size === 0}
                  onClick={() => void bulkSave({ saved: true, comment_ids: [...saveSel] }, '선택한 댓글')}
                >
                  선택한 {saveSel.size.toLocaleString()}개 저장
                </Button>
                {saveSel.size > 0 && (
                  <Button variant="ghost" className="min-h-10 px-3" onClick={() => setSaveSel(new Set())}>
                    선택 해제
                  </Button>
                )}
              </div>
              <p className="text-xs text-ink-600">일괄 저장한 증거는 “사용자 확인 전” 상태입니다. 원본과 비교해 직접 확인한 뒤 증거함에서 확인 표시를 해 주세요.</p>
              {saveMsg && <InfoBox>{saveMsg}</InfoBox>}
              {repeatAuthors > 0 && (
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input type="checkbox" className="h-5 w-5 accent-brand-600" checked={repeatOnly} onChange={(e) => setRepeatOnly(e.target.checked)} />
                  반복 작성자만 보기 ({repeatAuthors}명)
                </label>
              )}
              {repeatAuthors > 0 && <p className="text-xs text-ink-600">같은 계정명이 위험 신호 댓글을 2개 이상 남긴 경우입니다. 계정명이 같아도 같은 사람이라고 확정할 수 없습니다.</p>}
            </div>
          )}

          {analyzedCount > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-ink-200 bg-white p-3">
              <p className="text-xs text-ink-600">판독 기준이 바뀌었다면 이미 판독한 댓글도 다시 판독할 수 있습니다.</p>
              <Button variant="ghost" className="min-h-10 px-3" disabled={analyzing} onClick={() => setConfirmRe(true)}>
                새 기준으로 다시 판독
              </Button>
            </div>
          )}

          {analyzedCount === 0 && !analyzing && (
            <InfoBox>
              {status?.running === false && pendingCount > 0
                ? '아직 판독 결과가 없습니다. 위의 “전체 자동 판독” 버튼을 눌러 주세요.'
                : '판독 결과가 아직 없습니다.'}
            </InfoBox>
          )}

          <Group level="legal_review" items={shown(legal)} render={renderReview} />
          <Group level="needs_context" items={shown(context)} render={renderReview} />
          {repeatOnly && shown(legal).length + shown(context).length === 0 && <InfoBox>반복 작성자 댓글이 없습니다.</InfoBox>}

          {low.length > 0 && (
            <details className="rounded-2xl border border-ink-200 bg-white p-4" onToggle={(e) => setLowOpen(e.currentTarget.open)}>
              <summary className="cursor-pointer select-none text-sm font-semibold text-ink-700">
                <LevelBadge level="low_risk" /> {low.length.toLocaleString()}개 (눌러서 펼치기)
              </summary>
              <div className="mt-3 space-y-3">{lowOpen && <CardList items={shown(low)} render={renderReview} />}</div>
            </details>
          )}

          <details className="rounded-2xl border border-ink-200 bg-white p-4" onToggle={(e) => setManualOpen(e.currentTarget.open)}>
            <summary className="cursor-pointer select-none text-sm font-semibold text-ink-700">직접 골라서 판독하기 (보조 기능)</summary>
            {manualOpen && (
              <div className="mt-3 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-brand-100 bg-white p-3">
                  <span className="text-sm text-ink-600">
                    <b className="text-ink-900">{selected.size}개 선택</b> (최대 {MAX_BATCH})
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      className="min-h-10 px-3"
                      onClick={() => setSelected(selected.size ? new Set() : new Set(comments.slice(0, MAX_BATCH).map((c) => c.id)))}
                    >
                      {selected.size ? '선택 해제' : `처음 ${MAX_BATCH}개 선택`}
                    </Button>
                    <Button className="min-h-10 px-3" busy={busy} busyLabel="판독 중…" disabled={!selected.size} onClick={() => void analyze()}>
                      선택한 댓글 AI 판독
                    </Button>
                  </div>
                </div>
                <ErrorBox message={error} onClose={() => setError(null)} />
                <CardList items={comments} render={renderManual} />
              </div>
            )}
          </details>
        </>
      )}
      {!manualOpen && <ErrorBox message={error} onClose={() => setError(null)} />}
      <Disclaimer />
      <ConfirmModal
        open={confirmRe}
        title="새 기준으로 다시 판독할까요?"
        confirmLabel="다시 판독"
        message={
          <>
            <p>댓글 {comments.length.toLocaleString()}개를 AI로 다시 판독합니다. 시간이 걸릴 수 있습니다.</p>
            <p className="mt-1">새 결과가 저장되기 전까지 기존 판독 결과는 유지되며, 원문과 증거함·메모는 바뀌지 않습니다.</p>
          </>
        }
        onConfirm={() => {
          setConfirmRe(false);
          onReanalyze();
        }}
        onCancel={() => setConfirmRe(false)}
      />
    </div>
  );
}
