import { createFileRoute, Link, Outlet, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/admin')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
    const roles = context.auth.session?.claims.roles ?? [];
    if (!roles.includes('admin') && !roles.includes('data_owner')) {
      throw redirect({ to: '/chat' });
    }
  },
  component: AdminLayout,
});

const adminNavItems = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/users', label: 'Nguoi dung' },
  { to: '/admin/roles', label: 'Vai tro' },
  { to: '/admin/data-sources', label: 'Nguon du lieu' },
  { to: '/admin/documents', label: 'Tai lieu' },
  { to: '/admin/audit-log', label: 'Audit Log' },
];

function AdminLayout() {
  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      <nav
        style={{
          width: '13rem',
          background: 'rgba(255,255,255,0.5)',
          borderRight: '1px solid rgba(117, 94, 60, 0.12)',
          padding: '1rem 0.7rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.3rem',
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--color-neutral-400)',
            fontWeight: 600,
            padding: '0.3rem 0.5rem 0.5rem',
          }}
        >
          Quan tri he thong
        </div>
        {adminNavItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            style={{
              display: 'block',
              padding: '0.6rem 0.8rem',
              borderRadius: '0.75rem',
              textDecoration: 'none',
              fontSize: '0.9rem',
              fontWeight: 500,
              color: 'var(--color-neutral-700)',
            }}
            activeProps={{
              style: {
                display: 'block',
                padding: '0.6rem 0.8rem',
                borderRadius: '0.75rem',
                textDecoration: 'none',
                fontSize: '0.9rem',
                fontWeight: 700,
                color: '#0f766e',
                background: 'rgba(15,118,110,0.10)',
              },
            }}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
