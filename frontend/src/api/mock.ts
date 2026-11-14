// 개발용 목 API. 백엔드 미구현 기능을 UI에서 확인하기 위한 임시 데이터이며
// 실제 판독/수집 결과가 아닙니다. VITE_USE_MOCK=true 일 때만 사용됩니다.
import { ApiError, type Api } from './types';
import {
  DISCLAIMER,
  LEVEL_LABEL,
  type Analysis,
  type AnalyzeAllStatus,
  type AnswerItem,
  type CaseDetail,
  type CommentItem,
  type InputResponse,
  type ReviewResponse,
  type Source,
} from '../types';

const KEY = 'akpleguard.mock.v1';

interface Db {
  seq: number;
  cases: CaseDetail[];
}

function load(): Db {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as Db;
  } catch {
    /* 손상된 데이터는 무시 */
  }
  return { seq: 0, cases: [] };
}

let db = load();
const save = () => localStorage.setItem(KEY, JSON.stringify(db));
const nid = (p: string) => `${p}_${++db.seq}`;
const now = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z');
const wait = <T,>(v: T, ms = 250) => new Promise<T>((r) => setTimeout(() => r(structuredClone(v)), ms));

function findCase(id: string): CaseDetail {
  const c = db.cases.find((x) => x.id === id);
  if (!c) throw new ApiError('사건을 찾을 수 없습니다.', 'NOT_FOUND', 404);
  return c;
}

function findComment(id: string): CommentItem {
  for (const c of db.cases) {
    const m = c.comments.find((x) => x.id === id);
    if (m) return m;
  }
  throw new ApiError('댓글을 찾을 수 없습니다.', 'NOT_FOUND', 404);
}

const makeSource = (type: Source['type'], url: string | null, extra: Partial<Source> = {}): Source => ({
  id: nid('src'),
  type,
  url,
  file_sha256: null,
  collected_at: now(),
  needs_manual_input: false,
  message: null,
  ...extra,
});

const makeComment = (sourceId: string, content: string, platform: string, extra: Partial<CommentItem> = {}): CommentItem => ({
  id: nid('cmt'),
  source_id: sourceId,
  author: null,
  content,
  posted_at: null,
  comment_url: null,
  platform,
  like_count: null,
  parent_id: null,
  saved: false,
  user_note: null,
  user_confirmed: false,
  analysis: null,
  ...extra,
});

// 간단한 키워드 규칙(새 판독 기준 반영). 실제 판독은 백엔드의 Gemini가 수행합니다.
function mockAnalysis(content: string): Analysis {
  const threat = ['죽여', '죽인다', '가만 안 둔다', '찾아간다'];
  const family = ['패드립', '니 애미', '느금'];
  const fact = ['사기꾼', '횡령', '불륜', '범죄자'];
  const curse = ['병신', '쓰레기', '멍청', 'ㅅㅂ', 'ㅆㅂ', 'ㅂㅅ'];
  const hit = (words: string[]) => words.filter((w) => content.includes(w));
  const base = { disclaimer: DISCLAIMER };
  const make = (
    level: Analysis['level'],
    flagged: string[],
    issues: string[],
    reason: string,
    checks: string[],
    statement_type: string,
    laws: string[],
  ): Analysis => ({
    ...base,
    level,
    level_label: LEVEL_LABEL[level],
    issues,
    flagged_phrases: flagged,
    reason: `[목 데이터] ${reason}`,
    check_points: checks,
    statement_type,
    related_laws: laws,
  });
  const askTarget = ['피해자가 특정되는지 확인', '게시 공개 범위 확인', '같은 작성자의 반복 여부 확인'];
  if (hit(threat).length)
    return make('legal_review', hit(threat), ['협박성 표현'], '해악을 알리는 표현으로 보일 수 있습니다.', askTarget, '해당 없음', ['형법 제283조(협박)']);
  if (hit(family).length)
    return make('legal_review', hit(family), ['모욕'], '가족을 비하하는 표현으로 보일 수 있습니다.', askTarget, '해당 없음', ['형법 제311조(모욕)']);
  if (hit(fact).length)
    return make(
      'needs_context',
      hit(fact),
      ['명예훼손(사실 적시)'],
      '사실을 적시한 표현일 수 있어 진위와 대상 특정 확인이 필요합니다.',
      ['사실 여부를 뒷받침할 자료 확인', ...askTarget],
      '사실 적시',
      ['형법 제307조(명예훼손)', '정보통신망법 제70조(사이버 명예훼손)'],
    );
  if (hit(curse).length)
    return make('low_risk', hit(curse), [], '단순 욕설·의견 표명으로 보여 위험 신호가 낮습니다. 합법을 뜻하지는 않습니다.', ['같은 작성자의 반복 여부 확인'], '의견 표명', []);
  return make('low_risk', [], [], '현재 자료에서는 뚜렷한 위험 신호가 보이지 않습니다. 합법을 뜻하지는 않습니다.', [], '해당 없음', []);
}

function review(c: CaseDetail): ReviewResponse {
  const saved = c.comments.filter((x) => x.saved);
  const withUrl = saved.filter((x) => x.comment_url || c.sources.find((s) => s.id === x.source_id)?.url);
  const withTime = saved.filter((x) => x.posted_at);
  const checklist: ReviewResponse['checklist'] = [
    {
      item: '저장된 증거',
      status: saved.length ? 'ok' : 'missing',
      detail: saved.length ? `${saved.length}건 저장됨` : '저장된 댓글이 없습니다',
    },
    {
      item: '원본 게시글 URL',
      status: !saved.length ? 'missing' : withUrl.length === saved.length ? 'ok' : withUrl.length ? 'partial' : 'missing',
      detail: `${saved.length}건 중 ${withUrl.length}건 확인`,
    },
    {
      item: '작성 시각',
      status: !saved.length ? 'missing' : withTime.length === saved.length ? 'ok' : withTime.length ? 'partial' : 'missing',
      detail: `${saved.length}건 중 ${withTime.length}건 확인`,
    },
  ];
  const okCount = checklist.filter((x) => x.status === 'ok').length;
  const answered = new Set(c.answers.map((a) => a.question_id));
  const questions = [
    { id: 'q1', question: '실제 어떤 피해가 있었나요?' },
    { id: 'q2', question: '작성자가 누구인지 알고 있나요?' },
  ].filter((q) => !answered.has(q.id));
  return { completeness: Math.round((okCount / checklist.length) * 100), checklist, questions };
}

const checkImage = (file: File) => {
  if (!/\.(png|jpe?g|webp)$/i.test(file.name)) throw new ApiError('png/jpg/jpeg/webp 파일만 올릴 수 있습니다.', 'VALIDATION_ERROR', 422);
  if (file.size > 10 * 1024 * 1024) throw new ApiError('파일은 10MB 이하여야 합니다.', 'VALIDATION_ERROR', 413);
};

async function sha256(file: File): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function ytId(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname === 'youtu.be') return u.pathname.slice(1) || null;
    if (/(^|\.)youtube\.com$/.test(u.hostname)) {
      if (u.pathname === '/watch') return u.searchParams.get('v');
      const m = /^\/shorts\/([^/]+)/.exec(u.pathname);
      return m ? m[1] : null;
    }
  } catch {
    /* 잘못된 URL */
  }
  return null;
}

// 전체 자동 판독 시뮬레이션: 300ms마다 50개씩 처리. 메모리에만 있는 진행 상태.
interface MockJob {
  running: boolean;
  stop: boolean;
  total: number;
  done: number;
}
const mockJobs = new Map<string, MockJob>();

function mockStatus(c: CaseDetail): AnalyzeAllStatus {
  const counts = { legal_review: 0, needs_context: 0, low_risk: 0 };
  for (const cm of c.comments) if (cm.analysis) counts[cm.analysis.level] += 1;
  const analyzed = counts.legal_review + counts.needs_context + counts.low_risk;
  const job = mockJobs.get(c.id);
  return {
    case_id: c.id,
    running: job?.running === true,
    stopping: job?.running === true && job.stop,
    total: c.comments.length,
    analyzed,
    pending: c.comments.length - analyzed,
    failed: 0,
    run_total: job?.total ?? 0,
    run_done: job?.done ?? 0,
    counts,
    message: null,
    error: null,
  };
}

export const mockApi: Api = {
  async createCase({ title, description }) {
    if (!title.trim()) throw new ApiError('사건 제목을 입력해 주세요.', 'VALIDATION_ERROR', 422);
    const c: CaseDetail = { id: nid('case'), title, description, created_at: now(), sources: [], comments: [], answers: [] };
    db.cases.unshift(c);
    save();
    return wait({ id: c.id, title, description, created_at: c.created_at });
  },
  async listCases() {
    return wait(db.cases.map((c) => ({ id: c.id, title: c.title, created_at: c.created_at, saved_count: c.comments.filter((x) => x.saved).length })));
  },
  async getCase(id) {
    return wait(findCase(id));
  },
  async deleteCase(id) {
    findCase(id);
    db.cases = db.cases.filter((c) => c.id !== id);
    save();
    return wait(undefined);
  },
  async inputUrl(caseId, url) {
    const c = findCase(caseId);
    const vid = ytId(url);
    let res: InputResponse;
    if (vid) {
      const src = makeSource('youtube', url);
      res = {
        source: src,
        total_available: 2,
        notice: null,
        comments: [
          makeComment(src.id, '[목 데이터] 시연용 가상 댓글 1', 'youtube', { author: '예시계정A' }),
          makeComment(src.id, '[목 데이터] 그 사람은 사기꾼이다', 'youtube', { author: '예시계정B' }),
        ],
      };
    } else {
      const src = makeSource('url_only', url, {
        needs_manual_input: true,
        message: '이 주소는 자동 수집을 지원하지 않습니다. 출처만 저장했으니 댓글 텍스트나 스크린샷을 직접 입력해 주세요.',
      });
      res = { source: src, comments: [] };
    }
    c.sources.push(res.source);
    c.comments.push(...res.comments);
    save();
    return wait(res, 500);
  },
  async inputText(caseId, { text, source_url }) {
    const c = findCase(caseId);
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    if (!lines.length) throw new ApiError('댓글 내용을 입력해 주세요.', 'VALIDATION_ERROR', 422);
    const src = makeSource('text', source_url);
    const res: InputResponse = { source: src, comments: lines.map((l) => makeComment(src.id, l, 'text')) };
    c.sources.push(src);
    c.comments.push(...res.comments);
    save();
    return wait(res);
  },
  async inputImage(caseId, file, sourceUrl) {
    checkImage(file);
    const c = findCase(caseId);
    const src = makeSource('image', sourceUrl, { file_sha256: await sha256(file) });
    const res: InputResponse = {
      source: src,
      comments: [makeComment(src.id, '[목 데이터] 이미지에서 추출된 가상 댓글', 'image')],
    };
    c.sources.push(src);
    c.comments.push(...res.comments);
    save();
    return wait(res, 700);
  },
  async analyze(caseId, ids) {
    const c = findCase(caseId);
    if (!ids.length) throw new ApiError('분석할 댓글을 선택해 주세요.', 'VALIDATION_ERROR', 422);
    const results = ids.map((id) => {
      const cm = c.comments.find((x) => x.id === id);
      if (!cm) throw new ApiError('댓글을 찾을 수 없습니다.', 'NOT_FOUND', 404);
      cm.analysis = mockAnalysis(cm.content);
      return { comment_id: id, ...cm.analysis };
    });
    save();
    return wait({ results }, 600);
  },
  async analyzeAll(caseId, force = false) {
    const c = findCase(caseId);
    const targets = c.comments.filter((x) => force || !x.analysis);
    if (!mockJobs.get(caseId)?.running && targets.length) {
      const job: MockJob = { running: true, stop: false, total: targets.length, done: 0 };
      mockJobs.set(caseId, job);
      const timer = setInterval(() => {
        if (job.stop) {
          clearInterval(timer);
          job.running = false;
          save();
          return;
        }
        for (const cm of targets.slice(job.done, job.done + 50)) cm.analysis = mockAnalysis(cm.content);
        job.done = Math.min(job.done + 50, job.total);
        if (job.done >= job.total || !db.cases.includes(c)) {
          clearInterval(timer);
          job.running = false;
          save();
        }
      }, 300);
    }
    return wait(mockStatus(c), 50);
  },
  async analyzeAllStop(caseId) {
    const job = mockJobs.get(caseId);
    if (job?.running) job.stop = true;
    return wait(mockStatus(findCase(caseId)), 50);
  },
  async bulkSave(body) {
    let targets: CommentItem[];
    if (body.level) {
      targets = findCase(body.case_id ?? '').comments.filter((c) => c.analysis?.level === body.level);
    } else {
      const ids = new Set(body.comment_ids ?? []);
      targets = db.cases.flatMap((c) => c.comments).filter((c) => ids.has(c.id));
    }
    for (const c of targets) c.saved = body.saved;
    const found = new Set(targets.map((c) => c.id));
    save();
    return wait({ saved: body.saved, updated: targets.length, comment_ids: [...found], missing: (body.comment_ids ?? []).filter((id) => !found.has(id)) }, 150);
  },
  async analyzeAllStatus(caseId) {
    return wait(mockStatus(findCase(caseId)), 50);
  },
  async patchComment(id, patch) {
    const cm = findComment(id);
    if (patch.saved !== undefined) cm.saved = patch.saved;
    if (patch.user_note !== undefined) cm.user_note = patch.user_note;
    if (patch.user_confirmed !== undefined) cm.user_confirmed = patch.user_confirmed;
    save();
    return wait(cm, 100);
  },
  async agentReview(caseId) {
    return wait(review(findCase(caseId)));
  },
  async agentAnswers(caseId, answers: AnswerItem[]) {
    const c = findCase(caseId);
    for (const a of answers) {
      const ex = c.answers.find((x) => x.question_id === a.question_id);
      if (ex) ex.answer = a.answer;
      else c.answers.push(a);
    }
    save();
    return wait(review(c));
  },
  async downloadDocument() {
    throw new ApiError('목 모드에서는 PDF를 만들 수 없습니다. 백엔드 연결 후 사용해 주세요.', 'MOCK_UNSUPPORTED', 501);
  },
};
