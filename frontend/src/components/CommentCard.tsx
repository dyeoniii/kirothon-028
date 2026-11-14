import { useState } from 'react';
import type { api } from '../api';
import { formatKst } from '../lib/format';
import { maskAuthor, useMaskAuthors } from '../lib/maskAuthors';
import type { CommentItem, Source } from '../types';
import { Button, LevelBadge, inputCls } from './common';

export type CommentPatchFn = (p: Parameters<typeof api.patchComment>[1]) => Promise<void>;

interface Props {
  c: CommentItem;
  source?: Source;
  /** extract: 수동 선택 판독 목록, review: 자동 판독 결과 목록(onToggle이 있을 때만 선택 가능), evidence: 증거함 */
  variant: 'extract' | 'review' | 'evidence';
  checked?: boolean;
  onToggle?: () => void;
  /** 체크박스 접근성 이름 */
  checkLabel?: string;
  /** 같은 작성자가 위험 신호 댓글을 남긴 횟수(2 이상일 때 배지 표시) */
  repeatCount?: number;
  onPatch: CommentPatchFn;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-bold text-ink-700">{title}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

export default function CommentCard({ c, source, variant, checked = false, onToggle, checkLabel, repeatCount = 0, onPatch }: Props) {
  const { mask } = useMaskAuthors();
  const author = mask ? maskAuthor(c.author) : c.author;
  const selectable = variant === 'extract' || (variant === 'review' && !!onToggle);
  const [note, setNote] = useState(c.user_note ?? '');
  const [pending, setPending] = useState(false);
  const a = c.analysis;
  const origin = c.comment_url ?? source?.url ?? null;

  async function patch(p: Parameters<CommentPatchFn>[0]) {
    setPending(true);
    try {
      await onPatch(p);
    } finally {
      setPending(false);
    }
  }

  const body = (
    <div className="min-w-0 flex-1">
      {(c.saved || repeatCount >= 2) && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {c.saved && (
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${
                c.user_confirmed ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-800'
              }`}
            >
              증거함 · {c.user_confirmed ? '내용 확인함' : '사용자 확인 전'}
            </span>
          )}
          {repeatCount >= 2 && (
            <span
              tabIndex={0}
              title="계정명이 같아도 같은 사람이라고 확정할 수 없습니다. 같은 작성자인지는 직접 확인해 주세요."
              aria-label={`반복 작성자 ${repeatCount}건. 계정명이 같아도 같은 사람이라고 확정할 수 없습니다.`}
              className="cursor-help rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700"
            >
              반복 작성자 {repeatCount}건
            </span>
          )}
        </div>
      )}
      <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">{c.content}</p>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs text-ink-600">
        <dt>작성자</dt>
        <dd>{author ?? '확인되지 않음'}</dd>
        <dt>작성 시각</dt>
        <dd>{formatKst(c.posted_at)}</dd>
        <dt>출처</dt>
        <dd className="break-all">{origin ?? '확인되지 않음'}</dd>
        {source && (
          <>
            <dt>수집 시각</dt>
            <dd>{formatKst(source.collected_at)}</dd>
          </>
        )}
        {source?.file_sha256 && (
          <>
            <dt>SHA-256</dt>
            <dd className="break-all font-mono">{source.file_sha256}</dd>
          </>
        )}
      </dl>
    </div>
  );

  return (
    <li className={`border-b border-ink-200 px-4 py-4 last:border-b-0 sm:px-5 ${c.saved ? 'bg-brand-50' : 'bg-white'}`}>
      {selectable ? (
        <label className="flex cursor-pointer items-start gap-3">
          <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-brand-600" checked={checked} onChange={onToggle} aria-label={checkLabel ?? '판독할 댓글 선택'} />
          {body}
        </label>
      ) : (
        <div className="flex">{body}</div>
      )}

      {a ? (
        <div className="report-block mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-bold tracking-wide text-ink-700">AI 판독 리포트</p>
            <LevelBadge level={a.level} label={a.level_label} />
          </div>
          {a.issues.length > 0 && (
            <Section title="법적 검토 쟁점">
              <div className="flex flex-wrap gap-1.5">
                {a.issues.map((i) => (
                  <span key={i} className="rounded-lg border border-brand-200 bg-white px-2.5 py-1 text-xs font-semibold text-brand-800">
                    {i}
                  </span>
                ))}
              </div>
            </Section>
          )}
          {a.flagged_phrases.length > 0 && (
            <Section title="문제 표현">
              <p className="font-medium">{a.flagged_phrases.map((p) => `“${p}”`).join(', ')}</p>
            </Section>
          )}
          {(a.statement_type || (a.related_laws?.length ?? 0) > 0) && (
            <div className="rounded-xl border border-dashed border-ink-300 bg-white p-3.5 text-xs">
              <p className="font-bold text-ink-700">참고 (AI 추정)</p>
              {a.statement_type && (
                <p className="mt-1 text-sm">
                  발언 유형: <b>{a.statement_type}</b>
                </p>
              )}
              {(a.related_laws?.length ?? 0) > 0 && (
                <div className="mt-1">
                  <p className="text-sm">관련될 수 있는 법조</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {a.related_laws?.map((l) => (
                      <span key={l} className="rounded-lg border border-ink-200 bg-ink-50 px-2.5 py-1 text-xs font-semibold text-ink-800">
                        {l}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <p className="mt-2 text-ink-600">참고용 분류이며 처벌이나 고소 성립 여부를 뜻하지 않습니다.</p>
            </div>
          )}
          <div className="rounded-lg border border-ink-200 bg-white p-3.5">
            <p className="text-xs font-bold text-ink-700">판단 근거</p>
            <p className="mt-1 leading-relaxed">{a.reason}</p>
          </div>
          {a.check_points.length > 0 && (
            <div className="rounded-lg border border-ink-200 bg-white p-3.5">
              <p className="text-xs font-bold text-ink-700">추가 확인 사항</p>
              <ul className="mt-2 space-y-1.5">
                {a.check_points.map((p) => (
                  <li key={p} className="flex items-start gap-2">
                    <span aria-hidden className="mt-0.5 h-4 w-4 shrink-0 rounded border-2 border-brand-400" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-ink-600">AI 추정입니다. {a.disclaimer}</p>
        </div>
      ) : (
        variant === 'evidence' && <p className="mt-3 rounded-xl bg-ink-50 p-3 text-xs text-ink-600">아직 AI 판독을 하지 않은 댓글입니다. 판독 탭에서 자동 판독하거나 직접 선택해 판독할 수 있습니다.</p>
      )}

      <details open={variant === 'evidence'} className="group mt-4 border-t border-ink-100 pt-3">
        <summary className="cursor-pointer select-none text-sm font-semibold text-ink-600">
          메모 · 확인 {c.user_confirmed && <span className="ml-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">내용 확인함</span>}
        </summary>
        <div className="mt-2 space-y-3">
          <textarea
            className={`${inputCls} min-h-16`}
            placeholder="메모 (사용자 입력)"
            aria-label="메모"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note !== (c.user_note ?? '') && void patch({ user_note: note || null })}
          />
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-5 w-5 accent-brand-600"
              checked={c.user_confirmed}
              disabled={pending}
              onChange={(e) => void patch({ user_confirmed: e.target.checked })}
            />
            원본과 비교해 내용을 확인했습니다
          </label>
        </div>
      </details>

      <Button
        variant={c.saved ? 'ghost' : 'primary'}
        className="mt-4 w-full"
        busy={pending}
        busyLabel="저장 중…"
        onClick={() => void patch({ saved: !c.saved })}
      >
        {c.saved ? '증거함에서 빼기' : '증거함에 저장'}
      </Button>
    </li>
  );
}
