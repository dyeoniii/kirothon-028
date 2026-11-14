import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import { errMessage } from '../lib/format';
import type { AnswerItem, ReviewResponse } from '../types';
import { Button, Card, ErrorBox, InfoBox, LoadingBlock, inputCls } from './common';

const STATUS: Record<string, { label: string; cls: string }> = {
  ok: { label: '완료', cls: 'bg-emerald-50 text-emerald-700' },
  partial: { label: '일부 누락', cls: 'bg-amber-50 text-amber-800' },
  missing: { label: '누락', cls: 'bg-red-50 text-red-700' },
};

export default function ReviewPanel({
  caseId,
  savedAnswers,
  onSaved,
}: {
  caseId: string;
  savedAnswers: AnswerItem[];
  onSaved?: (answers: AnswerItem[]) => void;
}) {
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>(() => Object.fromEntries(savedAnswers.map((a) => [a.question_id, a.answer])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setReview(await api.agentReview(caseId));
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }, [caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit() {
    const list = Object.entries(answers)
      .filter(([, v]) => v.trim())
      .map(([question_id, answer]) => ({ question_id, answer: answer.trim() }));
    if (!list.length) return setError('답변을 하나 이상 입력해 주세요.');
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setReview(await api.agentAnswers(caseId, list));
      onSaved?.(list);
      setNotice('답변을 저장했습니다.');
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <ErrorBox message={error} onClose={() => setError(null)} onRetry={!review ? () => void load() : undefined} />
      {!review && busy && <LoadingBlock />}
      {review && (
        <>
          <Card>
            <div className="flex items-baseline justify-between">
              <h3 className="text-base font-bold">항목 작성률</h3>
              <span className="text-2xl font-bold text-brand-700">{review.completeness}%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded bg-ink-200">
              <div className="h-full bg-brand-600" style={{ width: `${Math.min(100, Math.max(0, review.completeness))}%` }} />
            </div>
            <p className="mt-2 text-xs text-ink-600">서비스 내 체크 항목을 채운 비율입니다. 소송 성공 가능성이나 증거의 법적 충분성을 뜻하지 않습니다.</p>
          </Card>

          <section className="space-y-3">
            <h3 className="text-base font-bold">증거 준비 체크리스트</h3>
            <ul className="grid gap-3 sm:grid-cols-2">
              {review.checklist.map((c) => {
                const s = STATUS[c.status] ?? { label: c.status, cls: 'bg-ink-100 text-ink-700' };
                return (
                  <li key={c.item} className="rounded-2xl border border-brand-100 bg-white p-4 shadow-card">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold">{c.item}</p>
                      <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>{s.label}</span>
                    </div>
                    <p className="mt-1 text-sm text-ink-600">{c.detail}</p>
                  </li>
                );
              })}
            </ul>
          </section>

          <Card className="space-y-3">
            <h3 className="text-base font-bold">추가 확인 질문</h3>
            {review.questions.length === 0 && Object.keys(answers).length === 0 && <InfoBox>추가로 확인할 질문이 없습니다.</InfoBox>}
            {review.questions.map((q) => (
              <label key={q.id} className="block text-sm font-medium">
                {q.question}
                <textarea className={`${inputCls} mt-1 min-h-20`} value={answers[q.id] ?? ''} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
              </label>
            ))}
            {Object.entries(answers)
              .filter(([id, v]) => v && !review.questions.some((q) => q.id === id))
              .map(([id, v]) => (
                <p key={id} className="rounded bg-ink-50 p-2 text-sm">
                  <span className="text-xs text-ink-600">저장된 답변 ({id})</span>
                  <br />
                  {v}
                </p>
              ))}
            {notice && <InfoBox>{notice}</InfoBox>}
            {review.questions.length > 0 && (
              <Button className="w-full" busy={busy} busyLabel="저장 중…" onClick={() => void submit()}>
                답변 저장
              </Button>
            )}
          </Card>
        </>
      )}
      <Button variant="ghost" className="w-full" busy={busy} busyLabel="확인 중…" onClick={() => void load()}>
        다시 확인
      </Button>
    </div>
  );
}
