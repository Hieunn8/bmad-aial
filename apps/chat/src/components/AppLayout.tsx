import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthProvider';

interface AppLayoutProps {
  children: ReactNode;
}

const navItemStyle: React.CSSProperties = {
  display: 'block',
  padding: '0.8rem 0.95rem',
  borderRadius: '1rem',
  color: 'var(--color-neutral-700)',
  textDecoration: 'none',
  fontSize: '0.95rem',
  fontWeight: 600,
  background: 'rgba(255,255,255,0.72)',
};

export function AppLayout({ children }: AppLayoutProps): React.JSX.Element {
  const auth = useAuth();
  const roles = auth.session?.claims.roles ?? [];
  const canManageDocuments = roles.includes('admin') || roles.includes('data_owner');

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f4ede2 0%, #fbfaf7 42%, #eff8f7 100%)',
        fontFamily: 'var(--font-family-base)',
      }}
    >
      <header
        role="banner"
        style={{
          height: 'var(--header-height)',
          background: 'rgba(255,255,255,0.82)',
          borderBottom: '1px solid rgba(117, 94, 60, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingInline: '1.4rem',
          position: 'sticky',
          top: 0,
          zIndex: 'var(--z-sticky)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <span
            aria-hidden="true"
            style={{
              width: '2.3rem',
              height: '2.3rem',
              background: 'linear-gradient(135deg, #0f766e 0%, #115e59 100%)',
              borderRadius: '0.9rem',
              display: 'grid',
              placeItems: 'center',
              color: 'white',
              fontSize: '0.92rem',
              fontWeight: 800,
              boxShadow: '0 12px 30px rgba(15, 118, 110, 0.22)',
            }}
          >
            AI
          </span>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-neutral-900)' }}>AIAL</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)' }}>Epic 5B + 6 workspace</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem', textAlign: 'right' }}>
            <div>{auth.session?.claims.name ?? auth.session?.claims.email ?? 'Guest'}</div>
            <div>{roles.join(', ') || 'user'}</div>
          </div>
          <button
            type="button"
            onClick={auth.logout}
            style={{
              border: '1px solid rgba(117, 94, 60, 0.16)',
              borderRadius: '999px',
              padding: '0.55rem 0.9rem',
              background: 'rgba(255,255,255,0.82)',
              cursor: 'pointer',
              color: 'var(--color-neutral-700)',
              fontWeight: 600,
            }}
          >
            Logout
          </button>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <nav
          aria-label="Primary navigation"
          style={{
            width: 'var(--sidebar-width)',
            background: 'rgba(255,255,255,0.58)',
            borderRight: '1px solid rgba(117, 94, 60, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
            padding: '1.05rem 0.9rem',
            gap: '1rem',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '0.78rem',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--color-neutral-500)',
              }}
            >
              Workspace
            </div>
            <ul
              role="list"
              style={{ margin: '0.7rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.55rem' }}
            >
              <li><a href="#chat-assistant" style={navItemStyle}>Chat assistant</a></li>
              {canManageDocuments ? <li><a href="#document-admin" style={navItemStyle}>Document admin</a></li> : null}
              <li><a href="#semantic-studio" style={navItemStyle}>Semantic studio</a></li>
              <li><a href="#memory-studio" style={navItemStyle}>Memory studio</a></li>
              <li><a href="#history-studio" style={navItemStyle}>History studio</a></li>
            </ul>
          </div>
          <div
            style={{
              borderRadius: '1.1rem',
              background: 'linear-gradient(160deg, rgba(15,118,110,0.08) 0%, rgba(17,94,89,0.02) 100%)',
              padding: '0.95rem 1rem',
              color: 'var(--color-neutral-700)',
              lineHeight: 1.6,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Delivery note</div>
            <div style={{ fontSize: '0.88rem' }}>
              This workspace now carries Epic 5B UI plus the first Epic 6 export flow on top of the governed backend APIs.
            </div>
          </div>
        </nav>

        <main
          id="main-content"
          role="main"
          aria-label="Main content"
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
