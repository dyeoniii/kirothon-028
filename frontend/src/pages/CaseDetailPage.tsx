import { ChevronLeft, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import CommentsPanel from '../components/CommentsPanel';
import DocumentsPanel from '../components/DocumentsPanel';
import AnalyzeProgress from '../components/AnalyzeProgress';
import EvidencePanel from '../components/EvidencePanel';
import InputPanel from '../components/InputPanel';
import ReviewPanel from '../components/ReviewPanel';
import { Button, Card, ConfirmModal, ErrorBox, InfoBox, LevelBadge, LoadingBlock, Panel, StatusBadge, TabBar, type TabItem } from '../components/common';
import { errMessage, formatKst } from '../lib/format';
import { useMaskAuthors } from '../lib/maskAuthors';
import { caseStatus } from '../lib/status';
import { useAnalyzeAll } from '../lib/useAnalyzeAll';
import { LEVEL_LABEL, type CaseDetail, type CommentItem, type InputResponse, type RiskLevel } from '../types';

type Tab = 'input' | 'comments' | 'evidence' | 'review' | 'docs';

export default function CaseDetailPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const sharedUrl = (location.state as { sharedUrl?: string } | null)?.sharedUrl ?? '';
  const [search] = useSearchParams();
  const initialTab = (['input', 'comments', 'evidence', 'review', 'docs'] as Tab[]).find((t) => t === search.get('tab')) ?? 'input';
  const [tab, setTab] = useState<Tab>(initialTab);
  const [data, setData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.getCase(id));
    } catch (e) {
      setError(errMessage(e));
    }
  }, [id]);

  useEffect(() => {
    setData(null);
    void load();
  }, [load]);

  const analyzeAll = useAnalyzeAll(id, load);
  const { mask, setMask } = useMaskAuthors();

  function onInput(res: InputResponse) {
    setData((d) => (d ? { ...d, sources: [...d.sources, res.source], comments: [...d.comments, ...res.comments] } : d));
    if (res.comments.length > 0) {
      setTab('comments');
      void analyzeAll.start(); // 입력이 끝나면 판독 안 된 댓글 전체를 자동 판독
    }
  }

  const setComments = (comments: CommentItem[]) => setData((d) => (d ? { ...d, comments } : d));

  async function remove() {
    setDeleting(true);
    try {
      await api.deleteCase(id);
      navigate('/cases', { replace: true });
    } catch (e) {
      setConfirmDelete(false);
      setError(errMessage(e));
      setDeleting(false);
    }
  }

  if (error && !data) {
    return (
      <div className="space-y-3">
        <ErrorBox message={error} onRetry={() => void load()} />
        <Button variant="ghost" onClick={() => navigate('/cases')}>
          사건 목록으로
        </Button>
      </div>
    );
  }
  if (!data) return <LoadingBlock />;

  const savedCount = data.comments.filter((c) => c.saved).length;
  const analyzedList = data.comments.filter((c) => c.analysis);
  const status = caseStatus(data);
  const tabs: TabItem<Tab>[] = [
    { key: 'input', label: '입력' },
    { key: 'comments', label: '판독', count: data.comments.length },
    { key: 'evidence', label: '증거함', count: savedCount },
    { key: 'review', label: '보완' },
    { key: 'docs', label: '문서' },
  ];

  return (
    <div className="space-y-5">
      <Card className="space-y-2">
        <Link to="/cases" className="inline-flex items-center text-sm font-semibold text-brand-700">
          <ChevronLeft className="h-4 w-4" aria-hidden />
          사건 목록
        </Link>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="break-words text-xl font-extrabold sm:text-2xl">{data.title}</h1>
            {data.description && <p className="mt-1 text-sm text-ink-600">{data.description}</p>}
            <p className="mt-1 text-xs text-ink-600">
              {formatKst(data.created_at)} · 댓글 {data.comments.length}개 · 증거 {savedCount}건
            </p>
          </div>
          <Button variant="danger" size="sm" className="shrink-0" onClick={() => setConfirmDelete(true)} aria-label="사건 삭제">
            <Trash2 className="h-4 w-4" aria-hidden />
            <span className="hidden sm:inline">삭제</span>
          </Button>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5 accent-brand-600" checked={mask} onChange={(e) => setMask(e.target.checked)} />
          작성자 가리기 (데모용 · 화면 표시만 바뀌고 저장된 원본은 그대로)
        </label>
        <ErrorBox message={error} onClose={() => setError(null)} />
      </Card>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 space-y-5">
      <TabBar label="사건 메뉴" items={tabs} value={tab} onChange={setTab} />

      <AnalyzeProgress status={analyzeAll.status} error={analyzeAll.error} onCloseError={analyzeAll.clearError} onStart={() => void analyzeAll.start()} onStop={() => void analyzeAll.stop()} />
      {tab === 'input' && (
        <>
          {sharedUrl && <InfoBox>공유받은 주소를 채웠습니다. 내용을 확인한 뒤 직접 “댓글 가져오기”를 눌러 주세요.</InfoBox>}
          <InputPanel caseId={data.id} initialUrl={sharedUrl} onDone={onInput} />
        </>
      )}
      {tab === 'comments' && (
        <CommentsPanel
          caseId={data.id}
          comments={data.comments}
          sources={data.sources}
          analyzing={analyzeAll.running}
          status={analyzeAll.status}
          onChange={setComments}
          onGoInput={() => setTab('input')}
          onReanalyze={() => void analyzeAll.start(true)}
        />
      )}
      {tab === 'evidence' && <EvidencePanel comments={data.comments} sources={data.sources} onChange={setComments} onGoComments={() => setTab('comments')} />}
      {tab === 'review' && <ReviewPanel
          caseId={data.id}
          savedAnswers={data.answers}
          onSaved={(list) =>
            setData((d) => (d ? { ...d, answers: [...d.answers.filter((a) => !list.some((n) => n.question_id === a.question_id)), ...list] } : d))
          }
        />}
      {tab === 'docs' && <DocumentsPanel caseId={data.id} savedCount={savedCount} />}
        </div>

        <aside className="hidden space-y-5 xl:block" aria-label="사건 요약">
          <Panel title="사건 요약">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-ink-600">상태</dt>
              <dd className="text-right">
                <StatusBadge badge={status.badge} label={status.label} />
              </dd>
              <dt className="text-ink-600">생성일</dt>
              <dd className="text-right">{formatKst(data.created_at)}</dd>
              <dt className="text-ink-600">댓글</dt>
              <dd className="text-right font-semibold">{data.comments.length}개</dd>
              <dt className="text-ink-600">판독 완료</dt>
              <dd className="text-right font-semibold">{analyzedList.length}개</dd>
              <dt className="text-ink-600">저장한 증거</dt>
              <dd className="text-right font-semibold">{savedCount}건</dd>
              <dt className="text-ink-600">내용 확인</dt>
              <dd className="text-right font-semibold">{data.comments.filter((c) => c.saved && c.user_confirmed).length}건</dd>
              <dt className="text-ink-600">보완 답변</dt>
              <dd className="text-right font-semibold">{data.answers.length}건</dd>
            </dl>
          </Panel>
          {analyzedList.length > 0 && (
            <Panel title="판독 결과 분포">
              <ul className="space-y-2 text-sm">
                {(['legal_review', 'needs_context', 'low_risk'] as RiskLevel[]).map((lv) => (
                  <li key={lv} className="flex items-center justify-between">
                    <LevelBadge level={lv} label={LEVEL_LABEL[lv]} />
                    <span className="font-bold">{analyzedList.filter((c) => c.analysis?.level === lv).length}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          <Panel title="문서">
            <Button variant="ghost" className="w-full" onClick={() => setTab('docs')}>
              문서 센터 열기
            </Button>
            <p className="mt-2 text-xs text-ink-600">사건 경위서와 증거자료 목록 PDF를 받을 수 있어요.</p>
          </Panel>
        </aside>
      </div>

      <ConfirmModal
        open={confirmDelete}
        title="사건을 삭제할까요?"
        message={
          <>
            <p className="font-semibold text-ink-900">“{data.title}”</p>
            <p className="mt-1">댓글 {data.comments.length}개, 판독 결과, 업로드한 원본 이미지가 모두 삭제되며 되돌릴 수 없습니다.</p>
          </>
        }
        busy={deleting}
        onConfirm={() => void remove()}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
