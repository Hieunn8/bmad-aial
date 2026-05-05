import { useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { AdminPageShell, adminCard } from './AdminShared';

type Summary = { users?: { total: number }; roles?: { total: number }; data_sources?: { total: number }; audit?: { total: number } };

export function AdminDashboardPage(): React.JSX.Element {
  const [summary, setSummary] = useState<Summary>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const [users, roles, dataSources, audit] = await Promise.all([
        apiRequest<{ total: number }>('/v1/admin/users'),
        apiRequest<{ total: number }>('/v1/admin/roles'),
        apiRequest<{ total: number }>('/v1/admin/data-sources'),
        apiRequest<{ total: number }>('/v1/admin/audit-logs?page=1&page_size=1'),
      ]);
      setSummary({ users, roles, data_sources: dataSources, audit });
    }
    void load().catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Không tải được dashboard'));
  }, []);

  const cards = [
    { label: 'Người dùng', value: summary.users?.total ?? 0 },
    { label: 'Vai trò', value: summary.roles?.total ?? 0 },
    { label: 'Nguồn dữ liệu', value: summary.data_sources?.total ?? 0 },
    { label: 'Audit records - Nhật ký kiểm toán', value: summary.audit?.total ?? 0 },
  ];

  return (
    <AdminPageShell title="Tổng quan quản trị - Admin Dashboard">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '1rem' }}>
        {cards.map((card) => (
          <div key={card.label} style={adminCard}>
            <div style={{ color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontSize: '0.78rem' }}>{card.label}</div>
            <div style={{ marginTop: '0.45rem', fontSize: '2rem', fontWeight: 800 }}>{card.value}</div>
          </div>
        ))}
      </div>
    </AdminPageShell>
  );
}
