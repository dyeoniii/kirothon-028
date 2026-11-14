import { Archive, Bell, FolderOpen, Info, LayoutDashboard, ScanSearch, Search, ShieldCheck } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useServerStatus, type ServerState } from '../lib/health';

const GROUPS = [
  { title: '개요', items: [{ to: '/', label: '대시보드', short: '홈', icon: LayoutDashboard, end: true }] },
  {
    title: '사건 관리',
    items: [
      { to: '/analyze', label: '새 악플 판독', short: '판독', icon: ScanSearch, end: false },
      { to: '/cases', label: '내 사건 관리', short: '사건', icon: FolderOpen, end: false },
    ],
  },
  { title: '증거 · 문서', items: [{ to: '/evidence', label: '내 증거함', short: '증거함', icon: Archive, end: false }] },
];
const ALL = GROUPS.flatMap((g) => g.items);

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-base font-extrabold text-ink-900">
      <ShieldCheck className="h-6 w-6 text-brand-600" aria-hidden />
      악플가드
    </Link>
  );
}

const STATUS_TEXT: Record<ServerState, { label: string; dot: string; badge: string }> = {
  mock: { label: '목 모드', dot: 'mock', badge: 'badge-context' },
  checking: { label: '서버 확인 중', dot: 'checking', badge: 'badge-neutral' },
  ok: { label: '서버 연결됨', dot: 'ok', badge: 'badge-low' },
  down: { label: '서버 연결 안 됨', dot: 'down', badge: 'badge-legal' },
};

function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, close]);
  return ref;
}

function Toolbar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const server = useServerStatus();
  const [q, setQ] = useState(params.get('q') ?? '');
  const [menu, setMenu] = useState<'bell' | 'user' | null>(null);
  const ref = useDismiss(menu !== null, () => setMenu(null));
  const status = STATUS_TEXT[server];

  useEffect(() => {
    setQ(params.get('q') ?? '');
  }, [params, pathname]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const base = pathname.startsWith('/evidence') ? '/evidence' : '/cases';
    navigate(q.trim() ? `${base}?q=${encodeURIComponent(q.trim())}` : base);
  }

  return (
    <div className="toolbar">
      <form role="search" onSubmit={submit} className="search">
        <Search className="h-4 w-4" aria-hidden />
        <input className="field" value={q} onChange={(e) => setQ(e.target.value)} placeholder="사건·댓글·증거 검색" aria-label="사건, 댓글, 증거 검색" />
      </form>
      <div className="ml-auto flex items-center gap-1.5 sm:gap-3">
        <span className={`badge ${status.badge} hidden items-center gap-1.5 sm:inline-flex`} title={server === 'mock' ? '실제 서버·AI 분석이 아닌 목 데이터입니다' : '/api/health 확인 결과'}>
          <span className="status-dot" data-state={status.dot} aria-hidden />
          {status.label}
        </span>
        <span className="hidden text-xs font-semibold text-ink-600 xl:inline">⚖️ AI 분석은 법률 자문이 아닙니다</span>
        <div ref={ref} className="relative flex items-center gap-1">
          <button type="button" className="icon-btn" aria-label="알림" aria-expanded={menu === 'bell'} onClick={() => setMenu(menu === 'bell' ? null : 'bell')}>
            <Bell className="h-5 w-5" aria-hidden />
          </button>
          <button type="button" className="icon-btn !w-auto px-1" aria-label="사용자 메뉴" aria-expanded={menu === 'user'} onClick={() => setMenu(menu === 'user' ? null : 'user')}>
            <span className="avatar">나</span>
          </button>
          {menu && (
            <div className="popover" role="dialog" aria-label={menu === 'bell' ? '알림' : '사용자 메뉴'}>
              {menu === 'bell' ? (
                <>
                  <p className="font-bold">알림</p>
                  <p className="mt-1 text-ink-600">새 알림이 없어요. 알림 기능은 아직 서버와 연결되지 않았습니다.</p>
                </>
              ) : (
                <>
                  <p className="font-bold">내 작업공간</p>
                  <p className="mt-1 text-ink-600">로그인 없이 쓰는 로컬 시연 환경이에요. 사건은 이 환경에만 저장됩니다.</p>
                  <p className="mt-2 text-xs text-ink-600">연결 상태: {status.label}</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      {/* 데스크톱: 좌측 고정 사이드바 (브랜드 / 그룹 메뉴 / 이용 안내) */}
      <aside className="fixed inset-y-0 left-0 hidden w-[248px] flex-col border-r border-ink-200 bg-white px-4 py-5 lg:flex">
        <div className="px-2 pb-4 pt-1">
          <Logo />
        </div>
        <nav aria-label="주 메뉴" className="space-y-4">
          {GROUPS.map((g) => (
            <div key={g.title} className="space-y-1">
              <p className="px-3.5 pb-0.5 text-xs font-bold tracking-wide text-ink-600">{g.title}</p>
              {g.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} className="nav-item">
                  <Icon className="h-5 w-5" aria-hidden />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="mt-auto flex gap-2.5 rounded-xl bg-brand-50 p-3.5">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden />
          <div>
            <p className="text-sm font-bold text-ink-900">이용 안내</p>
            <p className="mt-0.5 text-xs leading-relaxed text-ink-700">AI 분석 결과는 참고용이며 법률 자문이 아닙니다. 최종 판단은 전문가와 상의하세요.</p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-[248px]">
        {/* 모바일·태블릿 상단 헤더 */}
        <header className="flex items-center justify-between border-b border-ink-200 bg-white px-4 py-3 lg:hidden">
          <Logo />
        </header>
        <Toolbar />
        <main className="mx-auto max-w-[1180px] px-4 py-5 pb-28 lg:px-8 lg:py-7 lg:pb-10">
          <div className="space-y-5">{children}</div>
        </main>
      </div>

      {/* 모바일·태블릿 하단 내비게이션 */}
      <nav aria-label="하단 메뉴" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-ink-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        {ALL.map(({ to, short, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="nav-bottom">
            <span className="nav-bottom-icon">
              <Icon className="h-5 w-5" aria-hidden />
            </span>
            {short}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
