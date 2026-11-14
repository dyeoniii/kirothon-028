const fmt = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

/** ISO UTC → KST 표시. 값이 없으면 '확인되지 않음' (추측하지 않음) */
export function formatKst(iso: string | null | undefined): string {
  if (!iso) return '확인되지 않음';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '확인되지 않음';
  return fmt.format(d) + ' (KST)';
}

export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function errMessage(e: unknown): string {
  return e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.';
}
