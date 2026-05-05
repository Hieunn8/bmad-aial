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
  { to: '/admin', label: 'Tổng quan', note: 'Dashboard' },
  { to: '/admin/users', label: 'Người dùng', note: 'Users' },
  { to: '/admin/roles', label: 'Vai trò', note: 'Roles' },
  { to: '/admin/data-sources', label: 'Nguồn dữ liệu', note: 'Data sources' },
  { to: '/admin/documents', label: 'Tài liệu', note: 'Documents' },
  { to: '/admin/audit-log', label: 'Audit Log', note: 'Nhật ký kiểm toán' },
];

function AdminLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      <nav
        style={{
          background: 'rgba(255,255,255,0.7)',
          borderBottom: '1px solid rgba(117, 94, 60, 0.12)',
          padding: '0.75rem 2.4rem 0',
          display: 'flex',
          gap: '0.4rem',
          overflowX: 'auto',
        }}
      >
        {adminNavItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            style={{
              padding: '0.6rem 1.1rem',
              borderRadius: '0.75rem 0.75rem 0 0',
              textDecoration: 'none',
              fontSize: '0.92rem',
              fontWeight: 500,
              color: 'var(--color-neutral-600)',
              borderBottom: '2px solid transparent',
            }}
            activeProps={{
              style: {
                padding: '0.6rem 1.1rem',
                borderRadius: '0.75rem 0.75rem 0 0',
                textDecoration: 'none',
                fontSize: '0.92rem',
                fontWeight: 700,
                color: '#0f766e',
                borderBottom: '2px solid #0f766e',
              },
            }}
          >
            {item.label}
            <span style={{ display: 'block', fontSize: '0.74rem', fontWeight: 500, color: 'var(--color-neutral-500)' }}>
              {item.note}
            </span>
          </Link>
        ))}
      </nav>
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
