import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, dangerButtonStyle, ghostButtonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, splitList, tableStyle } from './AdminShared';

type User = { user_id: string; email: string; department: string; roles: string[]; ldap_groups: string[]; disabled?: boolean };

export function UsersPage(): React.JSX.Element {
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState({ user_id: '', email: '', department: '', roles: '', ldap_groups: '' });
  const [editing, setEditing] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadUsers(): Promise<void> {
    const data = await apiRequest<{ users: User[] }>('/v1/admin/users');
    setUsers(data.users);
  }

  useEffect(() => {
    void loadUsers().catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Không tải được danh sách người dùng'));
  }, []);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    const payload = {
      user_id: form.user_id.trim(),
      email: form.email.trim(),
      department: form.department.trim(),
      roles: splitList(form.roles),
      ldap_groups: splitList(form.ldap_groups),
    };
    try {
      if (editing) {
        await apiRequest(`/v1/admin/users/${encodeURIComponent(editing.user_id)}`, { method: 'PATCH', body: JSON.stringify(payload) });
      } else {
        await apiRequest('/v1/admin/users', { method: 'POST', body: JSON.stringify(payload) });
      }
      setEditing(null);
      setForm({ user_id: '', email: '', department: '', roles: '', ldap_groups: '' });
      await loadUsers();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Lưu người dùng thất bại');
    }
  }

  async function handleDelete(user: User): Promise<void> {
    if (!window.confirm(`Xóa người dùng ${user.user_id}?`)) return;
    await apiRequest(`/v1/admin/users/${encodeURIComponent(user.user_id)}`, { method: 'DELETE' });
    await loadUsers();
  }

  function startEdit(user: User): void {
    setEditing(user);
    setForm({
      user_id: user.user_id,
      email: user.email,
      department: user.department,
      roles: user.roles.join(', '),
      ldap_groups: user.ldap_groups.join(', '),
    });
  }

  return (
    <AdminPageShell title="Quản lý người dùng">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: '0.8rem' }}>
          <input value={form.user_id} onChange={(event) => setForm((current) => ({ ...current, user_id: event.target.value }))} style={inputStyle} placeholder="Mã người dùng (user_id)" disabled={Boolean(editing)} required />
          <input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} style={inputStyle} placeholder="Email" required />
          <input value={form.department} onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))} style={inputStyle} placeholder="Phòng ban (department)" required />
          <input value={form.roles} onChange={(event) => setForm((current) => ({ ...current, roles: event.target.value }))} style={inputStyle} placeholder="Vai trò (roles)" />
          <input value={form.ldap_groups} onChange={(event) => setForm((current) => ({ ...current, ldap_groups: event.target.value }))} style={inputStyle} placeholder="Nhóm LDAP (LDAP groups)" />
        </div>
        <div style={{ display: 'flex', gap: '0.7rem' }}>
          <button type="submit" style={buttonStyle}>{editing ? 'Cập nhật người dùng' : 'Tạo người dùng'}</button>
          {editing && <button type="button" style={ghostButtonStyle} onClick={() => setEditing(null)}>Hủy</button>}
        </div>
      </form>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead><tr><th style={cellStyle}>Người dùng</th><th style={cellStyle}>Email</th><th style={cellStyle}>Phòng ban</th><th style={cellStyle}>Vai trò</th><th style={cellStyle}>Thao tác</th></tr></thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.user_id}>
                <td style={cellStyle}>{user.user_id}</td>
                <td style={cellStyle}>{user.email}</td>
                <td style={cellStyle}>{user.department}</td>
                <td style={cellStyle}>{user.roles.join(', ') || 'Không có'}</td>
                <td style={cellStyle}>
                  <button type="button" style={ghostButtonStyle} onClick={() => startEdit(user)}>Sửa</button>{' '}
                  <button type="button" style={dangerButtonStyle} onClick={() => void handleDelete(user)}>Xóa</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPageShell>
  );
}
