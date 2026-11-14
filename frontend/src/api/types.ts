import type {
  AnalysisResult,
  AnalyzeAllStatus,
  BulkSaveRequest,
  BulkSaveResult,
  AnswerItem,
  CaseDetail,
  CaseSummary,
  CommentItem,
  CommentPatch,
  DocumentKind,
  InputResponse,
  ReviewResponse,
} from '../types';

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code = 'UNKNOWN', status = 0) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/** 실제 API(client.ts)와 목(mock.ts)이 함께 구현하는 인터페이스 */
export interface Api {
  createCase(body: { title: string; description: string }): Promise<{ id: string; title: string; description: string; created_at: string }>;
  listCases(): Promise<CaseSummary[]>;
  getCase(id: string): Promise<CaseDetail>;
  deleteCase(id: string): Promise<void>;
  inputUrl(caseId: string, url: string): Promise<InputResponse>;
  inputText(caseId: string, body: { text: string; source_url: string | null; context: string | null }): Promise<InputResponse>;
  inputImage(caseId: string, file: File, sourceUrl: string | null, context: string | null): Promise<InputResponse>;
  analyze(caseId: string, commentIds: string[]): Promise<{ results: AnalysisResult[] }>;
  /** 판독 안 된 댓글 전체를 서버에서 백그라운드로 판독 시작(이미 실행 중이면 현재 상태 반환). force=true면 이미 판독된 댓글도 다시 판독 */
  analyzeAll(caseId: string, force?: boolean): Promise<AnalyzeAllStatus>;
  analyzeAllStatus(caseId: string): Promise<AnalyzeAllStatus>;
  /** 진행 중인 배치는 마무리하고 새 배치는 시작하지 않음. 저장된 결과는 유지 */
  analyzeAllStop(caseId: string): Promise<AnalyzeAllStatus>;
  /** 증거함 일괄 저장/해제. 사용자 확인 상태는 바꾸지 않음 */
  bulkSave(body: BulkSaveRequest): Promise<BulkSaveResult>;
  patchComment(commentId: string, patch: CommentPatch): Promise<CommentItem>;
  agentReview(caseId: string): Promise<ReviewResponse>;
  agentAnswers(caseId: string, answers: AnswerItem[]): Promise<ReviewResponse>;
  downloadDocument(caseId: string, kind: DocumentKind, maskAuthor?: boolean): Promise<{ blob: Blob; filename: string }>;
}
