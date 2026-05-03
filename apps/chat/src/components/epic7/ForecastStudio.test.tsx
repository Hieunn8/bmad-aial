import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ForecastStudio } from './ForecastStudio';

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

vi.mock('@aial/ui/export-job-status', () => ({
  ExportJobStatus: ({ title, detail, etaLabel }: { title?: string; detail?: string; etaLabel?: string | null }) => (
    <div>
      <div>{title}</div>
      <div>{detail}</div>
      <div>{etaLabel}</div>
    </div>
  ),
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
}));

describe('ForecastStudio', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it('runs forecast job and renders summary plus download link', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/forecast/run')) {
        return new Response(
          JSON.stringify({
            job_id: 'forecast-job-1',
            status: 'queued',
            queue_name: 'forecast-batch',
            task_name: 'forecast.time_series.generate_report',
            heavy_job: true,
            estimated_wait_seconds: 180,
            estimated_wait_message: 'Kết quả dự kiến sau khoảng 3 phút.',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/v1/forecast/forecast-job-1')) {
        return new Response(
          JSON.stringify({
            job_id: 'forecast-job-1',
            status: 'completed',
            queue_name: 'forecast-batch',
            task_name: 'forecast.time_series.generate_report',
            heavy_job: true,
            estimated_wait_seconds: 180,
            estimated_wait_message: 'Kết quả dự kiến sau khoảng 3 phút.',
            provider_used: 'nixtla-timegpt',
            mape: 0.124,
            download_url: '/v1/forecast/forecast-job-1/download',
            cached_until: '2026-05-03T13:00:00Z',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/v1/forecast/forecast-job-1/result')) {
        return new Response(
          JSON.stringify({
            query: 'Dự báo doanh thu Q3 2026 theo kênh phân phối',
            provider_used: 'nixtla-timegpt',
            fallback_used: false,
            mape: 0.124,
            confidence_state: 'forecast-uncertainty',
            generated_at: '2026-05-03T12:00:00Z',
            summary: 'Dự báo doanh thu Q3 2026 tăng nhẹ trên cả ba kênh với biên độ bất định vừa phải.',
            series: [
              { period: '2026-Q1', channel: 'Retail', actual: 12.1, point_type: 'historical' },
              { period: '2026-Q2', channel: 'Retail', actual: 12.8, point_type: 'historical' },
              { period: '2026-Q3', channel: 'Retail', forecast: 13.6, lower_95: 12.24, upper_95: 14.96, point_type: 'forecast' },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<ForecastStudio />);

    await userEvent.click(screen.getByRole('button', { name: 'Run Forecast' }));

    expect(await screen.findByText(/Forecast hoàn tất/i)).toBeInTheDocument();
    expect(screen.getByText(/Forecast batch lớn/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Kết quả dự kiến sau khoảng 3 phút/i).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByText(/Dự báo doanh thu Q3 2026 tăng nhẹ/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Provider: nixtla-timegpt/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download forecast JSON' })).toHaveAttribute(
      'href',
      expect.stringContaining('/v1/forecast/forecast-job-1/download'),
    );
  });

  it('surfaces queue timeout retry guidance when the forecast job fails in queue', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/forecast/run')) {
        return new Response(
          JSON.stringify({
            job_id: 'forecast-job-timeout',
            status: 'queued',
            queue_name: 'forecast-batch',
            task_name: 'forecast.time_series.generate_report',
            heavy_job: true,
            estimated_wait_seconds: 900,
            estimated_wait_message: 'Kết quả dự kiến sau 15 phút.',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/v1/forecast/forecast-job-timeout')) {
        return new Response(
          JSON.stringify({
            job_id: 'forecast-job-timeout',
            status: 'failed',
            queue_name: 'forecast-batch',
            task_name: 'forecast.time_series.generate_report',
            heavy_job: true,
            estimated_wait_seconds: 900,
            estimated_wait_message: 'Kết quả dự kiến sau 15 phút.',
            error: 'queue_timeout',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<ForecastStudio />);

    await userEvent.click(screen.getByRole('button', { name: 'Run Forecast' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Forecast job đã chờ quá 30 phút trong hàng đợi forecast-batch. Hãy thử lại.',
    );
    expect(screen.getByText(/Job thất bại:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Kết quả dự kiến sau 15 phút/i).length).toBeGreaterThan(0);
  });
});
