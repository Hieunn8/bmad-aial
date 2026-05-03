/**
 * ExportConfirmationBar — Story 4.5 (UX-DR15)
 *
 * AC: sticky bottom bar (NOT modal); Human-in-the-Loop Signature checkbox;
 * auto-dismisses after 30s with cancel default;
 * interface contract FROZEN before story begins (Epic 6 signed off).
 *
 * CONTRACT (frozen — Epic 6 consumes, no rebuild):
 *   { format, rowCount, sensitivityWarning?, onConfirm, onCancel }
 */
import { useEffect, useState } from 'react';

export interface ExportConfirmationBarProps {
  format: 'csv' | 'xlsx' | 'pdf';
  rowCount: number;
  sensitivityWarning?: string;
  onConfirm: () => void;
  onCancel: () => void;
  autoDismissSeconds?: number;
}

export function ExportConfirmationBar({
  format,
  rowCount,
  sensitivityWarning,
  onConfirm,
  onCancel,
  autoDismissSeconds,
}: ExportConfirmationBarProps): React.JSX.Element {
  const [checked, setChecked] = useState(false);
  const dismissSeconds = autoDismissSeconds ?? 30;
  const [remaining, setRemaining] = useState(dismissSeconds);

  useEffect(() => {
    if (remaining <= 0) { onCancel(); return; }
    const t = setTimeout(() => setRemaining((remainingSeconds: number) => remainingSeconds - 1), 1_000);
    return () => clearTimeout(t);
  }, [remaining, onCancel]);

  return (
    <div
      role="region"
      aria-label="Xác nhận xuất dữ liệu"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: 'var(--color-surface, white)',
        borderTop: '2px solid var(--color-primary, #2563eb)',
        padding: 'var(--space-4, 16px)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-4)',
        flexWrap: 'wrap',
        zIndex: 50,
        boxShadow: '0 -4px 12px rgba(0,0,0,0.1)',
      }}
    >
      <div style={{ flex: 1, minWidth: '200px' }}>
        <strong>Xuất {rowCount.toLocaleString()} dòng dưới dạng {format.toUpperCase()}</strong>
        {sensitivityWarning && (
          <p style={{ color: 'var(--color-warning, #d97706)', fontSize: 'var(--font-size-sm)', margin: '4px 0 0' }}>
            ⚠️ {sensitivityWarning}
          </p>
        )}
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={e => setChecked(e.target.checked)}
          aria-label="Xác nhận đã xem xét dữ liệu"
        />
        Tôi đã xem xét và xác nhận dữ liệu này
      </label>

      <button
        type="button"
        onClick={onConfirm}
        disabled={!checked}
        style={{
          padding: 'var(--space-2) var(--space-4)',
          backgroundColor: checked ? 'var(--color-primary, #2563eb)' : 'var(--color-neutral-300)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          cursor: checked ? 'pointer' : 'not-allowed',
          fontFamily: 'var(--font-family-base)',
        }}
      >
        Xác nhận xuất
      </button>

      <button
        type="button"
        onClick={onCancel}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-neutral-500)', fontSize: 'var(--font-size-sm)' }}
      >
        Hủy ({remaining}s)
      </button>
    </div>
  );
}
