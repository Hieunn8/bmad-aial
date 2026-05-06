import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, tableStyle } from './AdminShared';

type Department = {
  code: string;
  name: string;
  description: string | null;
  created_by: string;
  updated_at: string;
};

export function DepartmentsPage(): React.JSX.Element {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [form, setForm] = useState({ code: '', name: '', description: '' });
  const [error, setError] = useState<string | null>(null);

  async function loadDepartments(): Promise<void> {
    const data = await apiRequest<{ departments: Department[] }>('/v1/admin/departments');
    setDepartments(data.departments);
  }

  useEffect(() => {
    void loadDepartments().catch((loadError: unknown) =>
      setError(loadError instanceof Error ? loadError.message : 'Không tải được danh mục phòng ban')
    );
  }, []);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest('/v1/admin/departments', {
        method: 'POST',
        body: JSON.stringify({
          code: form.code,
          name: form.name || null,
          description: form.description || null,
        }),
      });
      setForm({ code: '', name: '', description: '' });
      await loadDepartments();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Tạo phòng ban thất bại');
    }
  }

  return (
    <AdminPageShell title="Danh mục phòng ban">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr auto', gap: '0.8rem' }}>
          <input value={form.code} onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))} style={inputStyle} placeholder="Mã phòng ban, ví dụ finance" required />
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} style={inputStyle} placeholder="Tên hiển thị" />
          <input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} style={inputStyle} placeholder="Mô tả" />
          <button type="submit" style={buttonStyle}>Thêm phòng ban</button>
        </div>
      </form>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead><tr><th style={cellStyle}>Mã phòng ban</th><th style={cellStyle}>Tên hiển thị</th><th style={cellStyle}>Mô tả</th><th style={cellStyle}>Cập nhật</th></tr></thead>
          <tbody>
            {departments.map((department) => (
              <tr key={department.code}>
                <td style={cellStyle}><strong>{department.code}</strong></td>
                <td style={cellStyle}>{department.name}</td>
                <td style={cellStyle}>{department.description ?? 'Không có'}</td>
                <td style={cellStyle}>{new Date(department.updated_at).toLocaleString('vi-VN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {departments.length === 0 ? <div style={{ color: 'var(--color-neutral-500)', marginTop: '0.8rem' }}>Chưa có phòng ban.</div> : null}
      </div>
    </AdminPageShell>
  );
}
