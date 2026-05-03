/**
 * ThinkingPulse — Progressive thinking state indicator (Story 2A.5)
 *
 * Phase 1 (0–300ms): opacity 0.4→1.0, 600ms, cubic-bezier(0.4,0,0.2,1), loop
 * Phase 2 (300ms–2s): scale 1.0→1.05→1.0, 800ms, ease-in-out, loop
 * prefers-reduced-motion: static indicator, no animation
 */
import { useRef } from 'react';

export interface ThinkingPulseProps {
  message?: string;
  phase?: 1 | 2;
}

const PHASE_1_STYLE: React.CSSProperties = {
  animation: 'aial-pulse-opacity 600ms cubic-bezier(0.4, 0, 0.2, 1) infinite',
};
const PHASE_2_STYLE: React.CSSProperties = {
  animation: 'aial-pulse-scale 800ms ease-in-out infinite',
};
const REDUCED_MOTION_STYLE: React.CSSProperties = {};

const CSS_KEYFRAMES = `
@keyframes aial-pulse-opacity {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1.0; }
}
@keyframes aial-pulse-scale {
  0%, 100% { transform: scale(1.0); }
  50% { transform: scale(1.05); }
}
@media (prefers-reduced-motion: reduce) {
  .aial-thinking-pulse { animation: none !important; }
}
`;

export function ThinkingPulse({ message = 'Đang phân tích...', phase = 1 }: ThinkingPulseProps): React.JSX.Element {
  const prefersReduced = useRef(
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  ).current;

  const animStyle = prefersReduced ? REDUCED_MOTION_STYLE : phase === 1 ? PHASE_1_STYLE : PHASE_2_STYLE;
  const displayMessage = prefersReduced ? 'đang xử lý...' : message;

  return (
    <>
      <style>{CSS_KEYFRAMES}</style>
      <div
        role="status"
        aria-live="polite"
        aria-label="AI đang xử lý"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2, 8px)',
          color: 'var(--color-neutral-600, #6b7280)',
          fontSize: 'var(--font-size-sm, 0.875rem)',
        }}
      >
        <span
          className="aial-thinking-pulse"
          aria-hidden="true"
          style={{
            display: 'inline-block',
            width: '0.75rem',
            height: '0.75rem',
            borderRadius: '50%',
            backgroundColor: 'var(--color-primary, #2563eb)',
            ...animStyle,
          }}
        />
        <span>{displayMessage}</span>
      </div>
    </>
  );
}
