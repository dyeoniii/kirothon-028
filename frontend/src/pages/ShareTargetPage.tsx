import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Button, Card, ErrorBox, InfoBox, inputCls } from '../components/common';
import { errMessage } from '../lib/format';
import { extractSharedUrl } from '../lib/share';
import type { CaseSummary } from '../types';

/** PWA 공유 수신 라우트. URL만 프리필하고, 수집은 사용자가 직접 누릅니다. */
export default function ShareTargetPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const shared = extractSharedUrl(location.search);
  const [url, setUrl] = useState(shared ?? '');
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listCases().then(setCases).catch((e) => {
      setError(errMessage(e));
      setCases([]);
    });
  }, []);

  const go = (caseId: string) => navigate(`/cases/${caseId}`, { state: { sharedUrl: url.trim() } });

  async function createAndGo() {
    setBusy(true);
    setError(null);
    try {
      const c = await api.createCase({ title: '공유받은 게시물', description: '' });
      go(c.id);
    } catch (e) {
      setError(errMessage(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">공유받은 주소</h2>
      {shared ? (
        <InfoBox>다른 앱에서 공유한 주소입니다. 확인 후 저장할 사건을 선택해 주세요. 선택해도 자동으로 수집하지 않습니다.</InfoBox>
      ) : (
        <InfoBox tone="warn">공유 내용에서 웹 주소를 찾지 못했습니다. 아래에 주소를 직접 붙여넣어 주세요.</InfoBox>
      )}
      <Card className="space-y-2">
        <label className="block text-sm font-medium">
          주소
          <input className={`${inputCls} mt-1`} inputMode="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" />
        </label>
      </Card>

      <ErrorBox message={error} onClose={() => setError(null)} />

      <Card className="space-y-2">
        <h3 className="font-semibold">사건 선택</h3>
        <Button className="w-full" busy={busy} disabled={!url.trim()} onClick={() => void createAndGo()}>
          새 사건으로 시작
        </Button>
        {cases?.map((c) => (
          <Button key={c.id} variant="ghost" className="w-full justify-start" disabled={!url.trim()} onClick={() => go(c.id)}>
            {c.title}
          </Button>
        ))}
      </Card>
      <Link to="/" className="block text-sm font-semibold text-brand-700">
        ← 사건 목록
      </Link>
    </div>
  );
}
