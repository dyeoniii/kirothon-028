// docs/api-contract.md v2 기준 타입
export type SourceType = 'youtube' | 'text' | 'image' | 'url_only';
export type RiskLevel = 'legal_review' | 'needs_context' | 'low_risk';

export interface Source {
  id: string;
  type: SourceType;
  url: string | null;
  file_sha256: string | null;
  collected_at: string;
  needs_manual_input: boolean;
  message: string | null;
}

export interface Analysis {
  level: RiskLevel;
  level_label: string;
  issues: string[];
  flagged_phrases: string[];
  reason: string;
  check_points: string[];
  disclaimer: string;
  /** 참고용(AI 추정). 이전 판독 결과에는 없을 수 있음 */
  statement_type?: string | null;
  related_laws?: string[] | null;
}

export interface AnalysisResult extends Analysis {
  comment_id: string;
}

export interface CommentItem {
  id: string;
  source_id: string;
  author: string | null;
  content: string;
  posted_at: string | null;
  comment_url: string | null;
  platform: string;
  like_count: number | null;
  parent_id: string | null;
  saved: boolean;
  user_note: string | null;
  user_confirmed: boolean;
  analysis?: Analysis | null;
}

export interface AnswerItem {
  question_id: string;
  answer: string;
}

export interface CaseSummary {
  id: string;
  title: string;
  created_at: string;
  saved_count: number;
}

export interface CaseDetail {
  id: string;
  title: string;
  description: string;
  created_at: string;
  sources: Source[];
  comments: CommentItem[];
  answers: AnswerItem[];
}

export interface InputResponse {
  source: Source;
  comments: CommentItem[];
  /** YouTube 전체 댓글 수(답글 포함). 알 수 없으면 null/없음 */
  total_available?: number | null;
  /** 수집 한도 초과 안내. 없으면 null */
  notice?: string | null;
}

export interface AnalyzeAllStatus {
  case_id: string;
  running: boolean;
  /** 중단 요청을 받고 진행 중인 배치를 마무리하는 중 */
  stopping?: boolean;
  total: number;
  analyzed: number;
  pending: number;
  failed: number;
  /** 가장 최근 실행의 대상 수·저장 수(다시 판독이면 이미 판독된 댓글 포함) */
  run_total?: number;
  run_done?: number;
  counts: Record<RiskLevel, number>;
  message: string | null;
  error: string | null;
}

export interface ChecklistItem {
  item: string;
  status: 'ok' | 'partial' | 'missing' | string;
  detail: string;
}

export interface ReviewResponse {
  completeness: number;
  checklist: ChecklistItem[];
  questions: { id: string; question: string }[];
}

export interface CommentPatch {
  saved?: boolean;
  user_note?: string | null;
  user_confirmed?: boolean;
}

export interface BulkSaveRequest {
  saved: boolean;
  /** 둘 중 하나로 대상 지정: 댓글 id 목록, 또는 case_id + level */
  comment_ids?: string[];
  case_id?: string;
  level?: RiskLevel;
}

export interface BulkSaveResult {
  saved: boolean;
  updated: number;
  comment_ids: string[];
  missing: string[];
}

export type DocumentKind = 'statement' | 'evidence-list';

export const LEVEL_LABEL: Record<RiskLevel, string> = {
  legal_review: '법적 검토 필요',
  needs_context: '추가 맥락 확인 필요',
  low_risk: '위험 신호 낮음',
};

export const DISCLAIMER = 'AI 분석은 법률 자문이 아닙니다.';
