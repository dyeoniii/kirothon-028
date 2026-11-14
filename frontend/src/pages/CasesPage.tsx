import { FolderOpen, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Button, ConfirmModal, Disclaimer, EmptyState, ErrorBox, LoadingBlock, PageHeader, Panel, StatusBadge, inputCls } from '../components/common';
import { errMessage, formatKst } from '../lib/format';
import { STATUS_FILTERS, caseStatus, type CaseStatusKey } from '../lib/status';
import { useCaseDetails } from '../lib/useCaseDetails';
import type { CaseSummary } from '../types';

export default function CasesPage() {
  const { summaries: cases, details, error: listError, reload } = useCaseDetails(50);
  const [params, setParams] = useSearchParams();
  const q = (params.get('q') ?? '').trim().toLowerCase();
  const [filter, setFilter] = useState<CaseStatusKey | 'all'>('all');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<CaseSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const detailById = new Map(details.map((d) => [d.id, d]));
  const sorted = cases ? [...cases].sort((a, b) => b.created_at.localeCompare(a.created_at)) : null;
  const visible = sorted?.filter((c) => {
    const d = detailById.get(c.id);
    if (filter !== 'all' && (!d || caseStatus(d).key !== filter)) return false;
    if (!q) return true;
    const hay = [c.title, d?.description ?? '', ...(d?.comments.flatMap((x) => [x.content, x.user_note ?? '']) ?? [])].join(' ').toLowerCase();
    return hay.includes(q);
  });

  async function create() {
    if (!title.trim()) return setError('사건 제목을 입력해 주세요.');
    setBusy(true);
    setError(null);
    try {
      await api.createCase({ title: title.trim(), description: description.trim() });
      setTitle('');
      setDescription('');
      await reload();
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!target) return;
    setDeleting(true);
    try {
      await api.deleteCase(target.id);
      setTarget(null);
      await reload();
    } catch (e) {
      setTarget(null);
      setError(errMessage(e));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader title="내 사건 관리" desc="사건마다 댓글, 판독 결과, 증거를 따로 보관합니다." />

      <Panel title="새 사건 만들기">
        <div className="grid gap-3 md:grid-cols-[1fr_1.4fr_auto] md:items-end">
          <label className="field-label">
            사건 제목
            <input className={`${inputCls} mt-1.5 font-normal`} placeholder="예: 게시물 A 비방 댓글" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="field-label">
            사건 설명 (선택)
            <input className={`${inputCls} mt-1.5 font-normal`} placeholder="어떤 일이 있었는지 간단히 적어 주세요" value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <Button busy={busy} busyLabel="만드는 중…" onClick={() => void create()}>
            <Plus className="h-4 w-4" aria-hidden />
            사건 만들기
          </Button>
        </div>
        <div className="mt-3 empty:hidden">
          <ErrorBox message={error} onClose={() => setError(null)} />
        </div>
      </Panel>

      <Panel
        title={`사건 목록${visible ? ` (${visible.length})` : ''}`}
        flush
        action={
          <div className="flex flex-wrap justify-end gap-1.5" role="group" aria-label="상태 필터">
            <button type="button" className="chip" aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>
              전체
            </button>
            {STATUS_FILTERS.map((f) => (
              <button key={f.key} type="button" className="chip" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
                {f.label}
              </button>
            ))}
          </div>
        }
      >
        {q && (
          <div className="flex items-center justify-between gap-2 border-b border-ink-200 bg-brand-50 px-5 py-2 text-sm">
            <span>
              “<b>{params.get('q')}</b>” 검색 결과 (사건명·설명·댓글·메모)
            </span>
            <button type="button" className="font-semibold text-brand-700 underline" onClick={() => setParams({})}>
              검색 해제
            </button>
          </div>
        )}
        <div className="px-5 pt-4 empty:hidden">
          <ErrorBox message={listError} onRetry={() => void reload()} />
        </div>
        {cases === null && (
          <div className="p-4">
            <LoadingBlock />
          </div>
        )}
        {visible?.length === 0 && !listError && (
          <div className="p-4">
            <EmptyState
              icon={<FolderOpen className="h-5 w-5" aria-hidden />}
              title={cases && cases.length > 0 ? '조건에 맞는 사건이 없습니다' : '아직 사건이 없습니다'}
              desc={cases && cases.length > 0 ? '검색어나 상태 필터를 바꿔 보세요.' : '위에서 첫 사건을 만들어 보세요.'}
            />
          </div>
        )}
        {visible && visible.length > 0 && (
          <div className="table-wrap">
            <table className="dtable">
              <thead>
                <tr>
                  <th>사건명</th>
                  <th className="num hidden sm:table-cell">댓글</th>
                  <th className="num hidden sm:table-cell">증거</th>
                  <th className="hidden md:table-cell">생성일</th>
                  <th>상태</th>
                  <th className="text-right">액션</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((c) => {
                  const d = detailById.get(c.id);
                  const st = d ? caseStatus(d) : null;
                  return (
                    <tr key={c.id}>
                      <td>
                        <Link to={`/cases/${c.id}`} className="cell-title hover:underline">
                          {c.title}
                        </Link>
                        <p className="mt-0.5 line-clamp-1 max-w-xs text-xs text-ink-600">{d ? d.description || '설명 없음' : ''}</p>
                      </td>
                      <td className="num hidden sm:table-cell">{d ? d.comments.length : '-'}</td>
                      <td className="num hidden sm:table-cell">{c.saved_count}</td>
                      <td className="hidden whitespace-nowrap text-ink-600 md:table-cell">{formatKst(c.created_at)}</td>
                      <td>{st ? <StatusBadge badge={st.badge} label={st.label} /> : <span className="text-ink-600">-</span>}</td>
                      <td>
                        <div className="flex justify-end gap-1.5">
                          <Link to={`/cases/${c.id}`} className="btn btn-primary btn-sm">
                            상세 보기
                          </Link>
                          <Button variant="danger" size="sm" onClick={() => setTarget(c)} aria-label={`${c.title} 삭제`}>
                            <Trash2 className="h-4 w-4" aria-hidden />
                            <span className="hidden sm:inline">삭제</span>
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <p className="text-xs text-ink-600">상태는 사건의 판독·증거·보완 답변 데이터로 계산합니다. 서버에 저장된 값이 아니며, API에 수정일이 없어 생성일을 표시합니다.</p>
      <Disclaimer />

      <ConfirmModal
        open={target !== null}
        title="사건을 삭제할까요?"
        message={
          <>
            <p className="font-semibold text-ink-900">“{target?.title}”</p>
            <p className="mt-1">댓글, 판독 결과, 업로드한 원본 이미지가 모두 삭제되며 되돌릴 수 없습니다.</p>
          </>
        }
        busy={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setTarget(null)}
      />
    </div>
  );
}
