import type { ReactNode } from 'react';
import { cardStyle, pageShell, pageTitle } from '../../styles/shared';

export function AdminPageShell({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section style={pageShell}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.2rem' }}>
        <h1 style={pageTitle}>{title}</h1>
        {actions}
      </div>
      {children}
    </section>
  );
}

export const adminCard = { ...cardStyle, padding: '1.2rem' };

export const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'separate',
  borderSpacing: 0,
  fontSize: '0.92rem',
};

export const cellStyle: React.CSSProperties = {
  padding: '0.75rem',
  borderBottom: '1px solid rgba(117,94,60,0.12)',
  textAlign: 'left',
  verticalAlign: 'top',
};

export function splitList(value: string): string[] {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

export function MultiSelectField({
  label,
  note,
  options,
  value,
  onChange,
  emptyText = 'Chưa có dữ liệu để chọn',
}: {
  label: string;
  note?: string;
  options: string[];
  value: string[];
  onChange: (nextValue: string[]) => void;
  emptyText?: string;
}) {
  const uniqueOptions = Array.from(new Set(options.filter(Boolean))).sort((left, right) => left.localeCompare(right));
  const selected = new Set(value);

  function toggle(option: string, checked: boolean): void {
    const next = new Set(selected);
    if (checked) {
      next.add(option);
    } else {
      next.delete(option);
    }
    onChange(Array.from(next).sort((left, right) => left.localeCompare(right)));
  }

  return (
    <fieldset
      style={{
        border: '1px solid rgba(117,94,60,0.18)',
        borderRadius: '0.9rem',
        padding: '0.75rem 0.85rem',
        margin: 0,
        background: 'rgba(255,255,255,0.72)',
        minWidth: 0,
      }}
    >
      <legend style={{ padding: '0 0.25rem', fontWeight: 700, color: 'var(--color-neutral-800)' }}>{label}</legend>
      {note ? <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.82rem', marginBottom: '0.5rem' }}>{note}</div> : null}
      {uniqueOptions.length === 0 ? (
        <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>{emptyText}</div>
      ) : (
        <div style={{ display: 'grid', gap: '0.35rem', maxHeight: '9rem', overflowY: 'auto' }}>
          {uniqueOptions.map((option) => (
            <label key={option} style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: 0 }}>
              <input
                type="checkbox"
                checked={selected.has(option)}
                onChange={(event) => toggle(option, event.target.checked)}
              />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{option}</span>
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
