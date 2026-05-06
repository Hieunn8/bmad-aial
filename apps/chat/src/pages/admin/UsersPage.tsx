import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { buttonStyle, dangerButtonStyle, ghostButtonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, MultiSelectField, splitList, tableStyle } from './AdminShared';

type User = { user_id: string; email: string; department: string; roles: string[]; ldap_groups: string[]; disabled?: boolean };
type RoleDefinition = { name: string };
type Department = { code: string; name: string; description: string | null };

const emptyForm = { user_id: '', email: '', department: '', roles: [] as string[], ldap_groups: '' };

export function UsersPage(): React.JSX.Element {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadUsers(): Promise<void> {
    const data = await apiRequest<{ users: User[] }>('/v1/admin/users');
    setUsers(data.users);
  }

  async function loadRoles(): Promise<void> {
    const data = await apiRequest<{ roles: RoleDefinition[] }>('/v1/admin/roles');
    setRoles(data.roles);
  }

  async function loadDepartments(): Promise<void> {
    const data = await apiRequest<{ departments: Department[] }>('/v1/admin/departments');
    setDepartments(data.departments);
  }

  useEffect(() => {
    void Promise.all([loadUsers(), loadRoles(), loadDepartments()]).catch((loadError: unknown) =>
      setError(loadError instanceof Error ? loadError.message : 'Không tải được danh sách người dùng')
    );
  }, []);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    const payload = {
      user_id: form.user_id.trim(),
      email: form.email.trim(),
      department: form.department.trim(),
      roles: form.roles,
      ldap_groups: splitList(form.ldap_groups),
    };
    try {
      if (editing) {
        await apiRequest(`/v1/admin/users/${encodeURIComponent(editing.user_id)}`, { method: 'PATCH', body: JSON.stringify(payload) });
      } else {
        await apiRequest('/v1/admin/users', { method: 'POST', body: JSON.stringify(payload) });
      }
      setEditing(null);
      setForm(emptyForm);
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
      roles: user.roles,
      ldap_groups: user.ldap_groups.join(', '),
    });
  }

  return (
    <AdminPageShell title="Quản lý người dùng">
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={(event) => void handleSubmit(event)} style={{ ...adminCard, display: 'grid', gap: '0.8rem', marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.8rem' }}>
          <input value={form.user_id} onChange={(event) => setForm((current) => ({ ...current, user_id: event.target.value }))} style={inputStyle} placeholder="Mã người dùng (user_id)" disabled={Boolean(editing)} required />
          <input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} style={inputStyle} placeholder="Email" required />
          <select value={form.department} onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))} style={inputStyle} required aria-label="Phòng ban">
            <option value="">Chọn phòng ban</option>
            {departments.map((department) => (
              <option key={department.code} value={department.code}>{department.name} ({department.code})</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
          <MultiSelectField
            label="Vai trò"
            note="Chọn một hoặc nhiều vai trò đã khai báo trong danh mục Vai trò."
            options={roles.map((role) => role.name)}
            value={form.roles}
            onChange={(nextRoles) => setForm((current) => ({ ...current, roles: nextRoles }))}
            emptyText="Chưa có vai trò. Tạo vai trò trước khi gán cho người dùng."
          />
          <textarea value={form.ldap_groups} onChange={(event) => setForm((current) => ({ ...current, ldap_groups: event.target.value }))} style={{ ...inputStyle, minHeight: '6rem' }} placeholder="Nhóm LDAP, mỗi dòng hoặc dấu phẩy một nhóm" />
        </div>
        <div style={{ display: 'flex', gap: '0.7rem' }}>
          <button type="submit" style={buttonStyle}>{editing ? 'Cập nhật người dùng' : 'Tạo người dùng'}</button>
          {editing && <button type="button" style={ghostButtonStyle} onClick={() => { setEditing(null); setForm(emptyForm); }}>Hủy</button>}
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
