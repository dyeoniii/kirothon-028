import { Archive, ChevronDown, ChevronUp } from 'lucide-react';
import { Fragment, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import CommentCard from '../components/CommentCard';
import { Badge, Disclaimer, EmptyState, ErrorBox, LevelBadge, LoadingBlock, PageHeader, Panel } from '../components/common';
import { errMessage, formatKst } from '../lib/format';
import { useCaseDetails } from '../lib/useCaseDetails';
import type { CaseDetail, CommentItem } from '../types';

interface Row {
  c: CommentItem;
  d: CaseDetail;
}

/** 모든 사건의 저장된 증거를 표로 봅니다. 기존 listCases/getCase/patchComment만 사용합니다. */
export default function EvidencePage() {
  const { summaries, details, error, loading, reload, setDetails } = useCaseDetails(30);
  const [params, setParams] = useSearchParams();
  const q = (params.get('q') ?? '').trim().toLowerCase();
  const [actionError, setActionError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const all: Row[] = details.flatMap((d) => d.comments.filter((c) => c.saved).map((c) => ({ c, d })));
  const rows = q ? all.filter(({ c, d }) => [c.content, c.user_note ?? '', c.author ?? '', d.title].join(' ').toLowerCase().includes(q)) : all;

  async function patch(d: CaseDetail, id: string, p: Parameters<typeof api.patchComment>[1]) {
    setActionError(null);
    try {
      const updated = await api.patchComment(id, p);
      setDetails(
        details.map((x) =>
          x.id === d.id ? { ...x, comments: x.comments.map((c) => (c.id === id ? { ...c, ...updated, analysis: updated.analysis ?? c.analysis } : c)) } : x,
        ),
      );
    } catch (e) {
      setActionError(errMessage(e));
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader title="내 증거함" desc={`모든 사건에서 저장한 증거를 모아 봅니다.${loading ? '' : ` 현재 ${all.length}건`}`} />
      <ErrorBox message={error} onRetry={() => void reload()} />
      <ErrorBox message={actionError} onClose={() => setActionError(null)} />
      {loading && <LoadingBlock />}
      {!loading && rows.length === 0 && !error && (
        <EmptyState
          icon={<Archive className="h-5 w-5" aria-hidden />}
          title={q ? '검색 결과가 없습니다' : '저장된 증거가 없습니다'}
          desc={q ? '다른 검색어를 입력해 보세요.' : '사건의 판독 탭에서 보관할 댓글을 ‘증거함에 저장’해 주세요.'}
          action={
            q ? (
              <button type="button" className="btn btn-secondary" onClick={() => setParams({})}>
                검색 해제
              </button>
            ) : (
              <Link to={summaries && summaries.length ? '/cases' : '/analyze'} className="btn btn-primary">
                {summaries && summaries.length ? '내 사건 보기' : '악플 판독 시작하기'}
              </Link>
            )
          }
        />
      )}
      {rows.length > 0 && (
        <Panel title={`저장된 증거 (${rows.length})`} flush>
          {q && (
            <div className="flex items-center justify-between gap-2 border-b border-ink-200 bg-brand-50 px-5 py-2 text-sm">
              <span>
                “<b>{params.get('q')}</b>” 검색 결과
              </span>
              <button type="button" className="font-semibold text-brand-700 underline" onClick={() => setParams({})}>
                검색 해제
              </button>
            </div>
          )}
          <div className="table-wrap">
            <table className="dtable">
              <thead>
                <tr>
                  <th>댓글 / 메모</th>
                  <th className="hidden md:table-cell">사건</th>
                  <th className="hidden lg:table-cell">출처</th>
                  <th className="hidden md:table-cell">수집일</th>
                  <th>판독</th>
                  <th>확인</th>
                  <th className="text-right">
                    <span className="sr-only">상세</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ c, d }) => {
                  const src = d.sources.find((s) => s.id === c.source_id);
                  const isOpen = open === c.id;
                  return (
                    <Fragment key={c.id}>
                      <tr>
                        <td className="max-w-sm">
                          <p className="line-clamp-2 break-words font-medium">{c.content}</p>
                          {c.user_note && <p className="mt-0.5 line-clamp-1 text-xs text-ink-600">메모: {c.user_note}</p>}
                        </td>
                        <td className="hidden md:table-cell">
                          <Link to={`/cases/${d.id}`} className="font-semibold text-brand-700 hover:underline">
                            {d.title}
                          </Link>
                        </td>
                        <td className="hidden max-w-[12rem] break-all text-xs text-ink-600 lg:table-cell">{c.comment_url ?? src?.url ?? '확인되지 않음'}</td>
                        <td className="hidden whitespace-nowrap text-ink-600 md:table-cell">{formatKst(src?.collected_at)}</td>
                        <td>{c.analysis ? <LevelBadge level={c.analysis.level} label={c.analysis.level_label} /> : <Badge tone="neutral">미판독</Badge>}</td>
                        <td>{c.user_confirmed ? <Badge>확인함</Badge> : <span className="text-ink-600">-</span>}</td>
                        <td className="text-right">
                          <button type="button" className="btn btn-secondary btn-sm" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : c.id)}>
                            {isOpen ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
                            상세
                          </button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={7} className="!bg-ink-50 !p-0">
                            <ul>
                              <CommentCard c={c} variant="evidence" source={src} onPatch={(p) => patch(d, c.id, p)} />
                            </ul>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      <Disclaimer />
    </div>
  );
}
