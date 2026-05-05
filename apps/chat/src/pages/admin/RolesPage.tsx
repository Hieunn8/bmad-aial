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
    void loadRoles().catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Khong tai duoc roles'));
  }, []);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!/^[a-z0-9_]+$/.test(form.name)) {
      setError('Role name chi gom chu thuong, so va dau gach duoi.');
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
      setError(submitError instanceof Error ? submitError.message : 'Tao role that bai');
    }
  }

  return (
    <AdminPageShell title="Vai tro va pham vi du lieu">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} style={inputStyle} placeholder="role_name" required />
          <input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} style={inputStyle} placeholder="description" />
          <textarea value={form.schema_allowlist} onChange={(event) => setForm((current) => ({ ...current, schema_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="schema allowlist, moi dong mot schema" required />
          <textarea value={form.data_source_names} onChange={(event) => setForm((current) => ({ ...current, data_source_names: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="data source names" />
          <textarea value={form.metric_allowlist} onChange={(event) => setForm((current) => ({ ...current, metric_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '4rem' }} placeholder="metric allowlist" />
        </div>
        <button type="submit" style={buttonStyle}>Tao role</button>
      </form>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead><tr><th style={cellStyle}>Role</th><th style={cellStyle}>Schemas</th><th style={cellStyle}>Data sources</th><th style={cellStyle}>Metrics</th></tr></thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.name}>
                <td style={cellStyle}><strong>{role.name}</strong><br />{role.description}</td>
                <td style={cellStyle}>{role.schema_allowlist.join(', ')}</td>
                <td style={cellStyle}>{role.data_source_names.join(', ') || 'all configured'}</td>
                <td style={cellStyle}>{role.metric_allowlist.join(', ') || 'all allowed'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPageShell>
  );
}
