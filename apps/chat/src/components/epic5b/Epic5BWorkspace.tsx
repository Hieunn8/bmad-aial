import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ChatAssistantConsole } from '../epic6/ChatAssistantConsole';
import { AnomalyAlertsPanel } from '../epic7/AnomalyAlertsPanel';
import { DrilldownExplainabilityPanel } from '../epic7/DrilldownExplainabilityPanel';
import { ForecastStudio } from '../epic7/ForecastStudio';
import { TrendAnalysisPanel } from '../epic7/TrendAnalysisPanel';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../auth/AuthProvider';
import { DocumentAdminPanel } from '../rag/DocumentAdminPanel';

type Metric = {
  term: string;
  definition: string;
  formula: string;
  owner: string;
  freshness_rule: string;
  active_version_id: string;
  version_count: number;
  cache_invalidated_at: string;
};

type MetricVersion = {
  version_id: string;
  term: string;
  definition: string;
  formula: string;
  owner: string;
  freshness_rule: string;
  changed_by: string;
  timestamp: string;
  previous_formula: string | null;
  action: string;
  rollback_reason: string | null;
};

type MetricDiffRow = {
  kind: 'added' | 'removed' | 'unchanged';
  value: string;
};

type Suggestion = {
  type: 'kpi' | 'template';
  label: string;
  uses?: number;
  template_id?: string;
};

type SavedTemplate = {
  template_id: string;
  name: string;
  query_intent: string;
  filters: string;
  time_range: string;
  output_format: string;
  created_at: string;
};

type HistoryEntry = {
  entry_id: string;
  created_at: string;
  intent_type: string;
  topic: string;
  filter_context: string;
  key_result_summary: string;
};

type MemoryViolation = {
  user_id: string;
  entry_type: string;
  field: string;
};

type MemoryContextBundle = {
  summaries: Array<{
    summary_id: string;
    topic: string;
    filter_context: string;
    summary_text: string;
    created_at: string;
  }>;
  token_budget_increase_percent: number;
  threshold: number;
};

const workspaceShell: React.CSSProperties = {
  minHeight: '100%',
  background:
    'linear-gradient(180deg, rgba(242,236,226,0.92) 0%, rgba(248,245,239,0.98) 22%, rgba(255,255,255,1) 100%)',
  color: 'var(--color-neutral-900)',
};

const heroGrid: React.CSSProperties = {
  display: 'grid',
  gap: 'var(--space-4)',
  gridTemplateColumns: '2fr 1fr',
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
};

const panelGrid: React.CSSProperties = {
  display: 'grid',
  gap: 'var(--space-4)',
  gridTemplateColumns: '1.3fr 1fr',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.8rem 0.95rem',
  borderRadius: '0.9rem',
  border: '1px solid rgba(117, 94, 60, 0.22)',
  background: 'rgba(255,255,255,0.92)',
  color: 'var(--color-neutral-900)',
  fontSize: '0.95rem',
};

const buttonStyle: React.CSSProperties = {
  border: 'none',
  borderRadius: '999px',
  padding: '0.8rem 1.1rem',
  background: 'linear-gradient(135deg, #0f766e 0%, #115e59 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

const ghostButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: 'rgba(15, 118, 110, 0.09)',
  color: '#115e59',
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function Epic5BWorkspace(): React.JSX.Element {
  const auth = useAuth();
  const roles = auth.session?.claims.roles ?? [];
  const canManageDocuments = roles.includes('admin') || roles.includes('data_owner');
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>('doanh thu thuần');
  const [versions, setVersions] = useState<MetricVersion[]>([]);
  const [diffRows, setDiffRows] = useState<MetricDiffRow[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [templates, setTemplates] = useState<SavedTemplate[]>([]);
  const [historyEntries, setHistoryEntries] = useState<HistoryEntry[]>([]);
  const [memoryAudit, setMemoryAudit] = useState<MemoryViolation[]>([]);
  const [memoryProbe, setMemoryProbe] = useState<MemoryContextBundle | null>(null);
  const [draftPrompt, setDraftPrompt] = useState('');
  const [historyKeyword, setHistoryKeyword] = useState('');
  const [historyTopic, setHistoryTopic] = useState('');
  const [contextQuery, setContextQuery] = useState('monthly revenue trend');
  const [semanticForm, setSemanticForm] = useState({
    term: 'doanh thu thuần',
    definition: 'Doanh thu sau điều chỉnh hoàn trả và giảm trừ',
    formula: 'SUM(NET_REVENUE) - SUM(RETURNS)',
    owner: 'Finance',
    freshness_rule: 'daily',
  });
  const [templateForm, setTemplateForm] = useState({
    name: 'Revenue Monthly',
    query_intent: 'revenue trend',
    filters: 'month filter',
    time_range: 'last_30_days',
    output_format: 'table',
  });
  const [rollbackReason, setRollbackReason] = useState('restore audited baseline');
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [semanticDenied, setSemanticDenied] = useState(false);
  const [loading, setLoading] = useState(true);

  const selectedMetricData = useMemo(
    () => metrics.find((metric) => metric.term === selectedMetric) ?? null,
    [metrics, selectedMetric],
  );

  async function loadMetrics(preferredTerm?: string): Promise<void> {
    try {
      const data = await apiRequest<{ metrics: Metric[] }>('/v1/admin/semantic-layer/metrics');
      setSemanticDenied(false);
      setMetrics(data.metrics);
      const nextTerm = preferredTerm ?? data.metrics[0]?.term ?? selectedMetric;
      setSelectedMetric(nextTerm);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : 'Không tải được semantic metrics';
      if (message.toLowerCase().includes('admin') || message.includes('403')) {
        setSemanticDenied(true);
        setMetrics([]);
        setVersions([]);
        setDiffRows([]);
        return;
      }
      throw loadError;
    }
  }

  async function loadVersions(term: string): Promise<void> {
    const data = await apiRequest<{ versions: MetricVersion[] }>(
      `/v1/admin/semantic-layer/metrics/${encodeURIComponent(term)}/versions`,
    );
    setVersions(data.versions);
    if (data.versions.length >= 2) {
      const newest = data.versions[data.versions.length - 1];
      const previous = data.versions[data.versions.length - 2];
      const diff = await apiRequest<{ diff: MetricDiffRow[] }>(
        `/v1/admin/semantic-layer/metrics/${encodeURIComponent(term)}/diff?from_version_id=${encodeURIComponent(previous.version_id)}&to_version_id=${encodeURIComponent(newest.version_id)}`,
      );
      setDiffRows(diff.diff);
    } else {
      setDiffRows([]);
    }
  }

  async function loadMemorySurfaces(): Promise<void> {
    const [suggestionData, templateData, auditData] = await Promise.all([
      apiRequest<{ suggestions: Suggestion[] }>('/v1/chat/suggestions'),
      apiRequest<{ templates: SavedTemplate[] }>('/v1/chat/templates'),
      apiRequest<{ violations: MemoryViolation[] }>('/v1/chat/history/audit'),
    ]);
    setSuggestions(suggestionData.suggestions);
    setTemplates(templateData.templates);
    setMemoryAudit(auditData.violations);
  }

  async function loadInitial(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadMetrics(), loadMemorySurfaces()]);
      await loadHistory();
      await probeContext(contextQuery);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Không tải được workspace 5B');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const hasSelectedMetric = metrics.some((metric) => metric.term === selectedMetric);
    if (selectedMetric && !semanticDenied && hasSelectedMetric) {
      void loadVersions(selectedMetric).catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : 'Không tải được lịch sử KPI');
      });
    }
  }, [metrics, selectedMetric, semanticDenied]);

  async function loadHistory(): Promise<void> {
    const params = new URLSearchParams();
    if (historyKeyword.trim()) {
      params.set('keyword', historyKeyword.trim());
    }
    if (historyTopic.trim()) {
      params.set('topic', historyTopic.trim());
    }
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const data = await apiRequest<{ results: HistoryEntry[] }>(`/v1/chat/history/search${suffix}`);
    setHistoryEntries(data.results);
  }

  async function probeContext(query: string): Promise<void> {
    const data = await apiRequest<MemoryContextBundle>(
      `/v1/chat/memory/context?query=${encodeURIComponent(query)}`,
    );
    setMemoryProbe(data);
  }

  async function handlePublish(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (semanticDenied) {
      setError('Bạn cần quyền data_owner hoặc admin để publish KPI.');
      return;
    }
    setError(null);
    try {
      await apiRequest<{ version: MetricVersion }>('/v1/admin/semantic-layer/metrics/publish', {
        method: 'POST',
        body: JSON.stringify(semanticForm),
      });
      setFlash(`Đã publish KPI ${semanticForm.term}`);
      await loadMetrics(semanticForm.term);
      await loadVersions(semanticForm.term);
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Publish thất bại');
    }
  }

  async function handleRollback(versionId: string): Promise<void> {
    if (semanticDenied) {
      setError('Bạn cần quyền data_owner hoặc admin để rollback KPI.');
      return;
    }
    setError(null);
    try {
      await apiRequest<{ version: MetricVersion }>(
        `/v1/admin/semantic-layer/metrics/${encodeURIComponent(selectedMetric)}/rollback`,
        {
          method: 'POST',
          body: JSON.stringify({ version_id: versionId, reason: rollbackReason }),
        },
      );
      setFlash(`Đã rollback ${selectedMetric}`);
      await loadMetrics(selectedMetric);
      await loadVersions(selectedMetric);
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Rollback thất bại');
    }
  }

  async function handleSaveTemplate(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest<{ template: SavedTemplate }>('/v1/chat/templates', {
        method: 'POST',
        body: JSON.stringify(templateForm),
      });
      setFlash(`Đã lưu mẫu ${templateForm.name}`);
      await loadMemorySurfaces();
    } catch (templateError) {
      setError(templateError instanceof Error ? templateError.message : 'Lưu mẫu thất bại');
    }
  }

  async function handleReuse(entryId: string): Promise<void> {
    setError(null);
    try {
      const data = await apiRequest<{ preload: { topic: string; filters: string; intent_type: string } }>(
        `/v1/chat/history/${encodeURIComponent(entryId)}/reuse`,
        { method: 'POST' },
      );
      setDraftPrompt(`${data.preload.topic} | ${data.preload.filters}`);
      setFlash('Đã nạp lại intent vào khung soạn thảo');
    } catch (reuseError) {
      setError(reuseError instanceof Error ? reuseError.message : 'Không dùng lại được truy vấn');
    }
  }

  if (loading) {
    return (
      <section style={{ ...workspaceShell, padding: '2rem 2.4rem' }}>
        <div style={{ ...cardStyle, padding: '1.4rem 1.6rem' }}>Đang dựng workspace 5B...</div>
      </section>
    );
  }

  return (
    <section style={{ ...workspaceShell, padding: '2rem 2.4rem 3rem' }}>
      <div style={heroGrid}>
        <div style={{ ...cardStyle, padding: '1.6rem 1.8rem', position: 'relative', overflow: 'hidden' }}>
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 'auto -4rem -4rem auto',
              width: '12rem',
              height: '12rem',
              borderRadius: '999px',
              background: 'radial-gradient(circle, rgba(15,118,110,0.18) 0%, rgba(15,118,110,0) 68%)',
            }}
          />
          <p style={{ margin: 0, color: '#0f766e', fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Epic 5B Workspace
          </p>
          <h1 style={{ margin: '0.5rem 0 0.75rem', fontSize: '2.2rem', lineHeight: 1.04 }}>
            Semantic governance, memory recall, và conversation reuse trong một màn hình.
          </h1>
          <p style={{ margin: 0, maxWidth: '48rem', color: 'var(--color-neutral-600)', lineHeight: 1.7 }}>
            Workspace này nối trực tiếp vào API `5B`: publish KPI versions, xem diff và rollback, kiểm tra memory recall threshold,
            quản lý templates, suggestions, và tìm lại lịch sử phân tích mà không kéo raw Oracle values vào client state.
          </p>
        </div>

        <aside style={{ ...cardStyle, padding: '1.4rem 1.5rem', display: 'grid', gap: '0.9rem' }}>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>KPI active</div>
            <div style={{ marginTop: '0.2rem', fontWeight: 700, fontSize: '1.05rem' }}>{selectedMetricData?.term ?? 'Chưa có metric'}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Version count</div>
            <div style={{ marginTop: '0.2rem', fontWeight: 700, fontSize: '1.05rem' }}>{selectedMetricData?.version_count ?? 0}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Recall threshold</div>
            <div style={{ marginTop: '0.2rem', fontWeight: 700, fontSize: '1.05rem' }}>{memoryProbe?.threshold ?? 0.7}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Self audit</div>
            <div style={{ marginTop: '0.2rem', fontWeight: 700, fontSize: '1.05rem' }}>{memoryAudit.length === 0 ? 'Clean' : `${memoryAudit.length} violations`}</div>
          </div>
        </aside>
      </div>

      {(flash || error) && (
        <div
          role={error ? 'alert' : 'status'}
          style={{
            marginTop: '1rem',
            ...cardStyle,
            padding: '0.95rem 1.15rem',
            borderColor: error ? 'rgba(185, 28, 28, 0.22)' : 'rgba(15, 118, 110, 0.2)',
            color: error ? '#991b1b' : '#115e59',
          }}
        >
          {error ?? flash}
        </div>
      )}

      <div style={{ marginTop: '1.4rem' }}>
        <ChatAssistantConsole />
      </div>

      {canManageDocuments ? (
        <div style={{ marginTop: '1.4rem' }}>
          <DocumentAdminPanel />
        </div>
      ) : null}

      <div style={{ marginTop: '1.4rem' }}>
        <ForecastStudio />
      </div>

      <div style={{ marginTop: '1.4rem' }}>
        <AnomalyAlertsPanel />
      </div>

      <div style={{ marginTop: '1.4rem' }}>
        <TrendAnalysisPanel />
      </div>

      <div style={{ marginTop: '1.4rem' }}>
        <DrilldownExplainabilityPanel />
      </div>

      <div id="semantic-studio" style={{ ...panelGrid, marginTop: '1.4rem' }}>
        <section style={{ ...cardStyle, padding: '1.35rem 1.35rem 1.2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Semantic Studio</h2>
              <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
                Publish metric versions, inspect immutable history, và rollback có audit reason.
              </p>
            </div>
            <select
              value={selectedMetric}
              onChange={(event) => setSelectedMetric(event.target.value)}
              style={{ ...inputStyle, width: '14rem' }}
              aria-label="Chọn KPI"
            >
              {metrics.map((metric) => (
                <option key={metric.term} value={metric.term}>{metric.term}</option>
              ))}
            </select>
          </div>

          {semanticDenied ? (
            <div
              role="status"
              style={{
                borderRadius: '1rem',
                background: 'rgba(180, 83, 9, 0.12)',
                color: '#92400e',
                padding: '1rem 1.05rem',
                marginBottom: '1rem',
              }}
            >
              Semantic governance hiện yêu cầu quyền <strong>data_owner</strong> hoặc <strong>admin</strong>.
              Bạn vẫn có thể dùng Memory Studio và History Studio ở cùng workspace này.
            </div>
          ) : null}

          <form onSubmit={(event) => void handlePublish(event)} style={{ display: 'grid', gap: '0.9rem' }}>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input
                value={semanticForm.term}
                onChange={(event) => setSemanticForm((current) => ({ ...current, term: event.target.value }))}
                style={inputStyle}
                placeholder="Tên KPI"
                disabled={semanticDenied}
              />
              <input
                value={semanticForm.owner}
                onChange={(event) => setSemanticForm((current) => ({ ...current, owner: event.target.value }))}
                style={inputStyle}
                placeholder="Owner"
                disabled={semanticDenied}
              />
            </div>
            <textarea
              value={semanticForm.definition}
              onChange={(event) => setSemanticForm((current) => ({ ...current, definition: event.target.value }))}
              style={{ ...inputStyle, minHeight: '5.5rem', resize: 'vertical' }}
              placeholder="Diễn giải business"
              disabled={semanticDenied}
            />
            <textarea
              value={semanticForm.formula}
              onChange={(event) => setSemanticForm((current) => ({ ...current, formula: event.target.value }))}
              style={{ ...inputStyle, minHeight: '5.5rem', resize: 'vertical', fontFamily: 'ui-monospace, SFMono-Regular, monospace' }}
              placeholder="Công thức KPI"
              disabled={semanticDenied}
            />
            <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
              <input
                value={semanticForm.freshness_rule}
                onChange={(event) => setSemanticForm((current) => ({ ...current, freshness_rule: event.target.value }))}
                style={{ ...inputStyle, maxWidth: '10rem' }}
                placeholder="daily"
                disabled={semanticDenied}
              />
              <button type="submit" style={buttonStyle} disabled={semanticDenied}>Publish Version</button>
            </div>
          </form>

          <div style={{ marginTop: '1.25rem', display: 'grid', gap: '0.8rem' }}>
            {!semanticDenied && versions.length === 0 ? (
              <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.9)', padding: '1rem', color: 'var(--color-neutral-500)' }}>
                Chưa có version history cho KPI này.
              </div>
            ) : null}
            {versions.map((version) => {
              const isActive = version.version_id === selectedMetricData?.active_version_id;
              return (
                <article
                  key={version.version_id}
                  style={{
                    border: '1px solid rgba(117, 94, 60, 0.16)',
                    borderRadius: '1rem',
                    padding: '0.95rem 1rem',
                    background: isActive ? 'rgba(15,118,110,0.07)' : 'rgba(255,255,255,0.78)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 700 }}>{version.action === 'rollback' ? 'Rollback snapshot' : 'Published snapshot'}</div>
                      <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                        {version.changed_by} · {formatDate(version.timestamp)}
                      </div>
                    </div>
                    {!isActive && !semanticDenied && (
                      <button type="button" style={ghostButtonStyle} onClick={() => void handleRollback(version.version_id)}>
                        Rollback
                      </button>
                    )}
                  </div>
                  <pre
                    style={{
                      margin: '0.8rem 0 0',
                      padding: '0.9rem',
                      borderRadius: '0.9rem',
                      background: 'rgba(26, 31, 44, 0.94)',
                      color: '#d7f9f1',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {version.formula}
                  </pre>
                </article>
              );
            })}
          </div>
        </section>

        <aside style={{ ...cardStyle, padding: '1.35rem 1.35rem 1.2rem', display: 'grid', gap: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Diff view</h3>
            <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
              Side-by-side formula diff với added/removed token nổi bật để review nhanh trước khi rollback.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.7rem', alignItems: 'center' }}>
            <input
              value={rollbackReason}
              onChange={(event) => setRollbackReason(event.target.value)}
              style={inputStyle}
              placeholder="Rollback reason"
            />
          </div>
          <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.9)', padding: '1rem', minHeight: '16rem' }}>
            {diffRows.length === 0 ? (
              <p style={{ margin: 0, color: 'var(--color-neutral-500)' }}>Chưa đủ version để tạo diff.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                {diffRows.map((row, index) => (
                  <span
                    key={`${row.kind}-${row.value}-${index}`}
                    style={{
                      borderRadius: '999px',
                      padding: '0.35rem 0.65rem',
                      background:
                        row.kind === 'added'
                          ? 'rgba(22, 163, 74, 0.14)'
                          : row.kind === 'removed'
                            ? 'rgba(220, 38, 38, 0.14)'
                            : 'rgba(99, 74, 45, 0.08)',
                      color:
                        row.kind === 'added'
                          ? '#166534'
                          : row.kind === 'removed'
                            ? '#991b1b'
                            : 'var(--color-neutral-700)',
                    }}
                  >
                    {row.kind === 'added' ? '+' : row.kind === 'removed' ? '-' : '·'} {row.value}
                  </span>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>

      <div id="memory-studio" style={{ ...panelGrid, marginTop: '1.4rem' }}>
        <section style={{ ...cardStyle, padding: '1.35rem 1.35rem 1.2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Memory Studio</h2>
              <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
                Kiểm tra selective recall, top suggestions, saved templates, và self-audit cho memory hygiene.
              </p>
            </div>
            <button type="button" style={ghostButtonStyle} onClick={() => void loadMemorySurfaces()}>
              Refresh
            </button>
          </div>

          <div style={{ marginTop: '1rem', display: 'grid', gap: '0.9rem', gridTemplateColumns: '1.1fr 0.9fr' }}>
            <div style={{ borderRadius: '1rem', padding: '1rem', background: 'rgba(246,241,232,0.8)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.8rem' }}>
                <h3 style={{ margin: 0 }}>Context probe</h3>
                <button type="button" style={ghostButtonStyle} onClick={() => void probeContext(contextQuery)}>Probe</button>
              </div>
              <input
                value={contextQuery}
                onChange={(event) => setContextQuery(event.target.value)}
                style={{ ...inputStyle, marginTop: '0.8rem' }}
                placeholder="monthly revenue trend"
              />
              <div style={{ marginTop: '0.9rem', color: 'var(--color-neutral-600)' }}>
                Token delta: <strong>{memoryProbe?.token_budget_increase_percent ?? 0}%</strong>
              </div>
              <div style={{ marginTop: '0.9rem', display: 'grid', gap: '0.7rem' }}>
                {(memoryProbe?.summaries ?? []).map((summary) => (
                  <article key={summary.summary_id} style={{ borderRadius: '0.9rem', background: 'white', padding: '0.8rem 0.9rem' }}>
                    <div style={{ fontWeight: 700 }}>{summary.topic}</div>
                    <div style={{ marginTop: '0.2rem', color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>{summary.filter_context}</div>
                    <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)' }}>{summary.summary_text}</p>
                  </article>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gap: '0.9rem' }}>
              <div style={{ borderRadius: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.78)', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
                <h3 style={{ margin: 0 }}>Suggestions</h3>
                <div style={{ marginTop: '0.8rem', display: 'grid', gap: '0.6rem' }}>
                  {suggestions.map((suggestion) => (
                    <div key={`${suggestion.type}-${suggestion.label}`} style={{ borderRadius: '0.85rem', padding: '0.75rem 0.85rem', background: 'rgba(15,118,110,0.08)' }}>
                      <div style={{ fontWeight: 700 }}>{suggestion.label}</div>
                      <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.86rem' }}>
                        {suggestion.type === 'kpi' ? `${suggestion.uses ?? 0} lần dùng` : 'Saved template'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ borderRadius: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.78)', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
                <h3 style={{ margin: 0 }}>Memory self-audit</h3>
                <div style={{ marginTop: '0.8rem', color: memoryAudit.length === 0 ? '#166534' : '#991b1b' }}>
                  {memoryAudit.length === 0 ? 'Không có raw-value violation cho user hiện tại.' : `${memoryAudit.length} violation`}
                </div>
              </div>
            </div>
          </div>

          <form onSubmit={(event) => void handleSaveTemplate(event)} style={{ marginTop: '1rem', display: 'grid', gap: '0.8rem' }}>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input
                value={templateForm.name}
                onChange={(event) => setTemplateForm((current) => ({ ...current, name: event.target.value }))}
                style={inputStyle}
                placeholder="Template name"
              />
              <input
                value={templateForm.output_format}
                onChange={(event) => setTemplateForm((current) => ({ ...current, output_format: event.target.value }))}
                style={inputStyle}
                placeholder="Output format"
              />
            </div>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input
                value={templateForm.query_intent}
                onChange={(event) => setTemplateForm((current) => ({ ...current, query_intent: event.target.value }))}
                style={inputStyle}
                placeholder="Query intent"
              />
              <input
                value={templateForm.time_range}
                onChange={(event) => setTemplateForm((current) => ({ ...current, time_range: event.target.value }))}
                style={inputStyle}
                placeholder="Time range"
              />
            </div>
            <textarea
              value={templateForm.filters}
              onChange={(event) => setTemplateForm((current) => ({ ...current, filters: event.target.value }))}
              style={{ ...inputStyle, minHeight: '4.5rem', resize: 'vertical' }}
              placeholder="Filters"
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
              <button type="submit" style={buttonStyle}>Save Template</button>
              <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                Templates được giữ private theo user và không chứa raw Oracle values.
              </div>
            </div>
          </form>
        </section>

        <aside style={{ ...cardStyle, padding: '1.35rem 1.35rem 1.2rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Saved templates</h3>
          <div style={{ marginTop: '0.8rem', display: 'grid', gap: '0.8rem' }}>
            {templates.map((template) => (
              <article key={template.template_id} style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '0.9rem 1rem' }}>
                <div style={{ fontWeight: 700 }}>{template.name}</div>
                <div style={{ marginTop: '0.2rem', color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                  {template.query_intent} · {template.time_range}
                </div>
                <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)' }}>{template.filters}</p>
              </article>
            ))}
          </div>
        </aside>
      </div>

      <div id="history-studio" style={{ ...cardStyle, padding: '1.35rem 1.35rem 1.2rem', marginTop: '1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Conversation History</h2>
            <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
              Tìm lại phân tích cũ theo keyword hoặc topic, rồi preload intent metadata vào khung soạn thảo mới.
            </p>
          </div>
          <button type="button" style={ghostButtonStyle} onClick={() => void loadHistory()}>
            Search
          </button>
        </div>

        <div style={{ marginTop: '1rem', display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr auto' }}>
          <input
            value={historyKeyword}
            onChange={(event) => setHistoryKeyword(event.target.value)}
            style={inputStyle}
            placeholder="Keyword"
          />
          <input
            value={historyTopic}
            onChange={(event) => setHistoryTopic(event.target.value)}
            style={inputStyle}
            placeholder="Topic"
          />
          <button type="button" style={buttonStyle} onClick={() => void loadHistory()}>
            Run search
          </button>
        </div>

        <div style={{ marginTop: '1rem', display: 'grid', gap: '0.85rem' }}>
          {historyEntries.map((entry) => (
            <article
              key={entry.entry_id}
              style={{
                borderRadius: '1rem',
                border: '1px solid rgba(117, 94, 60, 0.14)',
                background: 'rgba(255,255,255,0.74)',
                padding: '0.95rem 1rem',
                display: 'grid',
                gap: '0.45rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{entry.topic}</div>
                  <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                    {entry.intent_type} · {formatDate(entry.created_at)}
                  </div>
                </div>
                <button type="button" style={ghostButtonStyle} onClick={() => void handleReuse(entry.entry_id)}>
                  Dùng lại
                </button>
              </div>
              <div style={{ color: 'var(--color-neutral-600)' }}>{entry.filter_context}</div>
              <div style={{ color: 'var(--color-neutral-800)' }}>{entry.key_result_summary}</div>
            </article>
          ))}
        </div>

        <div style={{ marginTop: '1rem', borderRadius: '1rem', background: 'rgba(26,31,44,0.95)', color: '#d7f9f1', padding: '1rem 1.1rem' }}>
          <div style={{ fontWeight: 700, marginBottom: '0.4rem' }}>Preloaded draft</div>
          <div style={{ whiteSpace: 'pre-wrap', minHeight: '2.5rem' }}>{draftPrompt || 'Chưa có intent nào được nạp lại.'}</div>
        </div>
      </div>
    </section>
  );
}
