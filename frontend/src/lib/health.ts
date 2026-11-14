import { useEffect, useState } from 'react';
import { USE_MOCK } from '../api';

export type ServerState = 'mock' | 'checking' | 'ok' | 'down';

/** GET /api/health(API 계약 공통 항목)로 실서버 연결을 확인합니다. 목 모드에서는 요청하지 않습니다. */
export function useServerStatus(): ServerState {
  const [state, setState] = useState<ServerState>(USE_MOCK ? 'mock' : 'checking');

  useEffect(() => {
    if (USE_MOCK) return;
    let alive = true;
    const check = async () => {
      try {
        const res = await fetch('/api/health');
        const isJson = (res.headers.get('Content-Type') ?? '').toLowerCase().includes('json');
        const body = res.ok && isJson ? ((await res.json()) as { status?: string }) : null;
        if (alive) setState(body?.status === 'ok' ? 'ok' : 'down');
      } catch {
        if (alive) setState('down');
      }
    };
    void check();
    const t = setInterval(check, 30000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return state;
}
