/**
 * ProvenanceDrawer — Story 2B.3 (UX-DR11)
 *
 * AC: slides in from right (not modal); conversation stays visible;
 * Escape closes; focus returns to trigger; pluggable ProvenanceSection children;
 * role="complementary"; data-testid="provenance-drawer"
 */
import { type ReactNode, useCallback, useEffect, useRef } from 'react';

export interface ProvenanceSectionProps {
  title: string;
  children: ReactNode;
}

export function ProvenanceSection({ title, children }: ProvenanceSectionProps): React.JSX.Element {
  return (
    <section style={{ marginBottom: 'var(--space-5, 20px)' }}>
      <h3 style={{
        fontSize: 'var(--font-size-sm, 0.875rem)',
        fontWeight: 'var(--font-weight-semibold, 600)',
        color: 'var(--color-neutral-500, #6b7280)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: 'var(--space-2, 8px)',
      }}>
        {title}
      </h3>
      {children}
    </section>
  );
}

export interface ProvenanceDrawerProps {
  open: boolean;
  onClose: () => void;
  triggerRef?: React.RefObject<HTMLElement>;
  children?: ReactNode;
}

const FOCUSABLE = 'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])';

export function ProvenanceDrawer({ open, onClose, triggerRef, children }: ProvenanceDrawerProps): React.JSX.Element {
  const drawerRef = useRef<HTMLElement>(null);

  const trapFocus = useCallback((e: KeyboardEvent): void => {
    if (e.key !== 'Tab' || !drawerRef.current) return;
    const focusable = Array.from(drawerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) { e.preventDefault(); last.focus(); }
    } else {
      if (document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') { onClose(); triggerRef?.current?.focus(); }
      else trapFocus(e);
    };
    document.addEventListener('keydown', handleKey);
    // Move focus into drawer on open
    const firstFocusable = drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE);
    (firstFocusable ?? drawerRef.current)?.focus();
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose, triggerRef, trapFocus]);

  if (!open) return <></>;

  return (
    <aside
      ref={drawerRef as React.RefObject<HTMLElement>}
      role="complementary"
      aria-label="Nguồn dữ liệu và bằng chứng"
      aria-modal="true"
      data-testid="provenance-drawer"
      className="aial-provenance-drawer"
      tabIndex={-1}
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 'min(28rem, 90vw)',
        backgroundColor: 'var(--color-surface, white)',
        borderLeft: '1px solid var(--color-border, #e5e7eb)',
        boxShadow: '-4px 0 24px rgba(0,0,0,0.1)',
        zIndex: 40,
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        animation: 'aial-drawer-in 250ms ease-out',
        outline: 'none',
      }}
    >
      <style>{`
        @keyframes aial-drawer-in {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .aial-provenance-drawer { animation: none !important; }
        }
      `}</style>

      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 'var(--space-4, 16px)',
        borderBottom: '1px solid var(--color-border, #e5e7eb)',
        position: 'sticky',
        top: 0,
        backgroundColor: 'var(--color-surface, white)',
        zIndex: 1,
      }}>
        <h2 style={{ fontSize: 'var(--font-size-lg, 1.125rem)', fontWeight: 'var(--font-weight-semibold, 600)', margin: 0 }}>
          Nguồn dữ liệu và bằng chứng
        </h2>
        <button
          type="button"
          aria-label="Đóng khung nguồn dữ liệu (Escape)"
          onClick={() => { onClose(); triggerRef?.current?.focus(); }}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.25rem',
            color: 'var(--color-neutral-500)',
            padding: 'var(--space-1)',
          }}
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: 'var(--space-4, 16px)', flex: 1 }}>
        {children}
      </div>
    </aside>
  );
}
