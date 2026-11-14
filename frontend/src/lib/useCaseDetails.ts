import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { CaseDetail, CaseSummary } from '../types';
import { errMessage } from './format';

interface State {
  summaries: CaseSummary[] | null;
  details: CaseDetail[];
  error: string | null;
}

/**
 * 기존 API(listCases, getCase)만 조합해 여러 사건의 상세를 읽어 옵니다.
 * 최근 사건 `limit`개까지만 상세를 조회합니다. 일부 사건 조회가 실패해도 나머지는 표시합니다.
 */
export function useCaseDetails(limit: number) {
  const [state, setState] = useState<State>({ summaries: null, details: [], error: null });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, error: null }));
    try {
      const summaries = await api.listCases();
      const recent = [...summaries].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, limit);
      const settled = await Promise.allSettled(recent.map((c) => api.getCase(c.id)));
      const details = settled.flatMap((r) => (r.status === 'fulfilled' ? [r.value] : []));
      const failed = settled.length - details.length;
      setState({ summaries, details, error: failed ? `사건 ${failed}개의 상세 정보를 불러오지 못했습니다.` : null });
    } catch (e) {
      setState({ summaries: [], details: [], error: errMessage(e) });
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, loading: state.summaries === null, reload: load, setDetails: (details: CaseDetail[]) => setState((s) => ({ ...s, details })) };
}
