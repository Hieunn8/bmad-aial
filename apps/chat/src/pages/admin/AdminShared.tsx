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
