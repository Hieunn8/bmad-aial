import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, MultiSelectField, splitList, tableStyle } from './AdminShared';

type RoleDefinition = {
  name: string;
  description: string | null;
  schema_allowlist: string[];
  data_source_names: string[];
  metric_allowlist: string[];
};

type DataSource = { name: string };
type SemanticMetric = { term: string };

const emptyForm = {
  name: '',
  description: '',
  schema_allowlist: '',
  data_source_names: [] as string[],
  metric_allowlist: [] as string[],
};

export function RolesPage(): React.JSX.Element {
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [metrics, setMetrics] = useState<SemanticMetric[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);

  async function loadCatalog(): Promise<void> {
    const [rolesData, sourcesData, metricsData] = await Promise.all([
      apiRequest<{ roles: RoleDefinition[] }>('/v1/admin/roles'),
      apiRequest<{ data_sources: DataSource[] }>('/v1/admin/data-sources'),
      apiRequest<{ metrics: SemanticMetric[] }>('/v1/admin/semantic-layer/metrics'),
    ]);
    setRoles(rolesData.roles);
    setDataSources(sourcesData.data_sources);
    setMetrics(metricsData.metrics);
  }

  useEffect(() => {
    void loadCatalog().catch((loadError: unknown) =>
      setError(loadError instanceof Error ? loadError.message : 'Không tải được danh sách vai trò')
    );
  }, []);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!/^[a-z0-9_]+$/.test(form.name)) {
      setError('Tên vai trò chỉ gồm chữ thường, số và dấu gạch dưới.');
      return;
    }
    setError(null);
    try {
      await apiRequest('/v1/admin/roles', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name,
          description: form.description || null,
          schema_allowlist: splitList(form.schema_allowlist),
          data_source_names: form.data_source_names,
          metric_allowlist: form.metric_allowlist,
        }),
      });
      setForm(emptyForm);
      await loadCatalog();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Tạo vai trò thất bại');
    }
  }

  return (
    <AdminPageShell title="Vai trò và phạm vi dữ liệu">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} style={inputStyle} placeholder="Tên vai trò (role_name)" required />
          <input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} style={inputStyle} placeholder="Mô tả (description)" />
          <textarea value={form.schema_allowlist} onChange={(event) => setForm((current) => ({ ...current, schema_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '7rem' }} placeholder="Danh sách schema được phép, mỗi dòng một schema" required />
          <div style={{ display: 'grid', gap: '0.8rem' }}>
            <MultiSelectField
              label="Nguồn dữ liệu"
              note="Chọn một hoặc nhiều nguồn dữ liệu đã cấu hình."
              options={dataSources.map((source) => source.name)}
              value={form.data_source_names}
              onChange={(nextSources) => setForm((current) => ({ ...current, data_source_names: nextSources }))}
              emptyText="Chưa có nguồn dữ liệu để chọn."
            />
            <MultiSelectField
              label="Chỉ số / thuật ngữ nghiệp vụ"
              note="Chọn các semantic item đã publish. Có thể là KPI, nội quy, khái niệm nghiệp vụ hoặc kiến thức được quản trị."
              options={metrics.map((metric) => metric.term)}
              value={form.metric_allowlist}
              onChange={(nextMetrics) => setForm((current) => ({ ...current, metric_allowlist: nextMetrics }))}
              emptyText="Chưa có semantic item để chọn. Publish trong Semantic Studio trước."
            />
          </div>
        </div>
        <button type="submit" style={buttonStyle}>Tạo vai trò</button>
      </form>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead><tr><th style={cellStyle}>Vai trò</th><th style={cellStyle}>Schemas</th><th style={cellStyle}>Nguồn dữ liệu</th><th style={cellStyle}>Chỉ số / thuật ngữ nghiệp vụ</th></tr></thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.name}>
                <td style={cellStyle}><strong>{role.name}</strong><br />{role.description}</td>
                <td style={cellStyle}>{role.schema_allowlist.join(', ')}</td>
                <td style={cellStyle}>{role.data_source_names.join(', ') || 'Tất cả nguồn đã cấu hình'}</td>
                <td style={cellStyle}>{role.metric_allowlist.join(', ') || 'Tất cả semantic item được phép'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPageShell>
  );
}
