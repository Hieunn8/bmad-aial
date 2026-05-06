import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../auth/AuthProvider';
import { MultiSelectField } from '../../pages/admin/AdminShared';

type ManagedDocument = {
  document_id: string;
  filename: string;
  source_url?: string;
  owner_department: string;
  allowed_departments: string[];
  allowed_roles: string[];
  visibility: string;
  classification: number;
  source_trust: string;
  effective_date?: string | null;
  chunk_count: number;
  status: string;
  uploaded_by: string;
  indexed_at?: string | null;
};

type DocumentListResponse = {
  documents: ManagedDocument[];
  total: number;
};

type LocalAuthUser = {
  username: string;
  email: string;
  department: string;
  roles: string[];
  clearance: number;
  disabled: boolean;
};

type RoleDefinition = { name: string };
type Department = { code: string; name: string; description: string | null };

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
  padding: '1.35rem 1.35rem 1.2rem',
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

export function DocumentAdminPanel(): React.JSX.Element {
  const auth = useAuth();
  const canManageUsers = auth.session?.claims.roles.includes('admin') ?? false;
  const [documents, setDocuments] = useState<ManagedDocument[]>([]);
  const [roles, setRoles] = useState<RoleDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<LocalAuthUser[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [form, setForm] = useState({
    filename: 'policy-revenue.txt',
    content_text: '',
    source_url: '',
    owner_department: '',
    allowed_departments: [] as string[],
    allowed_roles: [] as string[],
    visibility: 'restricted',
    classification: 1,
    source_trust: 'internal',
    effective_date: new Date().toISOString().slice(0, 10),
  });
  const [userForm, setUserForm] = useState({
    username: 'sales.user',
    password: 'demo123!',
    email: 'sales.user@aial.local',
    department: '',
    roles: [] as string[],
    clearance: 1,
  });

  const roleOptions = useMemo(() => roles.map((role) => role.name), [roles]);
  const departmentOptions = useMemo(
    () => departments.map((department) => department.code),
    [departments],
  );

  async function loadDocuments(): Promise<void> {
    const payload = await apiRequest<DocumentListResponse>('/v1/admin/documents');
    setDocuments(payload.documents);
  }

  async function loadRoles(): Promise<void> {
    const payload = await apiRequest<{ roles: RoleDefinition[] }>('/v1/admin/roles');
    setRoles(payload.roles);
  }

  async function loadUsers(): Promise<void> {
    const payload = await apiRequest<{ users: LocalAuthUser[] }>('/v1/auth/local-users');
    setUsers(payload.users);
  }

  async function loadDepartments(): Promise<void> {
    const payload = await apiRequest<{ departments: Department[] }>('/v1/admin/departments');
    setDepartments(payload.departments);
  }

  useEffect(() => {
    void (async () => {
      try {
        await Promise.all([loadDocuments(), loadRoles(), loadDepartments(), canManageUsers ? loadUsers() : Promise.resolve()]);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Không tải được danh mục tài liệu');
      } finally {
        setLoading(false);
      }
    })();
  }, [canManageUsers]);

  async function handleUpload(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await apiRequest<{ document_id: string; chunk_count: number; message: string }>(
        '/v1/admin/documents',
        {
          method: 'POST',
          body: JSON.stringify(form),
        },
      );
      setMessage(`${result.message} (${result.chunk_count} chunks)`);
      setForm((current) => ({ ...current, content_text: '' }));
      await loadDocuments();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Không thể upload tài liệu');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(documentId: string): Promise<void> {
    setError(null);
    setMessage(null);
    try {
      await apiRequest(`/v1/admin/documents/${documentId}`, { method: 'DELETE' });
      setMessage('Tài liệu đã được xóa mềm');
      await loadDocuments();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Không thể xóa tài liệu');
    }
  }

  async function handleCreateUser(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await apiRequest('/v1/auth/local-users', {
        method: 'POST',
        body: JSON.stringify(userForm),
      });
      setMessage('Đã tạo local user');
      await loadUsers();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Không thể tạo local user');
    }
  }

  return (
    <section id="document-admin" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Quản trị tài liệu - Document Admin</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            Upload tài liệu text cho RAG, chọn phòng ban và vai trò được phép truy cập. Metadata lưu PostgreSQL, chunk và vector lưu Weaviate.
          </p>
        </div>
        <button type="button" style={ghostButtonStyle} onClick={() => void loadDocuments()}>
          Làm mới
        </button>
      </div>

      {(message || error) ? (
        <div
          role={error ? 'alert' : 'status'}
          style={{
            marginTop: '0.9rem',
            borderRadius: '0.9rem',
            padding: '0.85rem 0.95rem',
            background: error ? 'rgba(220, 38, 38, 0.09)' : 'rgba(15, 118, 110, 0.08)',
            color: error ? '#991b1b' : '#115e59',
          }}
        >
          {error ?? message}
        </div>
      ) : null}

      <form onSubmit={(event) => void handleUpload(event)} style={{ marginTop: '1rem', display: 'grid', gap: '0.8rem' }}>
        <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
          <input
            value={form.filename}
            onChange={(event) => setForm((current) => ({ ...current, filename: event.target.value }))}
            style={inputStyle}
            placeholder="Tên file (filename)"
          />
          <input
            value={form.source_url}
            onChange={(event) => setForm((current) => ({ ...current, source_url: event.target.value }))}
            style={inputStyle}
            placeholder="Nguồn tài liệu (source URL)"
          />
        </div>
        <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr 1fr 1fr' }}>
          <select
            value={form.owner_department}
            onChange={(event) => setForm((current) => ({ ...current, owner_department: event.target.value }))}
            style={inputStyle}
            aria-label="Phòng ban sở hữu"
          >
            <option value="">Chọn phòng ban sở hữu</option>
            {departmentOptions.map((department) => <option key={department} value={department}>{department}</option>)}
          </select>
          <select
            value={form.visibility}
            onChange={(event) => setForm((current) => ({ ...current, visibility: event.target.value }))}
            style={inputStyle}
            aria-label="Phạm vi hiển thị"
          >
            <option value="restricted">Hạn chế - Restricted</option>
            <option value="company-wide">Toàn công ty - Company-wide</option>
          </select>
          <select
            value={form.classification}
            onChange={(event) => setForm((current) => ({ ...current, classification: Number(event.target.value) }))}
            style={inputStyle}
            aria-label="Phân loại bảo mật"
          >
            <option value={0}>PUBLIC - Công khai</option>
            <option value={1}>INTERNAL - Nội bộ</option>
            <option value={2}>CONFIDENTIAL - Mật</option>
            <option value={3}>SECRET - Tối mật</option>
          </select>
          <input
            value={form.source_trust}
            onChange={(event) => setForm((current) => ({ ...current, source_trust: event.target.value }))}
            style={inputStyle}
            placeholder="Độ tin cậy nguồn (source trust)"
          />
        </div>
        <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr 1fr' }}>
          <MultiSelectField
            label="Phòng ban được phép"
            note="Có thể chọn nhiều phòng ban."
            options={departmentOptions}
            value={form.allowed_departments}
            onChange={(nextDepartments) => setForm((current) => ({ ...current, allowed_departments: nextDepartments }))}
            emptyText="Chưa có phòng ban. Vào Admin > Người dùng để tạo danh mục phòng ban trước."
          />
          <MultiSelectField
            label="Vai trò được phép"
            note="Có thể chọn nhiều vai trò từ danh mục Vai trò."
            options={roleOptions}
            value={form.allowed_roles}
            onChange={(nextRoles) => setForm((current) => ({ ...current, allowed_roles: nextRoles }))}
            emptyText="Chưa có vai trò để chọn."
          />
          <input
            value={form.effective_date}
            onChange={(event) => setForm((current) => ({ ...current, effective_date: event.target.value }))}
            type="date"
            style={inputStyle}
            aria-label="Ngày hiệu lực"
          />
        </div>
        <textarea
          value={form.content_text}
          onChange={(event) => setForm((current) => ({ ...current, content_text: event.target.value }))}
          style={{ ...inputStyle, minHeight: '10rem', resize: 'vertical' }}
          placeholder="Nội dung tài liệu để chunk và index vào Weaviate"
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
          <button type="submit" style={buttonStyle} disabled={submitting}>
            {submitting ? 'Đang upload...' : 'Upload và Index'}
          </button>
          <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
            Metadata lưu trong PostgreSQL; chunk và vector lưu trong Weaviate.
          </div>
        </div>
      </form>

      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.8rem' }}>
        {loading ? <div>Đang tải danh mục tài liệu...</div> : null}
        {!loading && documents.length === 0 ? (
          <div style={{ color: 'var(--color-neutral-500)' }}>Chưa upload tài liệu.</div>
        ) : null}
        {documents.map((document) => (
          <article
            key={document.document_id}
            style={{
              borderRadius: '1rem',
              border: '1px solid rgba(117, 94, 60, 0.14)',
              background: 'rgba(255,255,255,0.74)',
              padding: '0.95rem 1rem',
              display: 'grid',
              gap: '0.4rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
              <div>
                <div style={{ fontWeight: 700 }}>{document.filename}</div>
                <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                  Sở hữu: {document.owner_department} · {document.visibility} · phân loại {document.classification} · {document.status}
                </div>
              </div>
              <button type="button" style={ghostButtonStyle} onClick={() => void handleDelete(document.document_id)}>
                Xóa mềm
              </button>
            </div>
            <div style={{ color: 'var(--color-neutral-600)', fontSize: '0.9rem' }}>
              Chunks: {document.chunk_count} · Upload bởi: {document.uploaded_by}
            </div>
            <div style={{ color: 'var(--color-neutral-600)', fontSize: '0.88rem' }}>
              Phòng ban: {document.allowed_departments.join(', ') || 'Không có'} · Vai trò:{' '}
              {document.allowed_roles.join(', ') || 'Tất cả vai trò'}
            </div>
            {document.source_url ? (
              <a href={document.source_url} target="_blank" rel="noreferrer" style={{ color: '#115e59' }}>
                {document.source_url}
              </a>
            ) : null}
          </article>
        ))}
      </div>

      {canManageUsers ? (
        <div style={{ marginTop: '1.25rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1.1fr 0.9fr' }}>
          <form onSubmit={(event) => void handleCreateUser(event)} style={{ display: 'grid', gap: '0.8rem' }}>
            <h3 style={{ margin: 0 }}>Quản lý local user</h3>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input
                value={userForm.username}
                onChange={(event) => setUserForm((current) => ({ ...current, username: event.target.value }))}
                style={inputStyle}
                placeholder="Tên đăng nhập (username)"
              />
              <input
                value={userForm.email}
                onChange={(event) => setUserForm((current) => ({ ...current, email: event.target.value }))}
                style={inputStyle}
                placeholder="Email"
              />
            </div>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr 1fr' }}>
              <input
                type="password"
                value={userForm.password}
                onChange={(event) => setUserForm((current) => ({ ...current, password: event.target.value }))}
                style={inputStyle}
                placeholder="Mật khẩu"
              />
              <select
                value={userForm.department}
                onChange={(event) => setUserForm((current) => ({ ...current, department: event.target.value }))}
                style={inputStyle}
                aria-label="Phòng ban"
              >
                <option value="">Chọn phòng ban</option>
                {departmentOptions.map((department) => <option key={department} value={department}>{department}</option>)}
              </select>
            </div>
            <div style={{ display: 'grid', gap: '0.8rem', gridTemplateColumns: '1fr auto' }}>
              <MultiSelectField
                label="Vai trò"
                note="Chọn một hoặc nhiều vai trò đã khai báo."
                options={roleOptions}
                value={userForm.roles}
                onChange={(nextRoles) => setUserForm((current) => ({ ...current, roles: nextRoles }))}
                emptyText="Chưa có vai trò để chọn."
              />
              <input
                type="number"
                min={1}
                max={3}
                value={userForm.clearance}
                onChange={(event) => setUserForm((current) => ({ ...current, clearance: Number(event.target.value) }))}
                style={{ ...inputStyle, width: '7rem' }}
                aria-label="Clearance"
              />
            </div>
            <button type="submit" style={buttonStyle}>Tạo local user</button>
          </form>

          <div style={{ display: 'grid', gap: '0.8rem' }}>
            <h3 style={{ margin: 0 }}>Local users hiện có</h3>
            {users.map((user) => (
              <article
                key={user.username}
                style={{ borderRadius: '0.9rem', background: 'rgba(246,241,232,0.82)', padding: '0.85rem 0.95rem' }}
              >
                <div style={{ fontWeight: 700 }}>{user.username}</div>
                <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                  {user.email} · {user.department} · clearance {user.clearance}
                </div>
                <div style={{ marginTop: '0.25rem', color: 'var(--color-neutral-600)', fontSize: '0.88rem' }}>
                  Vai trò: {user.roles.join(', ')}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
