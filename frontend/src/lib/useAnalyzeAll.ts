import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { AnalyzeAllStatus } from '../types';
import { errMessage } from './format';

const POLL_MS = 1500;
/** 진행 중 몇 번 폴링할 때마다 사건 데이터를 다시 읽어 중간 결과를 보여줄지 */
const REFRESH_EVERY = 4;

/**
 * 서버의 전체 자동 판독(analyze-all)을 시작하고 진행 상황을 폴링합니다.
 * 끝나면 `onRefresh`로 사건 상세를 다시 읽어 판독 결과를 반영합니다.
 */
export function useAnalyzeAll(caseId: string, onRefresh: () => Promise<void> | void) {
  const [status, setStatus] = useState<AnalyzeAllStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const refreshRef = useRef(onRefresh);
  refreshRef.current = onRefresh;

  // 화면에 들어왔을 때 이미 진행 중인 판독이 있으면 이어서 보여준다.
  useEffect(() => {
    let alive = true;
    setStatus(null);
    api
      .analyzeAllStatus(caseId)
      .then((s) => {
        if (!alive) return;
        setStatus(s);
        if (s.running) setPolling(true);
      })
      .catch(() => {
        /* 상태를 못 읽어도 화면 사용에는 지장 없음 */
      });
    return () => {
      alive = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!polling) return;
    let alive = true;
    let ticks = 0;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const s = await api.analyzeAllStatus(caseId);
        if (!alive) return;
        setStatus(s);
        ticks += 1;
        if (!s.running) {
          setPolling(false);
          await refreshRef.current();
          return;
        }
        if (ticks % REFRESH_EVERY === 0) await refreshRef.current();
      } catch (e) {
        if (!alive) return;
        setError(errMessage(e));
        setPolling(false);
        return;
      }
      if (alive) timer = setTimeout(() => void tick(), POLL_MS);
    };
    timer = setTimeout(() => void tick(), POLL_MS);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [polling, caseId]);

  const start = useCallback(async (force = false) => {
    setError(null);
    try {
      const s = await api.analyzeAll(caseId, force);
      setStatus(s);
      if (s.running) setPolling(true);
      else await refreshRef.current();
    } catch (e) {
      setError(errMessage(e));
    }
  }, [caseId]);

  const stop = useCallback(async () => {
    setError(null);
    try {
      setStatus(await api.analyzeAllStop(caseId)); // 폴링은 계속되어 끝나면 결과를 반영한다
    } catch (e) {
      setError(errMessage(e));
    }
  }, [caseId]);

  return { status, error, stop, clearError: () => setError(null), start, running: polling || status?.running === true };
}
