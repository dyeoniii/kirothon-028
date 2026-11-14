import type { CaseDetail } from '../types';

export type CaseStatusKey = 'draft' | 'analyzed' | 'needs_info' | 'doc_ready';

export interface CaseStatus {
  key: CaseStatusKey;
  label: string;
  /** index.css 의 .badge-* 클래스 */
  badge: string;
}

export const STATUS_FILTERS: { key: CaseStatusKey; label: string }[] = [
  { key: 'draft', label: '초안' },
  { key: 'analyzed', label: '분석 완료' },
  { key: 'needs_info', label: '보완 필요' },
  { key: 'doc_ready', label: '문서 작성 가능' },
];

/**
 * 사건 상세의 실제 데이터로만 계산하는 진행 상태입니다. 서버에 별도 상태 필드는 없습니다.
 * - 초안: 판독한 댓글이 아직 없음
 * - 분석 완료: 판독은 했지만 저장한 증거가 없음
 * - 보완 필요: 증거를 저장했으나 보완 질문 답변이 없음
 * - 문서 작성 가능: 증거를 저장했고 보완 답변도 있음
 */
export function caseStatus(d: CaseDetail): CaseStatus {
  const analyzed = d.comments.some((c) => c.analysis);
  const saved = d.comments.some((c) => c.saved);
  if (saved && d.answers.length > 0) return { key: 'doc_ready', label: '문서 작성 가능', badge: 'badge-low' };
  if (saved) return { key: 'needs_info', label: '보완 필요', badge: 'badge-context' };
  if (analyzed) return { key: 'analyzed', label: '분석 완료', badge: 'badge-brand' };
  return { key: 'draft', label: '초안', badge: 'badge-neutral' };
}
