import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, ghostButtonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, splitList } from './AdminShared';

type DataSource = {
  name: string;
  description: string | null;
  host: string;
  port: number;
  service_name: string;
  username: string;
  schema_allowlist: string[];
  query_timeout_seconds: number;
  row_limit: number;
  status: string;
};

const emptyForm = {
  name: '',
  description: '',
  host: '',
  port: '1521',
  service_name: '',
  username: '',
  password: '',
  schema_allowlist: '',
  query_timeout_seconds: '30',
  row_limit: '50000',
};

export function DataSourcesPage(): React.JSX.Element {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<DataSource | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadDataSources(): Promise<void> {
    const data = await apiRequest<{ data_sources: DataSource[] }>('/v1/admin/data-sources');
    setDataSources(data.data_sources);
  }

  useEffect(() => {
    void loadDataSources().catch((loadError: unknown) =>
      setError(loadError instanceof Error ? loadError.message : 'Không tải được nguồn dữ liệu')
    );
  }, []);

  function startEdit(source: DataSource): void {
    setEditing(source);
    setForm({
      name: source.name,
      description: source.description ?? '',
      host: source.host,
      port: String(source.port),
      service_name: source.service_name,
      username: source.username,
      password: '',
      schema_allowlist: source.schema_allowlist.join('\n'),
      query_timeout_seconds: String(source.query_timeout_seconds),
      row_limit: String(source.row_limit),
    });
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    const payload = {
      description: form.description || null,
      host: form.host,
      port: Number(form.port),
      service_name: form.service_name,
      username: form.username,
      ...(form.password ? { password: form.password } : {}),
      schema_allowlist: splitList(form.schema_allowlist),
      query_timeout_seconds: Number(form.query_timeout_seconds),
      row_limit: Number(form.row_limit),
    };
    try {
      if (editing) {
        await apiRequest(`/v1/admin/data-sources/${encodeURIComponent(editing.name)}`, { method: 'PATCH', body: JSON.stringify(payload) });
      } else {
        await apiRequest('/v1/admin/data-sources', { method: 'POST', body: JSON.stringify({ name: form.name, password: form.password, ...payload }) });
      }
      setEditing(null);
      setForm(emptyForm);
      await loadDataSources();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Lưu nguồn dữ liệu thất bại');
    }
  }

  function statusColor(status: string): string {
    if (status === 'active') return '#16a34a';
    if (status === 'error') return '#dc2626';
    if (status === 'unreachable') return '#ca8a04';
    return 'var(--color-neutral-500)';
  }

  return (
    <AdminPageShell title="Nguồn dữ liệu Oracle">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '0.8rem' }}>
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} style={inputStyle} placeholder="Tên nguồn (name)" disabled={Boolean(editing)} required />
          <input value={form.host} onChange={(event) => setForm((current) => ({ ...current, host: event.target.value }))} style={inputStyle} placeholder="Máy chủ (host)" required />
          <input value={form.port} onChange={(event) => setForm((current) => ({ ...current, port: event.target.value }))} style={inputStyle} placeholder="Cổng (port)" type="number" required />
          <input value={form.service_name} onChange={(event) => setForm((current) => ({ ...current, service_name: event.target.value }))} style={inputStyle} placeholder="Tên service Oracle" required />
          <input value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} style={inputStyle} placeholder="Tài khoản (username)" required />
          <input value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} style={inputStyle} placeholder={editing ? 'Mật khẩu mới nếu đổi' : 'Mật khẩu'} type="password" required={!editing} />
          <input value={form.query_timeout_seconds} onChange={(event) => setForm((current) => ({ ...current, query_timeout_seconds: event.target.value }))} style={inputStyle} placeholder="Timeout truy vấn, giây" type="number" />
          <input value={form.row_limit} onChange={(event) => setForm((current) => ({ ...current, row_limit: event.target.value }))} style={inputStyle} placeholder="Giới hạn dòng (row limit)" type="number" />
        </div>
        <textarea value={form.schema_allowlist} onChange={(event) => setForm((current) => ({ ...current, schema_allowlist: event.target.value }))} style={{ ...inputStyle, minHeight: '4.5rem' }} placeholder="Danh sách schema được phép, mỗi dòng một schema" />
        <input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} style={inputStyle} placeholder="Mô tả (description)" />
        <div style={{ display: 'flex', gap: '0.7rem' }}>
          <button type="submit" style={buttonStyle}>{editing ? 'Sửa cấu hình' : 'Thêm nguồn dữ liệu'}</button>
          {editing && <button type="button" style={ghostButtonStyle} onClick={() => { setEditing(null); setForm(emptyForm); }}>Hủy</button>}
        </div>
      </form>
      <div style={{ display: 'grid', gap: '1rem' }}>
        {dataSources.map((source) => (
          <article key={source.name} style={adminCard}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.15rem' }}>
                  <span aria-hidden="true" style={{ display: 'inline-block', width: '0.7rem', height: '0.7rem', borderRadius: '999px', background: statusColor(source.status), marginRight: '0.45rem' }} />
                  {source.name}
                </h2>
                <p style={{ color: 'var(--color-neutral-600)' }}>{source.description}</p>
                <div>Máy chủ: {source.host}:{source.port} | Service: {source.service_name}</div>
                <div>Schema: {source.schema_allowlist.join(', ') || 'Không có'} | Timeout: {source.query_timeout_seconds}s | Giới hạn dòng: {source.row_limit.toLocaleString('vi-VN')}</div>
              </div>
              <button type="button" style={ghostButtonStyle} onClick={() => startEdit(source)}>Sửa cấu hình</button>
            </div>
          </article>
        ))}
      </div>
    </AdminPageShell>
  );
}
