import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DrilldownExplainabilityPanel } from './DrilldownExplainabilityPanel';

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

vi.mock('@aial/ui/export-job-status', () => ({
  ExportJobStatus: ({ title, detail }: { title?: string; detail?: string }) => (
    <div>
      <div>{title}</div>
      <div>{detail}</div>
    </div>
  ),
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

describe('DrilldownExplainabilityPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders direct explainability factors when shap is available', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/analytics/drilldown-explainability')) {
        return new Response(
          JSON.stringify({
            dimension: 'region',
            department_scope: 'sales',
            forecast_metric: 'total_revenue',
            confidence_label: 'có khả năng tăng',
            explanation_status: 'ready',
            business_labels_mapped: true,
            drilldown: [{ label: 'HCM', forecast_value: 4800, share_percent: 38 }],
            top_factors: [
              { label: 'Mùa vụ', contribution_percent: 45 },
              { label: 'Xu hướng thị trường', contribution_percent: 30 },
              { label: 'Chiến dịch marketing', contribution_percent: 15 },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<DrilldownExplainabilityPanel />);

    await userEvent.click(screen.getByRole('button', { name: /Phân tích chi tiết theo khu vực/i }));

    expect(await screen.findByText(/Yếu tố 1: Mùa vụ/i)).toBeInTheDocument();
    expect(screen.getByText(/có khả năng tăng/i)).toBeInTheDocument();
  });

  it('shows async fallback when shap is unavailable', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/analytics/drilldown-explainability')) {
        return new Response(
          JSON.stringify({
            dimension: 'region',
            department_scope: 'sales',
            forecast_metric: 'total_revenue',
            confidence_label: 'không rõ xu hướng',
            explanation_status: 'pending',
            drilldown: [{ label: 'HCM', forecast_value: 4800, share_percent: 38 }],
            top_factors: [],
            explainability_job: {
              job_id: 'job-1',
              status: 'queued',
              queue_name: 'analytics-batch',
              task_name: 'analytics.explainability.generate',
              message: 'Giải thích chi tiết đang được xử lý',
            },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/v1/analytics/explainability-jobs/job-1')) {
        return new Response(
          JSON.stringify({
            job_id: 'job-1',
            status: 'completed',
            queue_name: 'analytics-batch',
            task_name: 'analytics.explainability.generate',
            error: null,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/v1/analytics/explainability-jobs/job-1/result')) {
        return new Response(
          JSON.stringify({
            job_id: 'job-1',
            status: 'completed',
            confidence_label: 'có khả năng tăng',
            top_factors: [
              { label: 'Mùa vụ', contribution_percent: 45 },
              { label: 'Xu hướng thị trường', contribution_percent: 30 },
              { label: 'Chiến dịch marketing', contribution_percent: 15 },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<DrilldownExplainabilityPanel />);

    await userEvent.click(screen.getByLabelText(/SHAP available/i));
    await userEvent.click(screen.getByRole('button', { name: /Phân tích chi tiết theo khu vực/i }));

    expect((await screen.findAllByText(/Giải thích chi tiết đang được xử lý/i)).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByText(/Yếu tố 1: Mùa vụ/i)).toBeInTheDocument();
    });
  });
});
