import { FormEvent, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';
import { buttonStyle, cardStyle, ghostButtonStyle, inputStyle, pageShell, pageTitle } from '../styles/shared';

type Metric = {
  term: string;
  definition: string;
  formula: string;
  owner: string;
  freshness_rule: string;
  aliases: string[];
  aggregation: string | null;
  grain: string | null;
  unit: string | null;
  dimensions: string[];
  source: Record<string, unknown> | null;
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
  aliases: string[];
  aggregation: string | null;
  grain: string | null;
  unit: string | null;
  dimensions: string[];
  source: Record<string, unknown> | null;
  changed_by: string;
  timestamp: string;
  previous_formula: string | null;
  action: string;
  rollback_reason: string | null;
};

type MetricDiffRow = { kind: 'added' | 'removed' | 'unchanged'; value: string };

type ImportSemanticMetric = {
  term: string;
  aliases?: string[];
  definition: string;
  formula: string;
  aggregation?: string | null;
  owner: string;
  freshness_rule: string;
  grain?: string | null;
  unit?: string | null;
  dimensions?: string[];
  source?: Record<string, unknown> | null;
  joins?: Array<Record<string, string>>;
  certified_filters?: string[];
  security?: Record<string, object> | null;
};

type ConfigCatalogImportPayload = {
  catalog_version: string;
  data_sources?: Array<Record<string, unknown>>;
  semantic_metrics: ImportSemanticMetric[];
  role_mappings?: Array<Record<string, unknown>>;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
}

const emptyForm = {
  term: '',
  definition: '',
  formula: '',
  owner: '',
  freshness_rule: '',
  aliases: '',
  aggregation: '',
  grain: '',
  unit: '',
  dimensions: '',
  source_data_source: '',
  source_schema: '',
  source_table: '',
};

const importExample = JSON.stringify(
  {
    semantic_metrics: [
      {
        term: 'doanh thu thuần',
        aliases: ['doanh thu', 'net revenue', 'doanh thu ròng'],
        definition: 'Tổng doanh thu sau hoàn trả theo view SYSTEM.AIAL_SALES_DAILY_V.',
        formula: 'SUM(NET_REVENUE)',
        owner: 'Sales',
        freshness_rule: 'daily',
        aggregation: 'sum',
        grain: 'daily_product_region_channel',
        unit: 'VND',
        dimensions: ['PERIOD_DATE', 'REGION_CODE', 'CHANNEL_CODE', 'PRODUCT_CODE', 'CATEGORY_NAME'],
        source: { data_source: 'oracle-free-system', schema: 'SYSTEM', table: 'AIAL_SALES_DAILY_V' },
      },
    ],
  },
  null,
  2,
);

function todayCatalogVersion(): string {
  return new Date().toISOString().slice(0, 10);
}

function normalizeImportPayload(raw: unknown): ConfigCatalogImportPayload {
  if (Array.isArray(raw)) {
    return { catalog_version: todayCatalogVersion(), semantic_metrics: raw as ImportSemanticMetric[] };
  }
  if (!raw || typeof raw !== 'object') {
    throw new Error('JSON import phải là object hoặc array.');
  }
  const value = raw as Record<string, unknown>;
  if ('term' in value) {
    return { catalog_version: todayCatalogVersion(), semantic_metrics: [value as ImportSemanticMetric] };
  }
  const semanticMetrics = value.semantic_metrics;
  if (!Array.isArray(semanticMetrics)) {
    throw new Error('Thiếu semantic_metrics. Có thể dán một item, một array item, hoặc full config catalog.');
  }
  return {
    catalog_version: typeof value.catalog_version === 'string' ? value.catalog_version : todayCatalogVersion(),
    data_sources: Array.isArray(value.data_sources) ? (value.data_sources as Array<Record<string, unknown>>) : [],
    semantic_metrics: semanticMetrics as ImportSemanticMetric[],
    role_mappings: Array.isArray(value.role_mappings) ? (value.role_mappings as Array<Record<string, unknown>>) : [],
  };
}

function splitList(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function sourceFromForm(form: typeof emptyForm): Record<string, unknown> | null {
  if (!form.source_table.trim()) return null;
  return {
    data_source: form.source_data_source.trim(),
    schema: form.source_schema.trim(),
    table: form.source_table.trim(),
  };
}

export function SemanticStudioPage(): React.JSX.Element {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [selectedMetric, setSelectedMetric] = useState('');
  const [versions, setVersions] = useState<MetricVersion[]>([]);
  const [diffRows, setDiffRows] = useState<MetricDiffRow[]>([]);
  const [rollbackReason, setRollbackReason] = useState('Khôi phục baseline đã audit');
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [importJson, setImportJson] = useState(importExample);

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
        body: JSON.stringify({
          term: form.term,
          definition: form.definition,
          formula: form.formula,
          owner: form.owner,
          freshness_rule: form.freshness_rule,
          aliases: splitList(form.aliases),
          aggregation: form.aggregation || null,
          grain: form.grain || null,
          unit: form.unit || null,
          dimensions: splitList(form.dimensions),
          source: sourceFromForm(form),
        }),
      });
      setFlash(`Đã publish semantic item ${form.term}`);
      setForm(emptyForm);
      await loadMetrics(form.term);
      await loadVersions(form.term);
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Publish thất bại');
    }
  }

  function handleEdit(metric: Metric): void {
    setSelectedMetric(metric.term);
    setForm({
      term: metric.term,
      definition: metric.definition,
      formula: metric.formula,
      owner: metric.owner,
      freshness_rule: metric.freshness_rule,
      aliases: (metric.aliases ?? []).join(', '),
      aggregation: metric.aggregation ?? '',
      grain: metric.grain ?? '',
      unit: metric.unit ?? '',
      dimensions: (metric.dimensions ?? []).join(', '),
      source_data_source: String(metric.source?.data_source ?? ''),
      source_schema: String(metric.source?.schema ?? ''),
      source_table: String(metric.source?.table ?? ''),
    });
  }

  async function handleDelete(metric: Metric): Promise<void> {
    setError(null);
    try {
      await apiRequest<{ version: MetricVersion }>(`/v1/admin/semantic-layer/metrics/${encodeURIComponent(metric.term)}`, {
        method: 'DELETE',
        body: JSON.stringify({ reason: 'Xóa semantic item từ giao diện quản trị' }),
      });
      setFlash(`Đã xóa semantic item ${metric.term}`);
      setForm(emptyForm);
      await loadMetrics();
      if (selectedMetric === metric.term) {
        setSelectedMetric('');
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Xóa semantic thất bại');
    }
  }

  async function handleImport(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const payload = normalizeImportPayload(JSON.parse(importJson));
      const data = await apiRequest<{ imported: { semantic_metrics: MetricVersion[] } }>('/v1/admin/config-catalog/import', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      const importedCount = data.imported.semantic_metrics.length;
      const firstTerm = data.imported.semantic_metrics[0]?.term;
      setFlash(`Đã import ${importedCount} semantic item`);
      await loadMetrics(firstTerm);
      if (firstTerm) {
        await loadVersions(firstTerm);
      }
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : 'Import thất bại');
    }
  }

  async function handleImportSampleCatalog(): Promise<void> {
    setError(null);
    try {
      const template = await apiRequest<ConfigCatalogImportPayload>('/v1/admin/config-catalog/template');
      const payload: ConfigCatalogImportPayload = {
        catalog_version: template.catalog_version || todayCatalogVersion(),
        semantic_metrics: template.semantic_metrics,
      };
      setImportJson(JSON.stringify(payload, null, 2));
      const data = await apiRequest<{ imported: { semantic_metrics: MetricVersion[] } }>('/v1/admin/config-catalog/import', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      const importedCount = data.imported.semantic_metrics.length;
      const firstTerm = data.imported.semantic_metrics[0]?.term;
      setFlash(`Đã nạp ${importedCount} semantic mẫu từ docs/sql`);
      await loadMetrics(firstTerm);
      if (firstTerm) {
        await loadVersions(firstTerm);
      }
    } catch (sampleError) {
      setError(sampleError instanceof Error ? sampleError.message : 'Nạp semantic mẫu thất bại');
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
      setFlash(`Đã rollback ${selectedMetric}`);
      await loadMetrics(selectedMetric);
      await loadVersions(selectedMetric);
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Rollback thất bại');
    }
  }

  useEffect(() => {
    void loadMetrics().catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Không tải được semantic items');
    });
  }, []);

  useEffect(() => {
    if (selectedMetric) {
      void loadVersions(selectedMetric).catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : 'Không tải được lịch sử semantic item');
      });
    } else {
      setVersions([]);
      setDiffRows([]);
    }
  }, [selectedMetric]);

  return (
    <section style={pageShell}>
      <h1 style={pageTitle}>Semantic Studio</h1>
      <p style={{ margin: '0.45rem 0 1.2rem', color: 'var(--color-neutral-600)' }}>
        Publish chỉ số, thuật ngữ nghiệp vụ, nội quy hoặc tri thức có kiểm soát; xem diff và rollback có audit reason.
      </p>
      {(flash || error) && (
        <div role={error ? 'alert' : 'status'} style={{ ...cardStyle, padding: '0.9rem 1rem', marginBottom: '1rem', color: error ? '#991b1b' : '#115e59' }}>
          {error ?? flash}
        </div>
      )}
      <section style={{ ...cardStyle, padding: '1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '0.8rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Danh sách semantic</h2>
            <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)' }}>
              Các semantic item đang active, dùng để phân quyền vai trò và sinh SQL từ nguồn DB.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button type="button" style={ghostButtonStyle} onClick={() => void handleImportSampleCatalog()}>Nạp semantic mẫu từ docs/sql</button>
            <button type="button" style={ghostButtonStyle} onClick={() => void loadMetrics(selectedMetric)}>Refresh</button>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.92rem' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.16)' }}>Tên semantic</th>
                <th style={{ textAlign: 'left', padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.16)' }}>Công thức / quy tắc</th>
                <th style={{ textAlign: 'left', padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.16)' }}>Nguồn DB</th>
                <th style={{ textAlign: 'left', padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.16)' }}>Version</th>
                <th style={{ textAlign: 'left', padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.16)' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((metric) => (
                <tr key={metric.term}>
                  <td style={{ padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.1)', verticalAlign: 'top' }}>
                    <strong>{metric.term}</strong>
                    <div style={{ color: 'var(--color-neutral-500)' }}>{metric.definition}</div>
                  </td>
                  <td style={{ padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.1)', verticalAlign: 'top', fontFamily: 'ui-monospace, SFMono-Regular, monospace' }}>
                    {metric.formula}
                  </td>
                  <td style={{ padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.1)', verticalAlign: 'top' }}>
                    {String(metric.source?.schema ?? '')}{metric.source?.schema ? '.' : ''}{String(metric.source?.table ?? 'Chưa gắn nguồn')}
                    <div style={{ color: 'var(--color-neutral-500)' }}>{String(metric.source?.data_source ?? '')}</div>
                  </td>
                  <td style={{ padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.1)', verticalAlign: 'top' }}>{metric.version_count}</td>
                  <td style={{ padding: '0.65rem', borderBottom: '1px solid rgba(117, 94, 60, 0.1)', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                    <button type="button" style={ghostButtonStyle} onClick={() => handleEdit(metric)}>Sửa</button>{' '}
                    <button type="button" style={ghostButtonStyle} onClick={() => setSelectedMetric(metric.term)}>History</button>{' '}
                    <button type="button" style={ghostButtonStyle} onClick={() => void handleDelete(metric)}>Xóa</button>
                  </td>
                </tr>
              ))}
              {metrics.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: '0.9rem', color: 'var(--color-neutral-500)' }}>
                    Chưa có semantic item. Dùng form bên dưới hoặc Import semantic để tạo dữ liệu.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: '1.25fr 0.85fr' }}>
        <section style={{ ...cardStyle, padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Khai báo / chỉnh sửa semantic</h2>
              <p style={{ color: 'var(--color-neutral-600)' }}>Active - Đang dùng: {selectedMetricData?.term ?? 'chưa có semantic item'}</p>
            </div>
            <select value={selectedMetric} onChange={(event) => setSelectedMetric(event.target.value)} style={{ ...inputStyle, width: '15rem' }}>
              <option value="">Chọn semantic item</option>
              {metrics.map((metric) => <option key={metric.term} value={metric.term}>{metric.term}</option>)}
            </select>
          </div>
          <form onSubmit={(event) => void handlePublish(event)} style={{ display: 'grid', gap: '0.8rem', marginTop: '1rem' }}>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input value={form.term} onChange={(event) => setForm((current) => ({ ...current, term: event.target.value }))} style={inputStyle} placeholder="Tên chỉ số / thuật ngữ / nội quy" required />
              <input value={form.owner} onChange={(event) => setForm((current) => ({ ...current, owner: event.target.value }))} style={inputStyle} placeholder="Owner" required />
            </div>
            <textarea value={form.definition} onChange={(event) => setForm((current) => ({ ...current, definition: event.target.value }))} style={{ ...inputStyle, minHeight: '5rem' }} placeholder="Diễn giải business" required />
            <textarea value={form.formula} onChange={(event) => setForm((current) => ({ ...current, formula: event.target.value }))} style={{ ...inputStyle, minHeight: '5rem', fontFamily: 'ui-monospace, SFMono-Regular, monospace' }} placeholder="Công thức, quy tắc hoặc nội dung chuẩn hóa" required />
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr 1fr' }}>
              <input value={form.aliases} onChange={(event) => setForm((current) => ({ ...current, aliases: event.target.value }))} style={inputStyle} placeholder="Tên gọi khác, cách nhau bằng dấu phẩy" />
              <input value={form.aggregation} onChange={(event) => setForm((current) => ({ ...current, aggregation: event.target.value }))} style={inputStyle} placeholder="Kiểu tổng hợp, ví dụ sum" />
              <input value={form.unit} onChange={(event) => setForm((current) => ({ ...current, unit: event.target.value }))} style={inputStyle} placeholder="Đơn vị, ví dụ VND" />
              <input value={form.grain} onChange={(event) => setForm((current) => ({ ...current, grain: event.target.value }))} style={inputStyle} placeholder="Grain, ví dụ daily_product_region_channel" />
              <input value={form.source_schema} onChange={(event) => setForm((current) => ({ ...current, source_schema: event.target.value }))} style={inputStyle} placeholder="Schema DB, ví dụ SYSTEM" />
              <input value={form.source_table} onChange={(event) => setForm((current) => ({ ...current, source_table: event.target.value }))} style={inputStyle} placeholder="Table/View, ví dụ AIAL_SALES_DAILY_V" />
              <input value={form.source_data_source} onChange={(event) => setForm((current) => ({ ...current, source_data_source: event.target.value }))} style={inputStyle} placeholder="Nguồn dữ liệu, ví dụ oracle-free-system" />
              <input value={form.dimensions} onChange={(event) => setForm((current) => ({ ...current, dimensions: event.target.value }))} style={{ ...inputStyle, gridColumn: 'span 2' }} placeholder="Dimensions, ví dụ PERIOD_DATE, REGION_CODE, CHANNEL_CODE" />
            </div>
            <div style={{ display: 'flex', gap: '0.8rem' }}>
              <input value={form.freshness_rule} onChange={(event) => setForm((current) => ({ ...current, freshness_rule: event.target.value }))} style={{ ...inputStyle, maxWidth: '10rem' }} placeholder="Freshness rule" required />
              <button type="submit" style={buttonStyle}>Publish Version - Xuất bản phiên bản</button>
              <button type="button" style={ghostButtonStyle} onClick={() => setForm(emptyForm)}>Tạo mới</button>
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
          <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Diff view - So sánh công thức</h2>
          <input value={rollbackReason} onChange={(event) => setRollbackReason(event.target.value)} style={{ ...inputStyle, marginTop: '1rem' }} placeholder="Lý do rollback" />
          <div style={{ marginTop: '1rem', borderRadius: '1rem', background: 'rgba(246,241,232,0.9)', padding: '1rem', minHeight: '16rem' }}>
            {diffRows.length === 0 ? (
              <p style={{ margin: 0, color: 'var(--color-neutral-500)' }}>Chưa đủ version để tạo diff.</p>
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
      <section style={{ ...cardStyle, padding: '1.25rem', marginTop: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Import semantic - Nhập hàng loạt</h2>
        <p style={{ color: 'var(--color-neutral-600)', margin: '0.45rem 0 1rem' }}>
          Dán một semantic item, một mảng semantic item, hoặc full config catalog có trường semantic_metrics.
        </p>
        <form onSubmit={(event) => void handleImport(event)} style={{ display: 'grid', gap: '0.8rem' }}>
          <textarea
            value={importJson}
            onChange={(event) => setImportJson(event.target.value)}
            style={{ ...inputStyle, minHeight: '16rem', fontFamily: 'ui-monospace, SFMono-Regular, monospace' }}
            aria-label="Nội dung JSON import semantic"
            required
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.9rem' }}>
              Import sẽ publish version mới và lưu vào DB semantic catalog.
            </span>
            <button type="submit" style={buttonStyle}>Import JSON - Nhập semantic</button>
          </div>
        </form>
      </section>
    </section>
  );
}
