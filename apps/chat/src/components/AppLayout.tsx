import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthProvider';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps): React.JSX.Element {
  const auth = useAuth();
  const roles = auth.session?.claims.roles ?? [];
  const isAdminOrDataOwner = roles.includes('admin') || roles.includes('data_owner');

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
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)' }}>
              AI Assistant - Trợ lý dữ liệu nội bộ
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem', textAlign: 'right' }}>
            <div>{auth.session?.claims.name ?? auth.session?.claims.email ?? 'Khách'}</div>
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
            Đăng xuất
          </button>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <nav
          aria-label="Điều hướng chính"
          style={{
            width: 'var(--sidebar-width)',
            background: 'rgba(255,255,255,0.58)',
            borderRight: '1px solid rgba(117, 94, 60, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
            padding: '1.05rem 0.9rem',
            gap: '0.5rem',
          }}
        >
          <NavSection label="Ứng dụng">
            <NavLink to="/chat">Chat - Hỏi đáp dữ liệu</NavLink>
            <NavLink to="/analytics/forecast" activePrefix="/analytics">Phân tích - Dự báo</NavLink>
            <NavLink to="/memory">Memory Studio - Bộ nhớ</NavLink>
          </NavSection>

          {isAdminOrDataOwner && (
            <NavSection label="Quản lý">
              <NavLink to="/semantic">Semantic Studio - Lớp KPI</NavLink>
            </NavSection>
          )}

          {isAdminOrDataOwner && (
            <NavSection label="Quản trị">
              <NavLink to="/admin" activePrefix="/admin">Admin - Quản trị hệ thống</NavLink>
            </NavSection>
          )}
        </nav>

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

function NavSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div
        style={{
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--color-neutral-400)',
          fontWeight: 600,
          padding: '0.5rem 0.5rem 0.3rem',
        }}
      >
        {label}
      </div>
      <ul role="list" style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: '0.3rem' }}>
        {children}
      </ul>
    </div>
  );
}

function NavLink({ to, activePrefix, children }: { to: string; activePrefix?: string; children: React.ReactNode }) {
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '';
  const isActive = activePrefix ? pathname.startsWith(activePrefix) : pathname === to;
  return (
    <li>
      <a
        href={to}
        style={{
          display: 'block',
          padding: '0.65rem 0.85rem',
          borderRadius: '0.85rem',
          color: isActive ? '#0f766e' : 'var(--color-neutral-700)',
          textDecoration: 'none',
          fontSize: '0.92rem',
          fontWeight: isActive ? 600 : 500,
          background: isActive ? 'rgba(15, 118, 110, 0.10)' : undefined,
        }}
      >
        {children}
      </a>
    </li>
  );
}
