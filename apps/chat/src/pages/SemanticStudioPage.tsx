import { FormEvent, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';
import { buttonStyle, cardStyle, ghostButtonStyle, inputStyle, pageShell, pageTitle } from '../styles/shared';

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

type MetricDiffRow = { kind: 'added' | 'removed' | 'unchanged'; value: string };

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
}

export function SemanticStudioPage(): React.JSX.Element {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [selectedMetric, setSelectedMetric] = useState('');
  const [versions, setVersions] = useState<MetricVersion[]>([]);
  const [diffRows, setDiffRows] = useState<MetricDiffRow[]>([]);
  const [rollbackReason, setRollbackReason] = useState('restore audited baseline');
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    term: 'doanh thu thuan',
    definition: 'Doanh thu sau dieu chinh hoan tra va giam tru',
    formula: 'SUM(NET_REVENUE) - SUM(RETURNS)',
    owner: 'Finance',
    freshness_rule: 'daily',
  });

  const selectedMetricData = useMemo(
    () => metrics.find((metric) => metric.term === selectedMetric) ?? null,
    [metrics, selectedMetric],
  );

  async function loadMetrics(preferredTerm?: string): Promise<void> {
    const data = await apiRequest<{ metrics: Metric[] }>('/v1/admin/semantic-layer/metrics');
    setMetrics(data.metrics);
    setSelectedMetric(preferredTerm ?? data.metrics[0]?.term ?? '');
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

  async function handlePublish(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest<{ version: MetricVersion }>('/v1/admin/semantic-layer/metrics/publish', {
        method: 'POST',
        body: JSON.stringify(form),
      });
      setFlash(`Da publish KPI ${form.term}`);
      await loadMetrics(form.term);
      await loadVersions(form.term);
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Publish that bai');
    }
  }

  async function handleRollback(versionId: string): Promise<void> {
    if (!selectedMetric) return;
    setError(null);
    try {
      await apiRequest<{ version: MetricVersion }>(
        `/v1/admin/semantic-layer/metrics/${encodeURIComponent(selectedMetric)}/rollback`,
        {
          method: 'POST',
          body: JSON.stringify({ version_id: versionId, reason: rollbackReason }),
        },
      );
      setFlash(`Da rollback ${selectedMetric}`);
      await loadMetrics(selectedMetric);
      await loadVersions(selectedMetric);
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Rollback that bai');
    }
  }

  useEffect(() => {
    void loadMetrics().catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Khong tai duoc semantic metrics');
    });
  }, []);

  useEffect(() => {
    if (selectedMetric) {
      void loadVersions(selectedMetric).catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : 'Khong tai duoc lich su KPI');
      });
    }
  }, [selectedMetric]);

  return (
    <section style={pageShell}>
      <h1 style={pageTitle}>Semantic Studio</h1>
      <p style={{ margin: '0.45rem 0 1.2rem', color: 'var(--color-neutral-600)' }}>
        Publish KPI versions, xem diff cong thuc va rollback co audit reason.
      </p>
      {(flash || error) && (
        <div role={error ? 'alert' : 'status'} style={{ ...cardStyle, padding: '0.9rem 1rem', marginBottom: '1rem', color: error ? '#991b1b' : '#115e59' }}>
          {error ?? flash}
        </div>
      )}
      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: '1.25fr 0.85fr' }}>
        <section style={{ ...cardStyle, padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Metric versions</h2>
              <p style={{ color: 'var(--color-neutral-600)' }}>Active: {selectedMetricData?.term ?? 'chua co metric'}</p>
            </div>
            <select value={selectedMetric} onChange={(event) => setSelectedMetric(event.target.value)} style={{ ...inputStyle, width: '15rem' }}>
              {metrics.map((metric) => <option key={metric.term} value={metric.term}>{metric.term}</option>)}
            </select>
          </div>
          <form onSubmit={(event) => void handlePublish(event)} style={{ display: 'grid', gap: '0.8rem', marginTop: '1rem' }}>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input value={form.term} onChange={(event) => setForm((current) => ({ ...current, term: event.target.value }))} style={inputStyle} placeholder="Ten KPI" />
              <input value={form.owner} onChange={(event) => setForm((current) => ({ ...current, owner: event.target.value }))} style={inputStyle} placeholder="Owner" />
            </div>
            <textarea value={form.definition} onChange={(event) => setForm((current) => ({ ...current, definition: event.target.value }))} style={{ ...inputStyle, minHeight: '5rem' }} placeholder="Dien giai business" />
            <textarea value={form.formula} onChange={(event) => setForm((current) => ({ ...current, formula: event.target.value }))} style={{ ...inputStyle, minHeight: '5rem', fontFamily: 'ui-monospace, SFMono-Regular, monospace' }} placeholder="Cong thuc KPI" />
            <div style={{ display: 'flex', gap: '0.8rem' }}>
              <input value={form.freshness_rule} onChange={(event) => setForm((current) => ({ ...current, freshness_rule: event.target.value }))} style={{ ...inputStyle, maxWidth: '10rem' }} placeholder="daily" />
              <button type="submit" style={buttonStyle}>Publish Version</button>
            </div>
          </form>
          <div style={{ marginTop: '1.2rem', display: 'grid', gap: '0.8rem' }}>
            {versions.map((version) => {
              const isActive = version.version_id === selectedMetricData?.active_version_id;
              return (
                <article key={version.version_id} style={{ border: '1px solid rgba(117, 94, 60, 0.16)', borderRadius: '1rem', padding: '0.95rem', background: isActive ? 'rgba(15,118,110,0.07)' : 'rgba(255,255,255,0.78)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                    <div>
                      <strong>{version.action === 'rollback' ? 'Rollback snapshot' : 'Published snapshot'}</strong>
                      <div style={{ color: 'var(--color-neutral-500)' }}>{version.changed_by} - {formatDate(version.timestamp)}</div>
                    </div>
                    {!isActive && <button type="button" style={ghostButtonStyle} onClick={() => void handleRollback(version.version_id)}>Rollback</button>}
                  </div>
                  <pre style={{ margin: '0.8rem 0 0', padding: '0.9rem', borderRadius: '0.9rem', background: 'rgba(26,31,44,0.94)', color: '#d7f9f1', whiteSpace: 'pre-wrap' }}>
                    {version.formula}
                  </pre>
                </article>
              );
            })}
          </div>
        </section>
        <aside style={{ ...cardStyle, padding: '1.25rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Diff view</h2>
          <input value={rollbackReason} onChange={(event) => setRollbackReason(event.target.value)} style={{ ...inputStyle, marginTop: '1rem' }} placeholder="Rollback reason" />
          <div style={{ marginTop: '1rem', borderRadius: '1rem', background: 'rgba(246,241,232,0.9)', padding: '1rem', minHeight: '16rem' }}>
            {diffRows.length === 0 ? (
              <p style={{ margin: 0, color: 'var(--color-neutral-500)' }}>Chua du version de tao diff.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                {diffRows.map((row, index) => (
                  <span key={`${row.kind}-${row.value}-${index}`} style={{ borderRadius: '999px', padding: '0.35rem 0.65rem', background: row.kind === 'added' ? 'rgba(22,163,74,0.14)' : row.kind === 'removed' ? 'rgba(220,38,38,0.14)' : 'rgba(99,74,45,0.08)', color: row.kind === 'added' ? '#166534' : row.kind === 'removed' ? '#991b1b' : 'var(--color-neutral-700)' }}>
                    {row.kind === 'added' ? '+' : row.kind === 'removed' ? '-' : '.'} {row.value}
                  </span>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
