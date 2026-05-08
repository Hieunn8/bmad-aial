import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ChatAssistantConsole } from './ChatAssistantConsole';

const connectMock = vi.fn();
const resetMock = vi.fn();
let latestOptions: { onEvent?: (event: import('@aial/types').SSEEvent) => void } | undefined;

vi.mock('@aial/ui/confidence-breakdown-card', () => ({
  ConfidenceBreakdownCard: ({
    detail,
    onActions,
  }: {
    detail?: string;
    onActions?: Array<{ label: string; onClick: () => void }>;
  }) => (
    <div>
      <div>{detail}</div>
      {onActions?.map((action) => (
        <button key={action.label} type="button" onClick={action.onClick}>
          {action.label}
        </button>
      ))}
    </div>
  ),
}));

vi.mock('@aial/ui/provenance-drawer', () => ({
  ProvenanceDrawer: ({
    open,
    children,
  }: {
    open: boolean;
    children?: ReactNode;
  }) => (open ? <div data-testid="provenance-drawer">{children}</div> : null),
  ProvenanceSection: ({
    title,
    children,
  }: {
    title: string;
    children?: ReactNode;
  }) => (
    <section>
      <h3>{title}</h3>
      {children}
    </section>
  ),
}));

vi.mock('../../hooks/useSSEStream', () => ({
  useSSEStream: (_path: string, options?: { onEvent?: (event: import('@aial/types').SSEEvent) => void }) => {
    latestOptions = options;
    return {
    state: { status: 'idle', events: [], error: null, traceId: null },
    connect: connectMock,
    reset: resetMock,
    };
  },
}));

describe('ChatAssistantConsole', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    connectMock.mockReset();
    resetMock.mockReset();
    latestOptions = undefined;
  });

  it('renders the query and export controls', () => {
    render(<ChatAssistantConsole />);

    expect(screen.getByRole('heading', { name: 'Chat Assistant' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ask AI' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeDisabled();
    expect(screen.getByRole('combobox', { name: 'Export format' })).toHaveValue('xlsx');
  });

  it('shows cache freshness metadata and sends force_refresh on manual refresh', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) as { force_refresh?: boolean } : {};
      return new Response(
        JSON.stringify({
          request_id: body.force_refresh ? 'req-refresh' : 'req-cache',
          status: 'streaming',
          trace_id: body.force_refresh ? 'trace-refresh' : 'trace-cache',
          cache_hit: !body.force_refresh,
          cache_timestamp: '2026-05-03T12:34:56Z',
          freshness_indicator: 'Kết quả từ cache — cập nhật lúc 2026-05-03 12:34:56 UTC',
          cache_similarity: 0.91,
          force_refresh_available: !body.force_refresh,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<ChatAssistantConsole />);

    await userEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
    expect(await screen.findByText(/stream.*truy/i)).toBeInTheDocument();

    expect(await screen.findByRole('status', { name: 'Cache freshness' })).toHaveTextContent('Kết quả từ cache');
    expect(screen.getByText(/Độ tương đồng ngữ nghĩa: 91%/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Tải lại dữ liệu mới' }));

    const payloads = fetchMock.mock.calls.map((call) => JSON.parse(String(call[1]?.body ?? '{}')) as { force_refresh?: boolean });
    expect(payloads[0]?.force_refresh).toBe(false);
    expect(payloads[1]?.force_refresh).toBe(true);
  });

  it('renders cross-source conflict card and provenance drawer from done event metadata', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          request_id: 'req-conflict',
          status: 'streaming',
          trace_id: 'trace-conflict',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    render(<ChatAssistantConsole />);

    await userEvent.click(screen.getByRole('button', { name: 'Ask AI' }));
    latestOptions?.onEvent?.({
      type: 'done',
      trace_id: 'trace-conflict',
      answer: 'Chi phí vận hành Q1 là 5.2B so với ngân sách 4.9B.',
      confidence_state: 'cross-source-conflict',
      conflict_detail: 'FINANCE ghi nhận 5.2B trong khi BUDGET ghi nhận 4.9B cho OPS / 2026-Q1.',
      provenance: [
        {
          source: 'finance-primary',
          domain: 'FINANCE',
          department_code: 'OPS',
          period_key: '2026-Q1',
          value_label: 'actual_amount',
          value: 5.2,
        },
        {
          source: 'budget-primary',
          domain: 'BUDGET',
          department_code: 'OPS',
          period_key: '2026-Q1',
          value_label: 'budget_amount',
          value: 4.9,
        },
      ],
    });

    expect(await screen.findByText(/FINANCE ghi nhận 5.2B/i)).toBeInTheDocument();
    expect(screen.queryByText(/stream.*truy/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Xem chi tiết nguồn lệch' }));

    expect(await screen.findByTestId('provenance-drawer')).toBeInTheDocument();
    expect(screen.getByText('finance-primary')).toBeInTheDocument();
    expect(screen.getByText('budget-primary')).toBeInTheDocument();
  });
});
