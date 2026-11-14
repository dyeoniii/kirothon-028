import { Archive } from 'lucide-react';
import { useState } from 'react';
import { api } from '../api';
import { errMessage } from '../lib/format';
import type { CommentItem, Source } from '../types';
import CommentCard from './CommentCard';
import { Button, Disclaimer, EmptyState, ErrorBox } from './common';

interface Props {
  comments: CommentItem[];
  sources: Source[];
  onChange: (comments: CommentItem[]) => void;
  onGoComments: () => void;
}

/** 증거함에 저장한 댓글만 모아 보고 메모/확인 상태를 관리합니다. */
export default function EvidencePanel({ comments, sources, onChange, onGoComments }: Props) {
  const [error, setError] = useState<string | null>(null);
  const srcById = new Map(sources.map((s) => [s.id, s]));
  const saved = comments.filter((c) => c.saved);
  const confirmed = saved.filter((c) => c.user_confirmed).length;

  async function patch(id: string, p: Parameters<typeof api.patchComment>[1]) {
    setError(null);
    try {
      const updated = await api.patchComment(id, p);
      onChange(comments.map((c) => (c.id === id ? { ...c, ...updated, analysis: updated.analysis ?? c.analysis } : c)));
    } catch (e) {
      setError(errMessage(e));
    }
  }

  return (
    <div className="space-y-3">
      <ErrorBox message={error} onClose={() => setError(null)} />
      {saved.length === 0 ? (
        <EmptyState
          icon={<Archive className="h-5 w-5" aria-hidden />}
          title="증거함이 비어 있습니다"
          desc="판독 탭에서 보관할 댓글을 골라 ‘증거함에 저장’을 눌러 주세요."
          action={<Button onClick={onGoComments}>판독 탭으로 가기</Button>}
        />
      ) : (
        <>
          <p className="text-sm text-ink-600">
            저장된 증거 <b className="text-ink-900">{saved.length}건</b> · 내용 확인 {confirmed}건 · 사용자 확인 전 {saved.length - confirmed}건
          </p>
          <ul className="panel">
            {saved.map((c) => (
              <CommentCard key={c.id} c={c} variant="evidence" source={srcById.get(c.source_id)} onPatch={(p) => patch(c.id, p)} />
            ))}
          </ul>
        </>
      )}
      <Disclaimer />
    </div>
  );
}
