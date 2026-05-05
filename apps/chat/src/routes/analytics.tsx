import { createFileRoute, Link, Outlet, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/analytics')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: AnalyticsLayout,
});

const tabs = [
  { to: '/analytics/forecast', label: 'Dự báo', note: 'Forecast' },
  { to: '/analytics/anomaly', label: 'Bất thường', note: 'Anomaly' },
  { to: '/analytics/trend', label: 'Xu hướng', note: 'Trend' },
  { to: '/analytics/drilldown', label: 'Drill-down', note: 'Phân rã chỉ tiêu' },
];

function AnalyticsLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
      <div
        style={{
          display: 'flex',
          gap: '0.4rem',
          padding: '0.75rem 2.4rem 0',
          borderBottom: '1px solid rgba(117, 94, 60, 0.12)',
          background: 'rgba(255,255,255,0.7)',
        }}
      >
        {tabs.map((tab) => (
          <Link
            key={tab.to}
            to={tab.to}
            style={{
              padding: '0.6rem 1.1rem',
              borderRadius: '0.75rem 0.75rem 0 0',
              textDecoration: 'none',
              fontWeight: 500,
              fontSize: '0.92rem',
              color: 'var(--color-neutral-600)',
              borderBottom: '2px solid transparent',
            }}
            activeProps={{
              style: {
                padding: '0.6rem 1.1rem',
                borderRadius: '0.75rem 0.75rem 0 0',
                textDecoration: 'none',
                fontWeight: 700,
                fontSize: '0.92rem',
                color: '#0f766e',
                borderBottom: '2px solid #0f766e',
              },
            }}
          >
            {tab.label}
            <span style={{ display: 'block', fontSize: '0.74rem', fontWeight: 500, color: 'var(--color-neutral-500)' }}>
              {tab.note}
            </span>
          </Link>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </div>
    </div>
  );
}
