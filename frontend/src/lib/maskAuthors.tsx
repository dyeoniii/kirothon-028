import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

const KEY = 'akpleguard.maskAuthors';

/**
 * 작성자 가리기(데모용): 앞 1글자 + '**'. 앞의 '@'는 유지합니다(예: '@정수진' → '@정**').
 * 화면 표시만 바꾸며 서버의 원본 값은 그대로입니다. 백엔드 PDF 가리기 규칙(common.mask_author)과 같습니다.
 */
export function maskAuthor(name: string | null | undefined): string | null {
  if (name == null) return null;
  const text = name.trim();
  if (!text) return name;
  const prefix = text.startsWith('@') ? '@' : '';
  const rest = Array.from(text.slice(prefix.length));
  return rest.length ? `${prefix}${rest[0]}**` : name;
}

interface MaskState {
  mask: boolean;
  setMask: (v: boolean) => void;
}

const MaskContext = createContext<MaskState>({ mask: false, setMask: () => {} });

export function MaskAuthorsProvider({ children }: { children: ReactNode }) {
  const [mask, setMaskState] = useState<boolean>(() => {
    try {
      return localStorage.getItem(KEY) === '1';
    } catch {
      return false;
    }
  });
  const setMask = useCallback((v: boolean) => {
    setMaskState(v);
    try {
      localStorage.setItem(KEY, v ? '1' : '0');
    } catch {
      /* 저장 실패는 무시: 이번 화면에서만 적용 */
    }
  }, []);
  const value = useMemo(() => ({ mask, setMask }), [mask, setMask]);
  return <MaskContext.Provider value={value}>{children}</MaskContext.Provider>;
}

export const useMaskAuthors = () => useContext(MaskContext);
