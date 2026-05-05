import type { CSSProperties } from 'react';

export const cardStyle: CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
};

export const inputStyle: CSSProperties = {
  width: '100%',
  padding: '0.8rem 0.95rem',
  borderRadius: '0.9rem',
  border: '1px solid rgba(117, 94, 60, 0.22)',
  background: 'rgba(255,255,255,0.92)',
  color: 'var(--color-neutral-900)',
  fontSize: '0.95rem',
};

export const buttonStyle: CSSProperties = {
  border: 'none',
  borderRadius: '999px',
  padding: '0.8rem 1.1rem',
  background: 'linear-gradient(135deg, #0f766e 0%, #115e59 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

export const ghostButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: 'rgba(15, 118, 110, 0.09)',
  color: '#115e59',
};

export const dangerButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
};

export const pageShell: CSSProperties = {
  minHeight: '100%',
  background:
    'linear-gradient(180deg, rgba(242,236,226,0.92) 0%, rgba(248,245,239,0.98) 22%, rgba(255,255,255,1) 100%)',
  color: 'var(--color-neutral-900)',
  padding: '2rem 2.4rem 3rem',
};

export const pageTitle: CSSProperties = {
  margin: 0,
  fontSize: '1.6rem',
  fontWeight: 700,
  color: 'var(--color-neutral-900)',
};

export const sectionLabel: CSSProperties = {
  fontSize: '0.78rem',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: 'var(--color-neutral-500)',
  fontWeight: 600,
};
