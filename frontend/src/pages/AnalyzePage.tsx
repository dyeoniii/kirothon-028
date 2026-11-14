import { ChevronRight, ImageUp, Link2, Plus, Type } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Badge, Button, ErrorBox, LoadingBlock, PageHeader, Panel, inputCls } from '../components/common';
import { errMessage, formatKst } from '../lib/format';
import type { CaseSummary } from '../types';

const METHODS = [
  { icon: Type, title: '텍스트', desc: '댓글을 붙여넣으면 한 줄에 하나씩 나눠요. 원본 게시글 주소와 맥락도 적을 수 있어요.' },
  { icon: ImageUp, title: '스크린샷', desc: 'png·jpg·webp, 파일당 10MB 이하. AI가 읽은 작성자·시각은 저장 전에 직접 확인해 주세요.' },
  { icon: Link2, title: 'SNS URL', desc: '유튜브 주소는 공개 댓글을 최대 200개까지 가져와요. 다른 SNS는 주소만 출처로 저장해요.' },
];

/** 어떤 사건에 댓글을 넣을지 고른 뒤 사건 상세의 입력 탭으로 이동합니다. */
export default function AnalyzePage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setCases(await api.listCases());
    } catch (e) {
      setError(errMessage(e));
      setCases([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function create() {
    if (!title.trim()) return setError('사건 제목을 입력해 주세요.');
    setBusy(true);
    setError(null);
    try {
      const c = await api.createCase({ title: title.trim(), description: '' });
      navigate(`/cases/${c.id}`);
    } catch (e) {
      setError(errMessage(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader title="새 악플 판독" desc="댓글을 정리할 사건을 정하면 입력 화면으로 이동해요." />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <Panel title="1. 새 사건으로 시작">
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                className={`${inputCls} sm:flex-1`}
                placeholder="사건 제목 (예: 게시물 A 비방 댓글)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !busy && void create()}
                aria-label="사건 제목"
              />
              <Button className="shrink-0" busy={busy} busyLabel="만드는 중…" onClick={() => void create()}>
                <Plus className="h-4 w-4" aria-hidden />
                사건 만들고 시작
              </Button>
            </div>
            <div className="mt-3">
              <ErrorBox message={error} onClose={() => setError(null)} onRetry={cases?.length === 0 ? () => void load() : undefined} />
            </div>
          </Panel>

          <Panel title="또는 기존 사건에 추가" flush>
            {cases === null && (
              <div className="p-4">
                <LoadingBlock />
              </div>
            )}
            {cases?.length === 0 && !error && <p className="p-5 text-sm text-ink-600">아직 사건이 없어요. 위에서 새 사건을 만들어 주세요.</p>}
            {cases?.map((c) => (
              <button key={c.id} type="button" onClick={() => navigate(`/cases/${c.id}`)} className="list-row w-full bg-transparent text-left hover:bg-brand-50">
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{c.title}</span>
                  <span className="block text-xs text-ink-600">{formatKst(c.created_at)}</span>
                </span>
                <Badge>증거 {c.saved_count}건</Badge>
                <ChevronRight className="h-4 w-4 shrink-0 text-ink-600" aria-hidden />
              </button>
            ))}
          </Panel>
        </div>

        <Panel title="2. 입력 방식 안내">
          <ul className="space-y-4">
            {METHODS.map(({ icon: Icon, title: t, desc }) => (
              <li key={t} className="flex gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                  <Icon className="h-4 w-4" aria-hidden />
                </span>
                <div>
                  <p className="text-sm font-bold">{t}</p>
                  <p className="text-sm text-ink-600">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-4 rounded-lg bg-ink-50 p-3 text-xs leading-relaxed text-ink-600">사건을 만들면 입력 → 판독 → 증거함 → 보완 → 문서 순서로 이어서 진행해요.</p>
        </Panel>
      </div>
    </div>
  );
}
