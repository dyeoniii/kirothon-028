import { CircleAlert, CircleCheck, Info, LoaderCircle, TriangleAlert, X } from 'lucide-react';
import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { DISCLAIMER, LEVEL_LABEL, type RiskLevel } from '../types';

/* 공통 UI 컴포넌트. 색·크기·상태 스타일은 src/index.css 의 디자인 토큰과 .btn/.card/.field 등 공통 클래스가 정의합니다. */

const LEVEL_CLASS: Record<RiskLevel, string> = {
  legal_review: 'badge badge-legal',
  needs_context: 'badge badge-context',
  low_risk: 'badge badge-low',
};

export function LevelBadge({ level, label }: { level: RiskLevel; label?: string }) {
  return <span className={LEVEL_CLASS[level]}>{label || LEVEL_LABEL[level]}</span>;
}

export function Badge({ tone = 'brand', children }: { tone?: 'brand' | 'neutral'; children: ReactNode }) {
  return <span className={`badge ${tone === 'brand' ? 'badge-brand' : 'badge-neutral'}`}>{children}</span>;
}

export function Disclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-xs leading-relaxed text-ink-600 ${className}`}>
      ⚖️ {DISCLAIMER} 고소 가능 여부나 결과를 보장하지 않습니다.
    </p>
  );
}

type Tone = 'error' | 'warn' | 'info' | 'success';
const ALERT_ICON = { error: CircleAlert, warn: TriangleAlert, info: Info, success: CircleCheck } as const;

export function Alert({ tone, children, role }: { tone: Tone; children: ReactNode; role?: string }) {
  const Icon = ALERT_ICON[tone];
  return (
    <div role={role} className={`alert alert-${tone}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function ErrorBox({ message, onClose, onRetry }: { message: string | null; onClose?: () => void; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" className="alert alert-error">
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1">{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="shrink-0 font-semibold underline">
          다시 시도
        </button>
      )}
      {onClose && (
        <button type="button" onClick={onClose} aria-label="닫기" className="shrink-0">
          <X className="h-4 w-4" aria-hidden />
        </button>
      )}
    </div>
  );
}

export function InfoBox({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warn' | 'success' }) {
  return <Alert tone={tone}>{children}</Alert>;
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger';
  size?: 'md' | 'sm';
  busy?: boolean;
  busyLabel?: string;
};

export function Button({ variant = 'primary', size = 'md', busy, busyLabel = '처리 중…', className = '', children, disabled, ...rest }: BtnProps) {
  const v = { primary: 'btn-primary', ghost: 'btn-secondary', danger: 'btn-danger' }[variant];
  return (
    <button type="button" className={`btn ${v} ${size === 'sm' ? 'btn-sm' : ''} ${className}`} disabled={disabled || busy} aria-busy={busy || undefined} {...rest}>
      {busy && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />}
      {busy ? busyLabel : children}
    </button>
  );
}

export function Card({ children, className = '', compact }: { children: ReactNode; className?: string; compact?: boolean }) {
  return <section className={`card ${compact ? 'card-compact' : ''} ${className}`}>{children}</section>;
}

export const inputCls = 'field';

export function PageHeader({ title, desc, action }: { title: string; desc?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-extrabold text-ink-900">{title}</h1>
        {desc && <p className="mt-1 text-sm text-ink-600">{desc}</p>}
      </div>
      {action}
    </div>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <h2 className="text-base font-bold text-ink-900">{children}</h2>
      {action}
    </div>
  );
}

export function EmptyState({ icon, title, desc, action }: { icon?: ReactNode; title: string; desc?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card border border-dashed border-brand-300 bg-white px-4 py-8 text-center">
      {icon && <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-100 text-brand-700">{icon}</div>}
      <p className="font-semibold text-ink-900">{title}</p>
      {desc && <p className="max-w-sm text-sm text-ink-600">{desc}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-card bg-white/80 ${className}`} />;
}

export function LoadingBlock({ label = '불러오는 중…' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}</span>
      <Skeleton className="h-16" />
      <Skeleton className="h-16" />
    </div>
  );
}

export interface TabItem<K extends string> {
  key: K;
  label: string;
  count?: number;
}

/** 탭/세그먼트. 선택 상태는 aria-selected 로 표현하고 스타일은 .tab 이 정의합니다. */
export function TabBar<K extends string>({ items, value, onChange, label, inset }: { items: TabItem<K>[]; value: K; onChange: (k: K) => void; label: string; inset?: boolean }) {
  return (
    <div role="tablist" aria-label={label} className={`tabs ${inset ? 'tabs-inset' : ''}`} style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
      {items.map((t) => (
        <button key={t.key} role="tab" type="button" aria-selected={value === t.key} onClick={() => onChange(t.key)} className="tab">
          {t.label}
          {t.count !== undefined && t.count > 0 && <span className="tab-count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

interface ConfirmProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** 삭제 같은 되돌릴 수 없는 작업 전 확인 모달 */
export function ConfirmModal({ open, title, message, confirmLabel = '삭제', busy, onConfirm, onCancel }: ConfirmProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onCancel();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/40 p-4 sm:items-center" onClick={() => !busy && onCancel()}>
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-sm space-y-3 rounded-card bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-title" className="text-lg font-bold text-ink-900">
          {title}
        </h2>
        <div className="text-sm leading-relaxed text-ink-700">{message}</div>
        <div className="flex gap-2 pt-1">
          <button ref={cancelRef} type="button" disabled={busy} onClick={onCancel} className="btn btn-secondary flex-1">
            취소
          </button>
          <button type="button" disabled={busy} onClick={onConfirm} className="btn btn-danger-solid flex-1">
            {busy && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />}
            {busy ? '삭제 중…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/** 표·목록용 패널. 제목 줄(panel-head)과 본문을 한 덩어리로 보여 줍니다. */
export function Panel({ title, action, children, flush }: { title?: ReactNode; action?: ReactNode; children: ReactNode; flush?: boolean }) {
  return (
    <section className="panel">
      {(title || action) && (
        <div className="panel-head">
          <h2>{title}</h2>
          {action}
        </div>
      )}
      <div className={flush ? '' : 'panel-body'}>{children}</div>
    </section>
  );
}

export function KpiCard({ icon, label, value, note }: { icon: ReactNode; label: string; value: number | null; note: string }) {
  return (
    <Card compact>
      <div className="kpi-label">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-700">{icon}</span>
        {label}
      </div>
      {value === null ? <div className="mt-2 h-8 w-12 animate-pulse rounded-lg bg-ink-100" aria-label="불러오는 중" /> : <p className="kpi-value">{value}</p>}
      <p className="kpi-note">{note}</p>
    </Card>
  );
}

export function StatusBadge({ badge, label }: { badge: string; label: string }) {
  return <span className={`badge ${badge}`}>{label}</span>;
}
