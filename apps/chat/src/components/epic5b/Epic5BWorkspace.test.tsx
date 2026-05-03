import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Epic5BWorkspace } from './Epic5BWorkspace';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Epic5BWorkspace', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders semantic, memory, and history surfaces from API data', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/admin/semantic-layer/metrics')) {
        return jsonResponse({
          metrics: [
            {
              term: 'doanh thu thuáº§n',
              definition: 'Doanh thu sau giáº£m trá»«',
              formula: 'SUM(NET_REVENUE)',
              owner: 'Finance',
              freshness_rule: 'daily',
              active_version_id: 'v2',
              version_count: 2,
              cache_invalidated_at: '2026-05-03T10:00:00Z',
            },
          ],
        });
      }
      if (url.includes('/v1/admin/semantic-layer/metrics/') && url.includes('/versions')) {
        return jsonResponse({
          versions: [
            {
              version_id: 'v1',
              term: 'doanh thu thuáº§n',
              definition: 'Doanh thu cÅ©',
              formula: 'SUM(GROSS_REVENUE)',
              owner: 'Finance',
              freshness_rule: 'daily',
              changed_by: 'owner-1',
              timestamp: '2026-05-03T09:00:00Z',
              previous_formula: null,
              action: 'seed',
              rollback_reason: null,
            },
            {
              version_id: 'v2',
              term: 'doanh thu thuáº§n',
              definition: 'Doanh thu sau giáº£m trá»«',
              formula: 'SUM(NET_REVENUE)',
              owner: 'Finance',
              freshness_rule: 'daily',
              changed_by: 'owner-1',
              timestamp: '2026-05-03T10:00:00Z',
              previous_formula: 'SUM(GROSS_REVENUE)',
              action: 'publish',
              rollback_reason: null,
            },
          ],
        });
      }
      if (url.includes('/v1/admin/semantic-layer/metrics/') && url.includes('/diff')) {
        return jsonResponse({
          diff: [
            { kind: 'removed', value: 'SUM(GROSS_REVENUE)' },
            { kind: 'added', value: 'SUM(NET_REVENUE)' },
          ],
        });
      }
      if (url.endsWith('/v1/chat/suggestions')) {
        return jsonResponse({
          suggestions: [{ type: 'kpi', label: 'doanh thu thuáº§n', uses: 6 }],
        });
      }
      if (url.endsWith('/v1/chat/templates')) {
        if (init?.method === 'POST') {
          return jsonResponse(
            {
              template: {
                template_id: 'template-2',
                name: 'Revenue Monthly',
                query_intent: 'revenue trend',
                filters: 'month filter',
                time_range: 'last_30_days',
                output_format: 'table',
                created_at: '2026-05-03T11:00:00Z',
              },
            },
            201,
          );
        }
        return jsonResponse({
          templates: [
            {
              template_id: 'template-1',
              name: 'Finance Monthly',
              query_intent: 'revenue trend',
              filters: 'month filter',
              time_range: 'last_30_days',
              output_format: 'table',
              created_at: '2026-05-03T10:00:00Z',
            },
          ],
        });
      }
      if (url.endsWith('/v1/chat/history/audit')) {
        return jsonResponse({ violations: [] });
      }
      if (url.includes('/v1/chat/history/search')) {
        return jsonResponse({
          results: [
            {
              entry_id: 'history-1',
              created_at: '2026-05-03T08:00:00Z',
              intent_type: 'chat_query',
              topic: 'monthly revenue trend',
              filter_context: 'march filter',
              key_result_summary: 'summary only',
            },
          ],
        });
      }
      if (url.includes('/v1/chat/memory/context')) {
        return jsonResponse({
          summaries: [
            {
              summary_id: 'summary-1',
              topic: 'monthly revenue trend',
              filter_context: 'march filter',
              summary_text: 'business summary only',
              created_at: '2026-05-03T08:00:00Z',
            },
          ],
          token_budget_increase_percent: 10,
          threshold: 0.7,
        });
      }
      if (url.includes('/v1/chat/history/history-1/reuse')) {
        return jsonResponse({
          preload: {
            topic: 'monthly revenue trend',
            filters: 'march filter',
            intent_type: 'chat_query',
          },
        });
      }
      if (url.endsWith('/v1/admin/semantic-layer/metrics/publish')) {
        return jsonResponse(
          {
            version: {
              version_id: 'v3',
              term: 'doanh thu thuáº§n',
              definition: 'new',
              formula: 'SUM(NET_REVENUE) - SUM(RETURNS)',
              owner: 'Finance',
              freshness_rule: 'daily',
              changed_by: 'owner-1',
              timestamp: '2026-05-03T12:00:00Z',
              previous_formula: 'SUM(NET_REVENUE)',
              action: 'publish',
              rollback_reason: null,
            },
          },
          201,
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<Epic5BWorkspace />);

    expect(await screen.findByText(/Semantic governance, memory recall/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /kpi/i })).toHaveValue('doanh thu thuáº§n');
    expect(await screen.findByText('Finance Monthly')).toBeInTheDocument();
    expect((await screen.findAllByText('monthly revenue trend')).length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /dùng lại|dÃ¹ng láº¡i/i }));
    expect(await screen.findByText(/monthly revenue trend \| march filter/i)).toBeInTheDocument();
  });

  it('shows semantic permission state but keeps memory surfaces available', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/admin/semantic-layer/metrics')) {
        return jsonResponse({ detail: 'Admin or data_owner role required' }, 403);
      }
      if (url.endsWith('/v1/chat/suggestions')) {
        return jsonResponse({ suggestions: [{ type: 'template', label: 'Revenue Monthly', template_id: 't1' }] });
      }
      if (url.endsWith('/v1/chat/templates')) {
        return jsonResponse({ templates: [] });
      }
      if (url.endsWith('/v1/chat/history/audit')) {
        return jsonResponse({ violations: [] });
      }
      if (url.includes('/v1/chat/history/search')) {
        return jsonResponse({ results: [] });
      }
      if (url.includes('/v1/chat/memory/context')) {
        return jsonResponse({ summaries: [], token_budget_increase_percent: 0, threshold: 0.7 });
      }
      throw new Error(`Unhandled fetch ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<Epic5BWorkspace />);

    const permissionState = await screen.findByRole('status');
    expect(permissionState).toHaveTextContent(/data_owner/i);
    expect(permissionState).toHaveTextContent(/admin/i);
    expect(await screen.findByText('Memory Studio')).toBeInTheDocument();
    expect(await screen.findByText('Revenue Monthly')).toBeInTheDocument();

    const publishButton = screen.getByRole('button', { name: 'Publish Version' });
    expect(publishButton).toBeDisabled();

    expect(screen.getByText('Clean')).toBeInTheDocument();
  });
});
