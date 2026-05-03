import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AnomalyAlertsPanel } from './AnomalyAlertsPanel';

vi.mock('@aial/ui/chart-reveal', () => ({
  ChartReveal: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  useChartTheme: () => ({
    primary: '#2563eb',
    secondary: '#7c3aed',
    grid: '#e5e7eb',
    text: '#4b5563',
    colors: ['#2563eb', '#16a34a', '#d97706', '#dc2626'],
  }),
}));

vi.mock('@aial/ui/confidence-breakdown-card', () => ({
  ConfidenceBreakdownCard: ({ detail }: { detail?: string }) => <div>{detail}</div>,
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => <div>grid</div>,
  Legend: () => <div>legend</div>,
  Tooltip: () => <div>tooltip</div>,
  XAxis: () => <div>x-axis</div>,
  YAxis: () => <div>y-axis</div>,
  Area: () => <div>area</div>,
  Line: ({ name }: { name?: string }) => <div>{name}</div>,
  ReferenceDot: () => <div>reference-dot</div>,
}));

describe('AnomalyAlertsPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads anomaly history, shows detail, and acknowledges alert', async () => {
    const alert = {
      alert_id: 'alert-1',
      metric_name: 'order_volume',
      domain: 'sales',
      department_scope: 'sales',
      region: 'HCM',
      anomaly_timestamp: '2026-03-15T09:00:00+07:00',
      deviation_percent: -40,
      severity: 'high',
      status: 'active',
      explanation: 'Đơn hàng khu vực HCM ngày 15/3 thấp hơn 40% so với dự kiến.',
      false_positive_rate_30d: 0.08,
      detection_latency_minutes: 42,
      created_at: '2026-03-15T09:42:00+07:00',
      isolation_forest_score: -0.22,
      suggested_actions: ['A', 'B', 'C'],
      confidence_state: 'low-confidence',
      series: [
        { timestamp: '2026-03-15', actual: 780, expected_min: 1185, expected_max: 1310, is_anomaly: true },
      ],
    };

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/anomaly-detection/alerts')) {
        return new Response(JSON.stringify({ alerts: [alert], total: 1 }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.endsWith('/v1/anomaly-detection/alerts/alert-1')) {
        return new Response(JSON.stringify(alert), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.endsWith('/v1/anomaly-detection/alerts/alert-1/acknowledge')) {
        return new Response(JSON.stringify({ alert: { ...alert, status: 'acknowledged' } }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<AnomalyAlertsPanel />);

    expect(await screen.findByText(/Đơn hàng khu vực HCM ngày 15\/3 thấp hơn 40% so với dự kiến/i)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Acknowledge' })).toBeInTheDocument();
    expect(screen.getByText(/False positive 8.0%/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Acknowledge' }));

    await waitFor(() => {
      expect(screen.getByText(/Alert đã được xác nhận/i)).toBeInTheDocument();
    });
  });
});
