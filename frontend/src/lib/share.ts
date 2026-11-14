const URL_RE = /https?:\/\/[^\s<>"']+/i;

function toHttpUrl(value: string | null): string | null {
  if (!value) return null;
  const m = URL_RE.exec(value.trim());
  if (!m) return null;
  // 문장 끝 구두점 제거
  const candidate = m[0].replace(/[),.;!?]+$/, '');
  try {
    const u = new URL(candidate);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.toString() : null;
  } catch {
    return null;
  }
}

/** Web Share Target 쿼리(url → text → title 순)에서 http(s) URL만 안전하게 추출 */
export function extractSharedUrl(search: string): string | null {
  const p = new URLSearchParams(search);
  for (const k of ['url', 'text', 'title']) {
    const found = toHttpUrl(p.get(k));
    if (found) return found;
  }
  return null;
}

export function isHttpUrl(value: string): boolean {
  return toHttpUrl(value) !== null && /^https?:\/\/\S+$/i.test(value.trim());
}
