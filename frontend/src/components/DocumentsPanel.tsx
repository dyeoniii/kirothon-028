import { Download, FileText } from 'lucide-react';
import { useState } from 'react';
import { api } from '../api';
import { errMessage, triggerDownload } from '../lib/format';
import { useMaskAuthors } from '../lib/maskAuthors';
import type { DocumentKind } from '../types';
import { Badge, Button, Disclaimer, ErrorBox, InfoBox, Panel } from './common';

const DOCS: { kind: DocumentKind; title: string; desc: string }[] = [
  { kind: 'statement', title: '사건 경위서', desc: '사건 정보와 저장된 증거를 정리합니다. 확인된 사실과 AI 분석 추정이 구분됩니다.' },
  { kind: 'evidence-list', title: '증거자료 목록', desc: '증거 번호, 댓글, 작성자, 시각, URL, 수집 시각, SHA-256을 표로 정리합니다.' },
];

/** 문서 센터: 사건에서 만들 수 있는 PDF 2종을 목록으로 보여 주고 다운로드합니다. */
export default function DocumentsPanel({ caseId, savedCount }: { caseId: string; savedCount: number }) {
  const { mask } = useMaskAuthors();
  const [busy, setBusy] = useState<DocumentKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function download(kind: DocumentKind) {
    setBusy(kind);
    setError(null);
    setDone(null);
    try {
      const { blob, filename } = await api.downloadDocument(caseId, kind, mask);
      triggerDownload(blob, filename);
      setDone(`${filename} 파일을 내려받았습니다.`);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      {savedCount === 0 && <InfoBox tone="warn">저장된 증거가 없습니다. 판독 탭에서 댓글을 증거함에 저장한 뒤 문서를 만들 수 있습니다.</InfoBox>}
      <ErrorBox message={error} onClose={() => setError(null)} />
      <InfoBox>
        {mask
          ? '작성자 가리기가 켜져 있어 PDF의 작성자도 가려서(앞 1글자 + **) 출력됩니다. 원본 작성자로 출력하려면 상단의 “작성자 가리기”를 꺼 주세요.'
          : 'PDF에는 원본 작성자가 그대로 들어갑니다. 공유용이라면 상단의 “작성자 가리기”를 켠 뒤 내려받으세요.'}
      </InfoBox>
      {done && <InfoBox>{done}</InfoBox>}
      <Panel title="문서 센터" flush>
        {DOCS.map((d) => (
          <div key={d.kind} className="list-row !items-start flex-wrap sm:flex-nowrap">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
              <FileText className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2 font-semibold">
                {d.title}
                <Badge tone="neutral">PDF</Badge>
                {savedCount > 0 ? <span className="badge badge-low">작성 가능</span> : <span className="badge badge-context">증거 필요</span>}
              </p>
              <p className="mt-0.5 text-sm text-ink-600">{d.desc}</p>
            </div>
            <Button className="w-full sm:w-auto" busy={busy === d.kind} busyLabel="PDF 만드는 중…" disabled={busy !== null || savedCount === 0} onClick={() => void download(d.kind)}>
              <Download className="h-4 w-4" aria-hidden />
              PDF 다운로드
            </Button>
          </div>
        ))}
      </Panel>
      <Disclaimer />
    </div>
  );
}
