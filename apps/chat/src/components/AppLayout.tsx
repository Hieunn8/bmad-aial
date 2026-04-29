/**
 * AppLayout — Main application shell with ARIA landmark structure
 * Story 1.7 AC: ARIA landmark structure (<main>, <nav>, <header>) is present
 * UX-DR24: WCAG 2.2 AA compliance — ARIA landmarks required
 */
import type { ReactNode } from 'react';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps): React.JSX.Element {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: 'var(--color-background)',
        fontFamily: 'var(--font-family-base)',
      }}
    >
      {/* ARIA landmark: header */}
      <header
        role="banner"
        style={{
          height: 'var(--header-height)',
          backgroundColor: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          paddingInline: 'var(--space-4)',
          position: 'sticky',
          top: 0,
          zIndex: 'var(--z-sticky)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: '2rem',
              height: '2rem',
              backgroundColor: 'var(--color-primary)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '0.875rem',
              fontWeight: 700,
            }}
          >
            AI
          </span>
          <span
            style={{
              fontSize: 'var(--font-size-md)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-neutral-900)',
            }}
          >
            AIAL
          </span>
        </div>
      </header>

      <div
        style={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        {/* ARIA landmark: navigation */}
        <nav
          aria-label="Điều hướng chính"
          style={{
            width: 'var(--sidebar-width)',
            backgroundColor: 'var(--color-surface)',
            borderRight: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
          }}
        >
          {/* Navigation items will be populated by authenticated routes */}
          <ul
            role="list"
            style={{ margin: 0, padding: 'var(--space-2)', listStyle: 'none' }}
          >
            <li>
              <a
                href="/"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-neutral-700)',
                  textDecoration: 'none',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-medium)',
                }}
                aria-current="page"
              >
                Trò chuyện
              </a>
            </li>
          </ul>
        </nav>

        {/* ARIA landmark: main content */}
        <main
          id="main-content"
          role="main"
          aria-label="Nội dung chính"
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
