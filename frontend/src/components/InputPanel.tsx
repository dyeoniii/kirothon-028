import { ImagePlus, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { errMessage } from '../lib/format';
import { isHttpUrl } from '../lib/share';
import type { InputResponse } from '../types';
import { Button, Card, ErrorBox, InfoBox, TabBar, inputCls, type TabItem } from './common';

type Mode = 'url' | 'text' | 'image';
const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = /\.(png|jpe?g|webp)$/i;

interface Props {
  caseId: string;
  initialUrl?: string;
  onDone: (res: InputResponse) => void;
}

export default function InputPanel({ caseId, initialUrl = '', onDone }: Props) {
  const [mode, setMode] = useState<Mode>(initialUrl ? 'url' : 'text');
  const [url, setUrl] = useState(initialUrl);
  const [text, setText] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [context, setContext] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const u = URL.createObjectURL(file);
    setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);

  useEffect(() => {
    if (initialUrl) {
      setUrl(initialUrl);
      setMode('url');
    }
  }, [initialUrl]);

  async function run(fn: () => Promise<InputResponse>, reset: () => void) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await fn();
      if (res.source.needs_manual_input) {
        setNotice(res.source.message ?? '자동 수집이 되지 않았습니다. 텍스트나 스크린샷으로 직접 입력해 주세요.');
      } else {
        const base = `댓글 ${res.comments.length.toLocaleString()}개를 가져왔습니다. AI 자동 판독을 시작합니다.`;
        setNotice(res.notice ? `${res.notice}. ${base}` : base);
      }
      reset();
      onDone(res);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function submitUrl() {
    const v = url.trim();
    if (!isHttpUrl(v)) return setError('http:// 또는 https:// 로 시작하는 올바른 주소를 입력해 주세요.');
    void run(() => api.inputUrl(caseId, v), () => setUrl(''));
  }

  function submitText() {
    if (!text.trim()) return setError('댓글 내용을 붙여넣어 주세요.');
    const su = sourceUrl.trim();
    if (su && !isHttpUrl(su)) return setError('원본 게시글 주소 형식이 올바르지 않습니다.');
    void run(
      () => api.inputText(caseId, { text, source_url: su || null, context: context.trim() || null }),
      () => {
        setText('');
        setContext('');
      },
    );
  }

  function pickFile(f: File | null) {
    setError(null);
    if (!f) return setFile(null);
    if (!ALLOWED.test(f.name)) return setError('png, jpg, jpeg, webp 파일만 올릴 수 있습니다.');
    if (f.size > MAX_BYTES) return setError('파일 크기는 10MB 이하여야 합니다.');
    setNotice(null);
    setFile(f);
  }

  function submitImage() {
    if (!file) return setError('이미지를 선택해 주세요.');
    const su = sourceUrl.trim();
    if (su && !isHttpUrl(su)) return setError('원본 게시글 주소 형식이 올바르지 않습니다.');
    void run(
      () => api.inputImage(caseId, file, su || null, context.trim() || null),
      () => {
        setFile(null);
        if (fileRef.current) fileRef.current.value = '';
      },
    );
  }

  const tabs: TabItem<Mode>[] = [
    { key: 'text', label: '텍스트' },
    { key: 'image', label: '스크린샷' },
    { key: 'url', label: 'SNS URL' },
  ];

  return (
    <Card className="space-y-3">
      <TabBar label="입력 방식" inset items={tabs} value={mode} onChange={(m) => { setMode(m); setError(null); }} />

      {mode === 'url' && (
        <div className="space-y-3 rounded-2xl border border-brand-200 bg-brand-50 p-4">
          <label className="field-label">
            게시물 주소
            <input
              className={`${inputCls} mt-1.5`}
              inputMode="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </label>
          <InfoBox>
            YouTube 주소는 공개 댓글을 최근 것부터 서버 설정 한도까지 가져옵니다(한도보다 많으면 안내가 표시됩니다). 그 밖의 SNS는 주소만 출처로 저장하고 댓글은 직접 입력해야 합니다.
          </InfoBox>
          <Button className="w-full" busy={busy} busyLabel="댓글 가져오는 중…" onClick={submitUrl}>
            댓글 가져오기
          </Button>
        </div>
      )}

      {mode === 'text' && (
        <div className="space-y-3">
          <label className="field-label">
            댓글 내용 (한 줄에 하나)
            <textarea className={`${inputCls} mt-1.5 min-h-[7rem]`} value={text} onChange={(e) => setText(e.target.value)} placeholder="댓글을 붙여넣어 주세요" />
          </label>
          <SourceFields sourceUrl={sourceUrl} setSourceUrl={setSourceUrl} context={context} setContext={setContext} />
          <Button className="w-full" busy={busy} busyLabel="추가하는 중…" onClick={submitText}>
            댓글 추가
          </Button>
        </div>
      )}

      {mode === 'image' && (
        <div className="space-y-3">
          <div>
            <p className="field-label">댓글 스크린샷</p>
            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pickFile(e.dataTransfer.files?.[0] ?? null);
              }}
              className={`mt-1 flex cursor-pointer flex-col items-center gap-1 rounded-2xl border-2 border-dashed px-4 py-8 text-center text-sm text-ink-700 transition-colors ${
                dragging ? 'border-brand-600 bg-brand-100' : 'border-brand-300 bg-brand-50 hover:border-brand-500'
              }`}
            >
              <ImagePlus className="h-6 w-6 text-brand-600" aria-hidden />
              <span className="font-bold text-brand-800">{file ? '다른 이미지 선택' : '이미지를 끌어다 놓거나 눌러서 선택'}</span>
              <span className="text-xs text-ink-600">png, jpg, jpeg, webp · 10MB 이하</span>
              <input
                ref={fileRef}
                type="file"
                accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                className="sr-only"
                onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          {file && preview && (
            <div className="flex items-start gap-3 rounded-2xl border border-ink-200 p-2">
              <img src={preview} alt="선택한 스크린샷 미리보기" className="h-24 w-24 shrink-0 rounded-xl bg-ink-50 object-contain" />
              <div className="min-w-0 flex-1 text-xs text-ink-600">
                <p className="break-all font-medium text-ink-900">{file.name}</p>
                <p>{(file.size / 1024).toFixed(0)}KB</p>
              </div>
              <button
                type="button"
                aria-label="선택한 이미지 지우기"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-ink-600 hover:bg-ink-100"
                onClick={() => {
                  setFile(null);
                  if (fileRef.current) fileRef.current.value = '';
                }}
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )}
          <SourceFields sourceUrl={sourceUrl} setSourceUrl={setSourceUrl} context={context} setContext={setContext} />
          <InfoBox tone="warn">
            AI가 읽은 작성자·시각은 틀릴 수 있습니다. 읽지 못한 값은 비워 두며, 저장 전에 원본과 비교해 확인해 주세요. 원본 이미지는 서버로 전송됩니다.
          </InfoBox>
          <Button className="w-full" busy={busy} busyLabel="댓글 추출 중…" disabled={!file} onClick={submitImage}>
            댓글 추출
          </Button>
        </div>
      )}

      <ErrorBox message={error} onClose={() => setError(null)} />
      {notice && !error && <InfoBox>{notice}</InfoBox>}
    </Card>
  );
}

function SourceFields(p: { sourceUrl: string; setSourceUrl: (v: string) => void; context: string; setContext: (v: string) => void }) {
  return (
    <>
      <label className="field-label">
        원본 게시글 주소 (선택)
        <input className={`${inputCls} mt-1.5`} inputMode="url" value={p.sourceUrl} onChange={(e) => p.setSourceUrl(e.target.value)} placeholder="https://" />
      </label>
      <label className="field-label">
        원본 게시글 맥락 (선택)
        <textarea className={`${inputCls} mt-1.5 min-h-[4.5rem]`} value={p.context} onChange={(e) => p.setContext(e.target.value)} placeholder="어떤 게시물에 달린 댓글인지 적어 주세요" />
      </label>
    </>
  );
}
