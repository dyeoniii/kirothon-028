import { Archive, ArrowRight, FileSearch, FileText, FolderOpen, ScanSearch, Scale } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Disclaimer, EmptyState, ErrorBox, KpiCard, LevelBadge, Panel, Skeleton, StatusBadge } from '../components/common';
import { formatKst } from '../lib/format';
import { caseStatus } from '../lib/status';
import { useCaseDetails } from '../lib/useCaseDetails';
import { LEVEL_LABEL, type RiskLevel } from '../types';

const GUIDE = ['사건 만들기', '댓글 입력(텍스트·스크린샷·URL)', 'AI 판독', '증거함 저장', '보완 답변 작성', 'PDF 2종 받기'];
const BAR: Record<RiskLevel, string> = { legal_review: 'bg-red-500', needs_context: 'bg-amber-500', low_risk: 'bg-emerald-500' };
const LEVELS: RiskLevel[] = ['legal_review', 'needs_context', 'low_risk'];

export default function DashboardPage() {
  const { summaries, details, error, loading, reload } = useCaseDetails(10);

  const totalEvidence = summaries?.reduce((n, c) => n + c.saved_count, 0) ?? 0;
  const analyzed = details.flatMap((d) => d.comments.filter((c) => c.analysis).map((c) => ({ c, title: d.title, caseId: d.id })));
  const count = (lv: RiskLevel) => analyzed.filter((x) => x.c.analysis?.level === lv).length;
  const rows = details.slice(0, 5).map((d) => ({ d, st: caseStatus(d) }));
  const needInfo = details.map((d) => ({ d, st: caseStatus(d) })).filter((x) => x.st.key === 'needs_info');
  const docReady = details.filter((d) => d.comments.some((c) => c.saved));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">대시보드</h1>
          <p className="mt-1 text-sm text-ink-600">악성 댓글 판독, 증거 정리, 문서 준비 현황을 한눈에 확인하세요.</p>
        </div>
        <Link to="/analyze" className="btn btn-primary">
          <ScanSearch className="h-4 w-4" aria-hidden />새 악플 판독
        </Link>
      </div>

      <ErrorBox message={error} onRetry={() => void reload()} />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard icon={<FolderOpen className="h-4 w-4" aria-hidden />} label="전체 사건" value={loading ? null : summaries!.length} note="만든 사건" />
        <KpiCard icon={<Archive className="h-4 w-4" aria-hidden />} label="저장된 증거" value={loading ? null : totalEvidence} note="증거함에 저장한 댓글" />
        <KpiCard icon={<FileSearch className="h-4 w-4" aria-hidden />} label="판독한 댓글" value={loading ? null : analyzed.length} note="최근 사건 10개 기준" />
        <KpiCard icon={<Scale className="h-4 w-4" aria-hidden />} label="법적 검토 필요" value={loading ? null : count('legal_review')} note="최근 사건 10개 기준" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-5">
          <Panel
            title="사건 현황"
            flush
            action={
              <Link to="/cases" className="text-sm font-semibold text-brand-700">
                전체 보기
              </Link>
            }
          >
            {loading && <Skeleton className="m-4 h-16 !bg-ink-100" />}
            {!loading && rows.length === 0 && !error && (
              <div className="p-4">
                <EmptyState icon={<FolderOpen className="h-5 w-5" aria-hidden />} title="아직 사건이 없습니다" desc="새 악플 판독을 시작하면 사건이 만들어져요." />
              </div>
            )}
            {rows.length > 0 && (
              <div className="table-wrap">
                <table className="dtable">
                  <thead>
                    <tr>
                      <th>사건명</th>
                      <th className="num hidden sm:table-cell">댓글</th>
                      <th className="num hidden sm:table-cell">증거</th>
                      <th className="hidden md:table-cell">생성일</th>
                      <th>상태</th>
                      <th className="text-right">
                        <span className="sr-only">열기</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(({ d, st }) => (
                      <tr key={d.id}>
                        <td className="cell-title">{d.title}</td>
                        <td className="num hidden sm:table-cell">{d.comments.length}</td>
                        <td className="num hidden sm:table-cell">{d.comments.filter((c) => c.saved).length}</td>
                        <td className="hidden whitespace-nowrap text-ink-600 md:table-cell">{formatKst(d.created_at)}</td>
                        <td>
                          <StatusBadge badge={st.badge} label={st.label} />
                        </td>
                        <td className="text-right">
                          <Link to={`/cases/${d.id}`} className="btn btn-secondary btn-sm" aria-label={`${d.title} 열기`}>
                            열기
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel title="진행 중 보완 항목" flush>
            {needInfo.length === 0 ? (
              <p className="p-5 text-sm text-ink-600">보완 답변이 필요한 사건이 없어요. 증거를 저장한 사건에서 보완 질문 답변을 작성하면 문서를 만들 수 있어요.</p>
            ) : (
              needInfo.map(({ d }) => (
                <Link key={d.id} to={`/cases/${d.id}?tab=review`} className="list-row">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{d.title}</span>
                    <span className="block text-xs text-ink-600">저장한 증거 {d.comments.filter((c) => c.saved).length}건 · 보완 답변 없음</span>
                  </span>
                  <span className="shrink-0 text-sm font-semibold text-brand-700">보완하기</span>
                </Link>
              ))
            )}
          </Panel>
        </div>

        <div className="space-y-5">
          <section className="cta-card rounded-card p-5 shadow-card">
            <h2 className="cta-title text-base font-bold">빠른 시작</h2>
            <p className="cta-desc mt-1 text-sm">댓글을 입력하면 AI가 위험 신호를 알려 드려요. 결정은 사용자가 합니다.</p>
            <Link to="/analyze" className="cta-btn mt-4 w-full">
              악플 판독 시작하기
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </section>

          <Panel title="최근 판독 결과" flush>
            {analyzed.length === 0 && <p className="p-5 text-sm text-ink-600">아직 판독한 댓글이 없어요.</p>}
            {analyzed.slice(0, 4).map(({ c, title, caseId }) => (
              <Link key={c.id} to={`/cases/${caseId}`} className="list-row !items-start">
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <LevelBadge level={c.analysis!.level} label={c.analysis!.level_label} />
                    <span className="truncate text-xs text-ink-600">{title}</span>
                  </span>
                  <span className="mt-1.5 line-clamp-2 block break-words text-sm">{c.content}</span>
                </span>
              </Link>
            ))}
            {analyzed.length > 0 && (
              <div className="space-y-2 border-t border-ink-200 p-4">
                {LEVELS.map((lv) => (
                  <div key={lv}>
                    <div className="flex justify-between text-xs">
                      <span className="font-medium">{LEVEL_LABEL[lv]}</span>
                      <span className="font-bold">{count(lv)}</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-100">
                      <div className={`h-full rounded-full ${BAR[lv]}`} style={{ width: `${(count(lv) / analyzed.length) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="문서 다운로드 바로가기" flush>
            {docReady.length === 0 && <p className="p-5 text-sm text-ink-600">증거를 저장한 사건이 생기면 문서를 받을 수 있어요.</p>}
            {docReady.slice(0, 3).map((d) => (
              <Link key={d.id} to={`/cases/${d.id}?tab=docs`} className="list-row">
                <FileText className="h-4 w-4 shrink-0 text-brand-700" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm font-semibold">{d.title}</span>
                <span className="shrink-0 text-xs font-semibold text-brand-700">PDF 2종</span>
              </Link>
            ))}
          </Panel>

          <Panel title="사용 가이드">
            <ol className="space-y-1.5 text-sm">
              {GUIDE.map((g, i) => (
                <li key={g} className="flex gap-2.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">{i + 1}</span>
                  {g}
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
      <Disclaimer />
    </div>
  );
}
