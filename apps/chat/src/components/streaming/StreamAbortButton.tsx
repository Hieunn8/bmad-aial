/**
 * StreamAbortButton — always visible during streaming (Story 2A.5, UX-DR25).
 *
 * AC: button visible at ALL times during streaming — never hidden in a menu.
 * Escape key also triggers abort.
 */
import { useEffect } from 'react';

export interface StreamAbortButtonProps {
  onAbort: () => void;
  isStreaming: boolean;
}

export function StreamAbortButton({ onAbort, isStreaming }: StreamAbortButtonProps): React.JSX.Element {
  useEffect(() => {
    if (!isStreaming) return;
    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onAbort();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isStreaming, onAbort]);

  if (!isStreaming) return <></>;

  return (
    <button
      type="button"
      onClick={onAbort}
      aria-label="Hủy truy vấn (Escape)"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-1, 4px)',
        padding: 'var(--space-2, 8px) var(--space-3, 12px)',
        backgroundColor: 'transparent',
        border: '1px solid var(--color-border, #e5e7eb)',
        borderRadius: 'var(--radius-md, 6px)',
        cursor: 'pointer',
        fontSize: 'var(--font-size-sm, 0.875rem)',
        color: 'var(--color-neutral-600, #6b7280)',
      }}
    >
      <span aria-hidden="true">✕</span>
      <span>Đã hủy</span>
    </button>
  );
}
