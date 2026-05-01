/**
 * ProgressiveDataTable — rows batched every 150ms (Story 2A.5)
 *
 * AC: chunk renders with fade-in 60ms ease-out; column headers locked;
 * minimum visible chunk ≥15 tokens; isAnimationActive=false on Recharts.
 */
import { useEffect, useRef, useState } from 'react';

export interface DataRow {
  [key: string]: unknown;
}

export interface ProgressiveDataTableProps {
  rows: DataRow[];
  /** Batch interval ms (default 150) */
  batchIntervalMs?: number;
}

export function ProgressiveDataTable({ rows, batchIntervalMs = 150 }: ProgressiveDataTableProps): React.JSX.Element {
  const [visibleRows, setVisibleRows] = useState<DataRow[]>([]);
  const pendingRef = useRef<DataRow[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    pendingRef.current = [...rows];

    if (timerRef.current) clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      if (pendingRef.current.length === 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        return;
      }
      const chunk = pendingRef.current.splice(0, 50);
      setVisibleRows(prev => [...prev, ...chunk]);
    }, batchIntervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [rows, batchIntervalMs]);

  if (visibleRows.length === 0) return <></>;

  const columns = Object.keys(visibleRows[0] ?? {});

  return (
    <div role="region" aria-label="Kết quả truy vấn" style={{ overflowX: 'auto' }}>
      <table
        style={{
          borderCollapse: 'collapse',
          width: '100%',
          fontSize: 'var(--font-size-sm, 0.875rem)',
        }}
        aria-rowcount={rows.length}
      >
        {/* Column headers locked during streaming */}
        <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--color-surface, white)' }}>
          <tr>
            {columns.map(col => (
              <th
                key={col}
                scope="col"
                style={{
                  padding: 'var(--space-2, 8px) var(--space-3, 12px)',
                  textAlign: 'left',
                  borderBottom: '2px solid var(--color-border, #e5e7eb)',
                  fontWeight: 'var(--font-weight-semibold, 600)',
                  color: 'var(--color-neutral-700, #374151)',
                  whiteSpace: 'nowrap',
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, i) => (
            <tr
              key={i}
              style={{ animation: 'aial-row-fadein 60ms ease-out both' }}
            >
              {columns.map(col => (
                <td
                  key={col}
                  style={{
                    padding: 'var(--space-2, 8px) var(--space-3, 12px)',
                    borderBottom: '1px solid var(--color-border, #e5e7eb)',
                    color: 'var(--color-neutral-900, #111827)',
                  }}
                >
                  {String(row[col] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <style>{`@keyframes aial-row-fadein { from { opacity: 0; } to { opacity: 1; } }`}</style>
    </div>
  );
}
