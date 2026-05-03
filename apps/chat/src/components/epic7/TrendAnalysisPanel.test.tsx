import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { TrendAnalysisPanel } from './TrendAnalysisPanel';

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

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => <div>grid</div>,
  Legend: () => <div>legend</div>,
  Tooltip: () => <div>tooltip</div>,
  XAxis: () => <div>x-axis</div>,
  YAxis: () => <div>y-axis</div>,
  Bar: ({ name }: { name?: string }) => <div>{name}</div>,
}));

describe('TrendAnalysisPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('runs trend analysis and shows plain-language explanation plus drill-down', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/trend-analysis/run')) {
        return new Response(
          JSON.stringify({
            metric_name: 'doanh thu',
            comparison_type: 'yoy',
            provider_used: 'statsmodels-trend',
            department_scope: 'sales',
            dimension: 'region',
            current_period: 'Q1 2026',
            previous_period: 'Q1 2025',
            current_value: 12600,
            previous_value: 11250,
            absolute_change: 1350,
            percentage_change: 12,
            direction: 'tăng',
            explanation: 'doanh thu tăng 12% so với q1 2025, tương đương 1,350. Mức thay đổi tập trung nhiều nhất ở HCM.',
            contains_jargon: false,
            drilldown: [{ label: 'HCM', current_value: 4800, previous_value: 4250, absolute_change: 550, percentage_change: 12.9 }],
            generated_at: '2026-05-03T12:00:00Z',
            cache_hit: false,
            cached_at: null,
            cache_similarity: null,
            uat_gate: { required_reviewers: ['HR', 'Sales', 'Finance'], minimum_clarity_score: 4, status: 'pending-manual-review' },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<TrendAnalysisPanel />);

    await userEvent.click(screen.getByRole('button', { name: 'Run Trend' }));

    expect(await screen.findByText(/doanh thu tăng 12%/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Manual UAT gate/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Kết quả mới từ statsmodels-trend/i)).toBeInTheDocument();
    expect(screen.getByText(/Mức thay đổi tập trung nhiều nhất ở HCM/i)).toBeInTheDocument();
  });
});
