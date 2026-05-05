import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, splitList, tableStyle } from './AdminShared';

type RoleDefinition = {
  name: string;
  description: string | null;
  schema_allowlist: string[];
  data_source_names: string[];
  metric_allowlist: string[];
};

export function RolesPage(): React.JSX.Element {
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [form, setForm] = useState({ name: '', description: '', schema_allowlist: '', data_source_names: '', metric_allowlist: '' });
  const [error, setError] = useState<string | null>(null);

  async function loadRoles(): Promise<void> {
    const data = await apiRequest<{ roles: RoleDefinition[] }>('/v1/admin/roles');
    setRoles(data.roles);
  }

  useEffect(() => {
    void loadRoles().catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Không tải được danh sách vai trò'));
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
          data_source_names: splitList(form.data_source_names),
          metric_allowlist: splitList(form.metric_allowlist),
        }),
      });
      setForm({ name: '', description: '', schema_allowlist: '', data_source_names: '', metric_allowlist: '' });
      await loadRoles();
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
          <textarea value={form.schema_allowlist} onChange={(event) => setForm((current) => ({ ...current, schema_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="Danh sách schema được phép, mỗi dòng một schema" required />
          <textarea value={form.data_source_names} onChange={(event) => setForm((current) => ({ ...current, data_source_names: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="Nguồn dữ liệu (data source names)" />
          <textarea value={form.metric_allowlist} onChange={(event) => setForm((current) => ({ ...current, metric_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="Chỉ số KPI được phép (metric allowlist)" />
        </div>
        <button type="submit" style={buttonStyle}>Tạo vai trò</button>
      </form>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead><tr><th style={cellStyle}>Vai trò</th><th style={cellStyle}>Schemas</th><th style={cellStyle}>Nguồn dữ liệu</th><th style={cellStyle}>Chỉ số KPI</th></tr></thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.name}>
                <td style={cellStyle}><strong>{role.name}</strong><br />{role.description}</td>
                <td style={cellStyle}>{role.schema_allowlist.join(', ')}</td>
                <td style={cellStyle}>{role.data_source_names.join(', ') || 'Tất cả nguồn đã cấu hình'}</td>
                <td style={cellStyle}>{role.metric_allowlist.join(', ') || 'Tất cả chỉ số được phép'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPageShell>
  );
}
