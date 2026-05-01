/**
 * ChartReveal + DataFreshnessIndicator — Story 2B.4 (UX-DR9)
 *
 * ChartReveal AC: skeleton while streaming; fade-in 400ms cubic-bezier(0.4,0,0.2,1);
 * prefers-reduced-motion → instant; isAnimationActive=false on Recharts;
 * aspect ratio locked during skeleton.
 *
 * DataFreshnessIndicator AC: 🟢/🟡/🔴 color-coded AND text-labeled.
 */
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// useChartTheme — CSS-var-based colors for Recharts
// ---------------------------------------------------------------------------

export interface ChartTheme {
  primary: string;
  secondary: string;
  grid: string;
  text: string;
  colors: string[];
}

export function useChartTheme(): ChartTheme {
  return {
    primary: 'var(--color-primary, #2563eb)',
    secondary: 'var(--color-secondary, #7c3aed)',
    grid: 'var(--color-border, #e5e7eb)',
    text: 'var(--color-neutral-600, #4b5563)',
    colors: [
      'var(--color-primary, #2563eb)',
      'var(--color-success, #16a34a)',
      'var(--color-warning, #d97706)',
      'var(--color-error, #dc2626)',
    ],
  };
}

// ---------------------------------------------------------------------------
// ChartReveal
// ---------------------------------------------------------------------------

export interface ChartRevealProps {
  isStreaming: boolean;
  aspectRatio?: number;
  children: ReactNode;
}

const REDUCED_MOTION =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function ChartReveal({ isStreaming, aspectRatio = 16 / 9, children }: ChartRevealProps): React.JSX.Element {
  if (isStreaming) {
    return (
      <div
        role="img"
        aria-label="Đang tải biểu đồ..."
        aria-busy="true"
        style={{
          width: '100%',
          paddingBottom: `${(1 / aspectRatio) * 100}%`,
          position: 'relative',
          backgroundColor: 'var(--color-neutral-100, #f3f4f6)',
          borderRadius: 'var(--radius-md, 6px)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.6) 50%, transparent 100%)',
            animation: REDUCED_MOTION ? 'none' : 'aial-shimmer 1.5s infinite',
          }}
        />
        <style>{`@keyframes aial-shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(200%); } }`}</style>
      </div>
    );
  }

  return (
    <div
      style={{
        animation: REDUCED_MOTION ? 'none' : 'aial-chart-reveal 400ms cubic-bezier(0.4, 0, 0.2, 1) both',
      }}
    >
      <style>{`@keyframes aial-chart-reveal { from { opacity: 0; } to { opacity: 1; } }`}</style>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DataFreshnessIndicator
// ---------------------------------------------------------------------------

export type FreshnessLevel = 'fresh' | 'stale' | 'old';

export interface DataFreshnessIndicatorProps {
  updatedAt: Date | string;
  label?: string;
}

function computeFreshness(updatedAt: Date | string): FreshnessLevel {
  const dt = typeof updatedAt === 'string' ? new Date(updatedAt) : updatedAt;
  const ageMs = Date.now() - dt.getTime();
  const ageHours = ageMs / 3_600_000;
  if (ageHours < 12) return 'fresh';
  if (ageHours < 24) return 'stale';
  return 'old';
}

const FRESHNESS_CONFIG: Record<FreshnessLevel, { emoji: string; color: string; text: string }> = {
  fresh: { emoji: '🟢', color: 'var(--color-success, #16a34a)', text: 'Cập nhật hôm nay' },
  stale: { emoji: '🟡', color: 'var(--color-warning, #d97706)', text: 'Dữ liệu từ hôm qua' },
  old: { emoji: '🔴', color: 'var(--color-error, #dc2626)', text: 'Dữ liệu > 24 giờ' },
};

export function DataFreshnessIndicator({ updatedAt, label }: DataFreshnessIndicatorProps): React.JSX.Element {
  const level = computeFreshness(updatedAt);
  const cfg = FRESHNESS_CONFIG[level];
  const dt = typeof updatedAt === 'string' ? new Date(updatedAt) : updatedAt;
  const timeStr = dt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

  return (
    <span
      aria-label={`Độ tươi dữ liệu: ${cfg.text}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: 'var(--font-size-xs, 0.75rem)', color: cfg.color }}
    >
      <span aria-hidden="true">{cfg.emoji}</span>
      <span>{label ?? `${cfg.text} lúc ${timeStr}`}</span>
    </span>
  );
}
