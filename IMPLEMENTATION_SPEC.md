# AIAL — Implementation Spec: UX Restructure & Missing Features

**Ngày**: 2026-05-05 | **Dựa trên codebase thực tế** | **Không cần hỏi thêm**

---

## 1. Bối Cảnh & Phạm Vi

**Vấn đề**: `apps/chat/src/components/epic5b/Epic5BWorkspace.tsx` (820 dòng) render toàn bộ app trên một trang. Sidebar trong `AppLayout.tsx` dùng `<a href="#anchor">` thay vì real routes.

**Backend đã có đầy đủ** — chỉ cần viết UI. Ngoại lệ: Approvals và Security (chưa có backend endpoint) → **defer, không làm sprint này**.

**Stack**: React 19 + TypeScript, TanStack Router v1, TanStack Query, inline CSS styles (không dùng CSS modules hay Tailwind), `apiRequest<T>()` từ `../../api/client`.

**Phân công** (3 người làm song song):
- **Dev A**: Bước 0 (shared) + Phase 1 (route splitting, sidebar)
- **Dev B**: Phase 2 (Admin pages: Users, Roles, Data Sources, Documents, Audit Log)
- **Dev C**: Phase 3 (Analytics routes, Export trong Chat, Forecast download, Trend export)

Dev B và C bắt đầu được sau khi Dev A hoàn thành Bước 0.

---

## 2. Quy Ước Kỹ Thuật Bắt Buộc

### 2.1 Shared Style Constants

Tạo file **`apps/chat/src/styles/shared.ts`** (file mới):

```ts
import type { CSSProperties } from 'react';

export const cardStyle: CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
};

export const inputStyle: CSSProperties = {
  width: '100%',
  padding: '0.8rem 0.95rem',
  borderRadius: '0.9rem',
  border: '1px solid rgba(117, 94, 60, 0.22)',
  background: 'rgba(255,255,255,0.92)',
  color: 'var(--color-neutral-900)',
  fontSize: '0.95rem',
};

export const buttonStyle: CSSProperties = {
  border: 'none',
  borderRadius: '999px',
  padding: '0.8rem 1.1rem',
  background: 'linear-gradient(135deg, #0f766e 0%, #115e59 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

export const ghostButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: 'rgba(15, 118, 110, 0.09)',
  color: '#115e59',
};

export const dangerButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
};

export const pageShell: CSSProperties = {
  minHeight: '100%',
  background:
    'linear-gradient(180deg, rgba(242,236,226,0.92) 0%, rgba(248,245,239,0.98) 22%, rgba(255,255,255,1) 100%)',
  color: 'var(--color-neutral-900)',
  padding: '2rem 2.4rem 3rem',
};

export const pageTitle: CSSProperties = {
  margin: 0,
  fontSize: '1.6rem',
  fontWeight: 700,
  color: 'var(--color-neutral-900)',
};

export const sectionLabel: CSSProperties = {
  fontSize: '0.78rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: 'var(--color-neutral-500)',
  fontWeight: 600,
};
```

### 2.2 Auth Pattern

```tsx
// Đọc role từ session (roles là ARRAY, không phải string đơn)
const auth = useAuth();
const roles = auth.session?.claims.roles ?? [];
const isAdmin = roles.includes('admin');
const isAdminOrDataOwner = roles.includes('admin') || roles.includes('data_owner');
```

### 2.3 API Client

```tsx
import { apiRequest } from '../../api/client'; // điều chỉnh relative path theo vị trí file

// GET
const data = await apiRequest<{ users: User[] }>('/v1/admin/users');

// POST
const result = await apiRequest<{ user: User }>('/v1/admin/users', {
  method: 'POST',
  body: JSON.stringify(payload),
});

// PATCH
await apiRequest<{ user: User }>(`/v1/admin/users/${userId}`, {
  method: 'PATCH',
  body: JSON.stringify(changes),
});

// DELETE
await apiRequest<{ status: string }>(`/v1/admin/users/${userId}`, {
  method: 'DELETE',
});
```

### 2.4 Route Guard Pattern (từ `routes/index.tsx`)

```tsx
// Trong beforeLoad của route — dùng context.auth (không dùng useAuth)
beforeLoad: ({ context }) => {
  if (!context.auth.isAuthenticated && context.auth.isReady) {
    throw redirect({ to: '/login' });
  }
},
```

### 2.5 Role Guard (dùng thêm sau auth guard)

```tsx
// Trong beforeLoad admin routes
beforeLoad: ({ context }) => {
  if (!context.auth.isAuthenticated && context.auth.isReady) {
    throw redirect({ to: '/login' });
  }
  const roles = context.auth.session?.claims.roles ?? [];
  if (!roles.includes('admin') && !roles.includes('data_owner')) {
    throw redirect({ to: '/chat' });
  }
},
```

---

## 3. Bước 0 — Shared Foundation (Dev A làm trước, Dev B & C chờ)

### 3.1 Tạo Shared Styles

Tạo `apps/chat/src/styles/shared.ts` với nội dung từ mục 2.1.

### 3.2 Sửa `apps/chat/src/routes/index.tsx`

**Xóa toàn bộ nội dung hiện tại** và thay bằng:

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
    throw redirect({ to: '/chat' });
  },
  component: () => null,
});
```

### 3.3 Sửa `apps/chat/src/components/AppLayout.tsx`

**Giữ nguyên** phần header và layout structure. **Chỉ thay phần `<nav>`**.

Thêm import ở đầu file:
```tsx
import { Link } from '@tanstack/react-router';
```

Thay toàn bộ nội dung `<nav>` (từ dòng 99 đến 130) bằng:

```tsx
<nav
  aria-label="Primary navigation"
  style={{
    width: 'var(--sidebar-width)',
    background: 'rgba(255,255,255,0.58)',
    borderRight: '1px solid rgba(117, 94, 60, 0.12)',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    padding: '1.05rem 0.9rem',
    gap: '0.5rem',
  }}
>
  <NavSection label="Ứng dụng">
    <NavLink to="/chat">Chat</NavLink>
    <NavLink to="/analytics/forecast">Dự báo</NavLink>
    <NavLink to="/analytics/anomaly">Bất thường</NavLink>
    <NavLink to="/analytics/trend">Xu hướng</NavLink>
    <NavLink to="/analytics/drilldown">Drill-down</NavLink>
    <NavLink to="/memory">Memory Studio</NavLink>
  </NavSection>

  {isAdminOrDataOwner && (
    <NavSection label="Quản lý">
      <NavLink to="/semantic">Semantic Studio</NavLink>
    </NavSection>
  )}

  {isAdminOrDataOwner && (
    <NavSection label="Quản trị">
      <NavLink to="/admin">Dashboard</NavLink>
      <NavLink to="/admin/users">Người dùng</NavLink>
      <NavLink to="/admin/roles">Vai trò</NavLink>
      <NavLink to="/admin/data-sources">Nguồn dữ liệu</NavLink>
      <NavLink to="/admin/documents">Tài liệu</NavLink>
      <NavLink to="/admin/audit-log">Audit Log</NavLink>
    </NavSection>
  )}
</nav>
```

Thêm 2 helper components vào cuối file `AppLayout.tsx` (trước export):

```tsx
function NavSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div
        style={{
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--color-neutral-400)',
          fontWeight: 600,
          padding: '0.5rem 0.5rem 0.3rem',
        }}
      >
        {label}
      </div>
      <ul role="list" style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: '0.3rem' }}>
        {children}
      </ul>
    </div>
  );
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <li>
      <Link
        to={to}
        style={{
          display: 'block',
          padding: '0.65rem 0.85rem',
          borderRadius: '0.85rem',
          color: 'var(--color-neutral-700)',
          textDecoration: 'none',
          fontSize: '0.92rem',
          fontWeight: 500,
        }}
        activeProps={{
          style: {
            display: 'block',
            padding: '0.65rem 0.85rem',
            borderRadius: '0.85rem',
            textDecoration: 'none',
            fontSize: '0.92rem',
            fontWeight: 600,
            background: 'rgba(15, 118, 110, 0.10)',
            color: '#0f766e',
          },
        }}
      >
        {children}
      </Link>
    </li>
  );
}
```

Sửa khai báo `isAdminOrDataOwner` trong `AppLayout` (đã có `roles`):
```tsx
const isAdminOrDataOwner = roles.includes('admin') || roles.includes('data_owner');
```

Xóa dòng `const canManageDocuments = ...` vì không dùng nữa.

Xóa khối "Delivery note" trong sidebar (div có `background: linear-gradient(...)`).

Cập nhật subtitle trong header từ `'Epic 5B + 6 workspace'` thành `'AI Assistant'`.

---

## 4. Phase 1 — Route Files (Dev A)

### 4.1 `routes/chat.tsx`

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router';
import { ChatAssistantConsole } from '../components/epic6/ChatAssistantConsole';

export const Route = createFileRoute('/chat')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: ChatPage,
});

function ChatPage() {
  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <ChatAssistantConsole />
      </div>
    </div>
  );
}
```

### 4.2 `routes/memory.tsx`

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router';
import { MemoryStudioPage } from '../pages/MemoryStudioPage';

export const Route = createFileRoute('/memory')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: MemoryStudioPage,
});
```

### 4.3 `routes/semantic.tsx`

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router';
import { SemanticStudioPage } from '../pages/SemanticStudioPage';

export const Route = createFileRoute('/semantic')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
    const roles = context.auth.session?.claims.roles ?? [];
    if (!roles.includes('admin') && !roles.includes('data_owner')) {
      throw redirect({ to: '/chat' });
    }
  },
  component: SemanticStudioPage,
});
```

### 4.4 `routes/analytics.tsx` — Layout với tab navigation

```tsx
import { createFileRoute, Link, Outlet, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/analytics')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: AnalyticsLayout,
});

const tabs = [
  { to: '/analytics/forecast', label: 'Dự báo' },
  { to: '/analytics/anomaly', label: 'Bất thường' },
  { to: '/analytics/trend', label: 'Xu hướng' },
  { to: '/analytics/drilldown', label: 'Drill-down' },
];

function AnalyticsLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
      <div
        style={{
          display: 'flex',
          gap: '0.4rem',
          padding: '0.75rem 2.4rem 0',
          borderBottom: '1px solid rgba(117, 94, 60, 0.12)',
          background: 'rgba(255,255,255,0.7)',
        }}
      >
        {tabs.map((tab) => (
          <Link
            key={tab.to}
            to={tab.to}
            style={{
              padding: '0.6rem 1.1rem',
              borderRadius: '0.75rem 0.75rem 0 0',
              textDecoration: 'none',
              fontWeight: 500,
              fontSize: '0.92rem',
              color: 'var(--color-neutral-600)',
              borderBottom: '2px solid transparent',
            }}
            activeProps={{
              style: {
                padding: '0.6rem 1.1rem',
                borderRadius: '0.75rem 0.75rem 0 0',
                textDecoration: 'none',
                fontWeight: 700,
                fontSize: '0.92rem',
                color: '#0f766e',
                borderBottom: '2px solid #0f766e',
              },
            }}
          >
            {tab.label}
          </Link>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </div>
    </div>
  );
}
```

### 4.5 `routes/analytics/index.tsx`

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/analytics/')({
  beforeLoad: () => {
    throw redirect({ to: '/analytics/forecast' });
  },
  component: () => null,
});
```

### 4.6 `routes/analytics/forecast.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { ForecastStudio } from '../../components/epic7/ForecastStudio';

export const Route = createFileRoute('/analytics/forecast')({
  component: ForecastStudio,
});
```

### 4.7 `routes/analytics/anomaly.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { AnomalyAlertsPanel } from '../../components/epic7/AnomalyAlertsPanel';

export const Route = createFileRoute('/analytics/anomaly')({
  component: AnomalyAlertsPanel,
});
```

### 4.8 `routes/analytics/trend.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { TrendAnalysisPanel } from '../../components/epic7/TrendAnalysisPanel';

export const Route = createFileRoute('/analytics/trend')({
  component: TrendAnalysisPanel,
});
```

### 4.9 `routes/analytics/drilldown.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { DrilldownExplainabilityPanel } from '../../components/epic7/DrilldownExplainabilityPanel';

export const Route = createFileRoute('/analytics/drilldown')({
  component: DrilldownExplainabilityPanel,
});
```

### 4.10 `routes/admin.tsx` — Admin Layout + Role Guard

```tsx
import { createFileRoute, Link, Outlet, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/admin')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
    const roles = context.auth.session?.claims.roles ?? [];
    if (!roles.includes('admin') && !roles.includes('data_owner')) {
      throw redirect({ to: '/chat' });
    }
  },
  component: AdminLayout,
});

const adminNavItems = [
  { to: '/admin', label: 'Dashboard', exact: true },
  { to: '/admin/users', label: 'Người dùng' },
  { to: '/admin/roles', label: 'Vai trò' },
  { to: '/admin/data-sources', label: 'Nguồn dữ liệu' },
  { to: '/admin/documents', label: 'Tài liệu' },
  { to: '/admin/audit-log', label: 'Audit Log' },
];

function AdminLayout() {
  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      <nav
        style={{
          width: '13rem',
          background: 'rgba(255,255,255,0.5)',
          borderRight: '1px solid rgba(117, 94, 60, 0.12)',
          padding: '1rem 0.7rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.3rem',
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--color-neutral-400)',
            fontWeight: 600,
            padding: '0.3rem 0.5rem 0.5rem',
          }}
        >
          Quản trị hệ thống
        </div>
        {adminNavItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            style={{
              display: 'block',
              padding: '0.6rem 0.8rem',
              borderRadius: '0.75rem',
              textDecoration: 'none',
              fontSize: '0.9rem',
              fontWeight: 500,
              color: 'var(--color-neutral-700)',
            }}
            activeProps={{
              style: {
                display: 'block',
                padding: '0.6rem 0.8rem',
                borderRadius: '0.75rem',
                textDecoration: 'none',
                fontSize: '0.9rem',
                fontWeight: 700,
                color: '#0f766e',
                background: 'rgba(15,118,110,0.10)',
              },
            }}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
```

### 4.11 Tạo các route files admin (nội dung đơn giản — pages viết ở Phase 2)

**`routes/admin/index.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { AdminDashboardPage } from '../../pages/admin/AdminDashboardPage';
export const Route = createFileRoute('/admin/')({ component: AdminDashboardPage });
```

**`routes/admin/users.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { UsersPage } from '../../pages/admin/UsersPage';
export const Route = createFileRoute('/admin/users')({ component: UsersPage });
```

**`routes/admin/roles.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { RolesPage } from '../../pages/admin/RolesPage';
export const Route = createFileRoute('/admin/roles')({ component: RolesPage });
```

**`routes/admin/data-sources.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { DataSourcesPage } from '../../pages/admin/DataSourcesPage';
export const Route = createFileRoute('/admin/data-sources')({ component: DataSourcesPage });
```

**`routes/admin/documents.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { DocumentAdminPanel } from '../../components/rag/DocumentAdminPanel';

export const Route = createFileRoute('/admin/documents')({
  component: () => (
    <div style={{ padding: '2rem 2.4rem' }}>
      <DocumentAdminPanel />
    </div>
  ),
});
```

**`routes/admin/audit-log.tsx`**:
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { AuditLogPage } from '../../pages/admin/AuditLogPage';
export const Route = createFileRoute('/admin/audit-log')({ component: AuditLogPage });
```

### 4.12 Tạo Pages cho Memory và Semantic (extract từ Epic5BWorkspace)

**`apps/chat/src/pages/MemoryStudioPage.tsx`**:

Cắt toàn bộ khối `<div id="memory-studio">` (dòng 628–749) và `<div id="history-studio">` (dòng 751–816) từ `Epic5BWorkspace.tsx`, paste vào file mới này.

Cần copy thêm các types: `Suggestion`, `SavedTemplate`, `HistoryEntry`, `MemoryViolation`, `MemoryContextBundle`.

Cần copy các hàm: `loadMemorySurfaces`, `probeContext`, `handleSaveTemplate`, `handleReuse`, `loadHistory`.

Cần copy state: `suggestions`, `templates`, `historyEntries`, `memoryAudit`, `memoryProbe`, `draftPrompt`, `historyKeyword`, `historyTopic`, `contextQuery`, `templateForm`.

Cần copy style constants: `cardStyle`, `panelGrid`, `buttonStyle`, `ghostButtonStyle`, `inputStyle` — **thay bằng import từ `../styles/shared`**.

Import cần có:
```tsx
import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import { cardStyle, buttonStyle, ghostButtonStyle, inputStyle, pageShell } from '../styles/shared';
```

Wrap kết quả trong `<section style={pageShell}>`.

**`apps/chat/src/pages/SemanticStudioPage.tsx`**:

Tương tự — cắt khối `<div id="semantic-studio">` (dòng 450–626) từ `Epic5BWorkspace.tsx`.

Cần copy types: `Metric`, `MetricVersion`, `MetricDiffRow`.

Cần copy state: `metrics`, `selectedMetric`, `versions`, `diffRows`, `semanticForm`, `rollbackReason`, `flash`, `error`, `semanticDenied`, `loading`, `selectedMetricData`.

Cần copy hàm: `loadMetrics`, `loadVersions`, `handlePublish`, `handleRollback`, `formatDate`.

Import styles từ `../styles/shared`.

### 4.13 Dọn dẹp `Epic5BWorkspace.tsx`

Sau khi extract xong MemoryStudio và SemanticStudio, `Epic5BWorkspace.tsx` không còn được dùng nữa. **Xóa file này**. Đảm bảo không còn import nào trỏ đến nó.

---

## 5. Phase 2 — Admin Pages (Dev B)

Tất cả pages đặt trong `apps/chat/src/pages/admin/`.

### 5.1 `AdminDashboardPage.tsx`

**API**: Gọi 3 endpoint song song bằng `Promise.all`.

```tsx
import { useEffect, useState } from 'react';
import { apiRequest } from '../../api/client';
import { Link } from '@tanstack/react-router';
import { cardStyle, pageShell, pageTitle } from '../../styles/shared';

type DashboardStats = {
  userCount: number;
  dataSourceCount: number;
  auditToday: number;
};

export function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<{ total: number }>('/v1/admin/users'),
      apiRequest<{ total: number }>('/v1/admin/data-sources'),
      apiRequest<{ total: number }>('/v1/admin/audit-logs?page_size=1'),
    ])
      .then(([users, sources, audit]) => {
        setStats({
          userCount: users.total,
          dataSourceCount: sources.total,
          auditToday: audit.total,
        });
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Lỗi tải dữ liệu'));
  }, []);

  return (
    <section style={pageShell}>
      <h1 style={pageTitle}>Dashboard Quản trị</h1>
      {error && <div style={{ color: '#991b1b', marginTop: '1rem' }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.2rem', marginTop: '1.5rem' }}>
        <StatCard label="Người dùng" value={stats?.userCount} to="/admin/users" />
        <StatCard label="Nguồn dữ liệu" value={stats?.dataSourceCount} to="/admin/data-sources" />
        <StatCard label="Audit records" value={stats?.auditToday} to="/admin/audit-log" />
      </div>
    </section>
  );
}

function StatCard({ label, value, to }: { label: string; value?: number; to: string }) {
  return (
    <Link to={to} style={{ textDecoration: 'none' }}>
      <div style={{ ...cardStyle, padding: '1.4rem 1.6rem', cursor: 'pointer' }}>
        <div style={{ fontSize: '0.82rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>{label}</div>
        <div style={{ marginTop: '0.5rem', fontSize: '2rem', fontWeight: 700, color: '#0f766e' }}>
          {value ?? '—'}
        </div>
      </div>
    </Link>
  );
}
```

---

### 5.2 `UsersPage.tsx`

**Endpoints dùng**:
- `GET /v1/admin/users` → `{ users: User[], total: number }` (không có pagination param, trả hết)
- `POST /v1/admin/users` body: `{ user_id, email, department, roles: string[], ldap_groups: string[] }`
- `PATCH /v1/admin/users/{user_id}` body: `{ email?, department?, roles?, ldap_groups? }`
- `DELETE /v1/admin/users/{user_id}` → soft delete
- `POST /v1/admin/users/import/preview` body: `{ csv_content: string }` → preview
- `POST /v1/admin/users/import/commit` body: `{ csv_content: string }` → thực hiện import
- `POST /v1/admin/users/ldap-sync` body: `{ updates: [], interval_minutes?: number }`
- `GET /v1/admin/users/sync-status` → LDAP sync status

**Type User** (từ backend `UserCreateRequest` + `to_dict()`):
```ts
type User = {
  user_id: string;
  email: string;
  department: string;
  roles: string[];
  ldap_groups: string[];
  is_deleted?: boolean;
};
```

**Cấu trúc component**:

```tsx
export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  async function loadUsers() {
    setLoading(true);
    try {
      const data = await apiRequest<{ users: User[] }>('/v1/admin/users');
      setUsers(data.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lỗi tải users');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadUsers(); }, []);

  async function handleDelete(userId: string) {
    if (!confirm(`Xóa user "${userId}"?`)) return;
    try {
      await apiRequest(`/v1/admin/users/${userId}`, { method: 'DELETE' });
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xóa thất bại');
    }
  }

  // render: header + nút + bảng users + 2 modal
}
```

**Bảng Users** — các cột: `user_id`, `email`, `department`, `roles` (hiển thị dạng badge), `ldap_groups`, [Sửa] [Xóa].

**Form tạo user** (Modal `CreateUserModal`):
```
Trường:
- user_id: text, bắt buộc, lowercase + dấu gạch dưới/chấm, pattern: /^[a-z0-9._-]+$/
- email: email input, bắt buộc
- department: text, bắt buộc
- roles: multi-checkbox với options: ['admin', 'data_owner', 'user']
- ldap_groups: text input dạng comma-separated → split thành array khi submit

Submit: POST /v1/admin/users
Sau khi thành công: đóng modal + reload users
Error: hiện trong modal
```

**Form sửa user** (Modal `EditUserModal`) — fields tương tự, bắt đầu với giá trị hiện tại:
```
Submit: PATCH /v1/admin/users/{user_id}
Chỉ gửi fields thay đổi (partial update)
```

**Import CSV** (Modal `ImportModal`):
```
Bước 1: Textarea nhập CSV hoặc upload file .csv
  Format: user_id,email,department,roles (comma-sep), ldap_groups (comma-sep)
  Nút "Xem trước" → POST /v1/admin/users/import/preview → hiện số dòng hợp lệ/lỗi
Bước 2: Nếu preview OK → nút "Xác nhận import"
  → POST /v1/admin/users/import/commit
  → Hiện kết quả: "Đã import N users"
  → Đóng modal + reload
```

**LDAP Sync**: Nút "Đồng bộ LDAP" bên cạnh "Tạo user". Khi click:
```
1. GET /v1/admin/users/sync-status → kiểm tra status
2. Nếu user muốn sync thủ công: POST /v1/admin/users/ldap-sync với body { updates: [], interval_minutes: null }
   (updates rỗng = trigger sync từ LDAP server, backend tự pull)
3. Hiện toast: "Đồng bộ hoàn tất: N users"
```

---

### 5.3 `RolesPage.tsx`

**Endpoints**:
- `GET /v1/admin/roles` → `{ roles: Role[], total: number }` (chỉ `admin` role được gọi)
- `POST /v1/admin/roles` body: `{ name, schema_allowlist: string[], description?, data_source_names: string[], metric_allowlist: string[] }`

**Type Role**:
```ts
type Role = {
  name: string;
  description: string | null;
  schema_allowlist: string[];
  data_source_names: string[];
  metric_allowlist: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  cerbos_policy_status: string;
  data_source_config_status: string;
};
```

**Lưu ý quan trọng**: Không có DELETE và PATCH endpoint cho roles trong backend. Chỉ có GET và POST. **Không vẽ nút Xóa/Sửa** cho roles — chỉ hiển thị danh sách và cho phép tạo mới.

**Layout**:
```
Header: "Quản lý vai trò" + nút [+ Tạo vai trò]

Danh sách roles dạng card grid (2 cột):
┌────────────────────────────────┐
│ admin                          │
│ Schema: FIN_PROD, HR_SCHEMA    │
│ Data sources: 2                │
│ Metrics: 5                     │
│ Cerbos: synced ✓               │
│ Tạo bởi: system · 2026-01-01  │
└────────────────────────────────┘
```

**Form tạo role** (Modal):
```
- name: text, bắt buộc, pattern /^[a-z0-9_]+$/
- description: textarea, tùy chọn
- schema_allowlist: text input, comma-separated (vd: "FIN_PROD, HR_SCHEMA")
  → split và trim khi submit
- data_source_names: text input, comma-separated
- metric_allowlist: text input, comma-separated

Submit: POST /v1/admin/roles
Sau thành công: đóng modal + reload
```

---

### 5.4 `DataSourcesPage.tsx`

**Endpoints**:
- `GET /v1/admin/data-sources` → `{ data_sources: DataSource[], total: number }`
- `GET /v1/admin/data-sources/{name}` → `{ data_source: DataSource, query_execution: object }`
- `POST /v1/admin/data-sources` body: xem bên dưới
- `PATCH /v1/admin/data-sources/{name}` body: xem bên dưới

**KHÔNG CÓ DELETE endpoint**. Không hiện nút xóa.

**Type DataSource** (từ `DataSourceCreateRequest`):
```ts
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
  status: string;  // 'active' | 'error' | 'unreachable'
};
```

**Layout**:
```
Header: "Nguồn dữ liệu Oracle" + nút [+ Thêm nguồn dữ liệu]

Danh sách dạng card:
┌────────────────────────────────────────────────┐
│ 🟢 Oracle_Finance                              │
│    Host: oracle-fin:1521 | Schema: FIN_PROD    │
│    Timeout: 30s | Row limit: 50,000            │
│    [Sửa cấu hình]                              │
└────────────────────────────────────────────────┘
```

Status indicator: `status === 'active'` → 🟢, `'error'` → 🔴, `'unreachable'` → 🟡, mặc định → ⚪.

**Form tạo** (Modal — 1 bước, không phân bước):
```
- name: text, bắt buộc
- description: text, tùy chọn
- host: text, bắt buộc
- port: number, default 1521
- service_name: text, bắt buộc
- username: text, bắt buộc
- password: password input, bắt buộc
- schema_allowlist: textarea, mỗi dòng một schema (split by newline khi submit)
- query_timeout_seconds: number, default 30
- row_limit: number, default 50000

Submit: POST /v1/admin/data-sources
Body: { name, description, host, port, service_name, username, password,
        schema_allowlist: string[], query_timeout_seconds, row_limit }
```

**Form sửa** (Modal, pre-fill từ DataSource hiện có):
```
Có thể sửa: description, host, port, service_name, username, password, 
            schema_allowlist, query_timeout_seconds, row_limit
Không sửa: name (key của data source, bất biến)

Submit: PATCH /v1/admin/data-sources/{name}
Chỉ gửi fields có giá trị (partial update — null = không đổi)
```

---

### 5.5 `AuditLogPage.tsx`

**Endpoints**:
- `GET /v1/admin/audit-logs` query params: `user_id`, `department_id`, `action`, `data_source`, `policy_decision`, `status`, `request_id`, `date_from`, `date_to`, `page`, `page_size`
- Response: `{ records: AuditRecord[], total: number, page: number, page_size: number }`
- `GET /v1/admin/audit-logs/export` — cùng params, trả CSV text (`Content-Type: text/csv`)
- `GET /v1/admin/audit-logs/{request_id}/lifecycle` → `{ request_id, events: AuditRecord[], event_count: number }`

**Type AuditRecord** (từ `AuditRecord.to_response_dict()`):
```ts
type AuditRecord = {
  request_id: string;
  user_id: string;
  department_id: string;
  session_id: string;
  timestamp: string; // ISO
  intent_type: string;
  sensitivity_tier: string;
  sql_hash: string | null;
  data_sources: string[];
  rows_returned: number;
  latency_ms: number;
  policy_decision: string; // 'ALLOW' | 'DENY'
  status: string; // 'SUCCESS' | 'ERROR'
  denial_reason: string | null;
  cerbos_rule: string | null;
  metadata: Record<string, unknown> | null;
};
```

**Layout**:
```
Bộ lọc (dòng):
[Từ ngày date] [Đến ngày date] [User ID text] [Action text] [Policy: ALLOW/DENY select] [Tìm kiếm]

Nút bên phải: [Xuất CSV]

Bảng (50 dòng/trang):
| Thời gian | User | Action (intent_type) | Data Source | Rows | Latency | Policy | Chi tiết |
| --------- | ---- | -------------------- | ----------- | ---- | ------- | ------ | -------- |
```

**Pagination**: `page` và `page_size=50`. Hiện "Trang X / Y" + nút [Trước] [Tiếp theo].

**Chi tiết** (Drawer phải, mở khi click "Chi tiết"):
```
- request_id (copy button)
- Thời gian đầy đủ
- User + Department
- action (intent_type)
- Data sources: badge list
- SQL hash (nếu có)
- Rows returned + Latency
- Policy decision: ALLOW (xanh) / DENY (đỏ)
- Denial reason (nếu có)
- Metadata: JSON.stringify với indent 2
- Nút [Xem lifecycle] → gọi /lifecycle endpoint, hiện list events
```

**Xuất CSV**:
```tsx
async function handleExportCsv() {
  const params = buildQueryParams(); // cùng params filter hiện tại
  const response = await fetch(`/v1/admin/audit-logs/export?${params}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
  });
  const text = await response.text();
  const blob = new Blob([text], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
```

**Lưu ý**: `apiRequest` wrapper có thể không handle text response — dùng `fetch` trực tiếp cho CSV download, thêm Authorization header thủ công từ `auth.session?.accessToken`.

---

## 6. Phase 3 — Analytics & Export (Dev C)

### 6.1 Export Button trong ChatAssistantConsole

**File cần sửa**: `apps/chat/src/components/epic6/ChatAssistantConsole.tsx`

**Bước 1**: Tìm nơi xử lý response của `POST /v1/chat/query`. Response có chứa `request_id`. Thêm `request_id` vào message state.

Tìm type message hiện tại (tên có thể khác nhau), thêm field:
```ts
type ChatMessage = {
  // ... các field hiện có ...
  request_id?: string;        // thêm field này
  has_table_result?: boolean; // thêm field này — true khi result là bảng data
};
```

Khi nhận response từ query API, map `response.request_id` vào message.

**Bước 2**: Tạo component `ExportButton`:

```tsx
type ExportFormat = 'csv' | 'excel' | 'pdf';

type ExportState =
  | { phase: 'idle' }
  | { phase: 'previewing' }
  | { phase: 'confirming'; preview: ExportPreview }
  | { phase: 'exporting'; jobId: string }
  | { phase: 'polling'; jobId: string }
  | { phase: 'done'; downloadUrl: string }
  | { phase: 'error'; message: string };

type ExportPreview = {
  request_id: string;
  format: string;
  estimated_row_count: number;
  sensitivity_tier: number;
  sensitivity_warning: string | null;
  department_scope: string;
};

type ExportJob = {
  job_id: string;
  status: string; // 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED'
  download_url: string | null;
  error: string | null;
};

function ExportButton({ requestId }: { requestId: string }) {
  const auth = useAuth();
  const [state, setState] = useState<ExportState>({ phase: 'idle' });
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('excel');

  async function handlePreview() {
    setState({ phase: 'previewing' });
    try {
      const preview = await apiRequest<ExportPreview>(
        `/v1/chat/query/${requestId}/export-preview?format=${selectedFormat}`,
      );
      setState({ phase: 'confirming', preview });
    } catch (err) {
      setState({ phase: 'error', message: err instanceof Error ? err.message : 'Lỗi xem trước' });
    }
  }

  async function handleConfirmExport(preview: ExportPreview) {
    try {
      const job = await apiRequest<{ job_id: string; status: string }>(
        `/v1/chat/query/${requestId}/export`,
        {
          method: 'POST',
          body: JSON.stringify({
            format: selectedFormat,
            human_review_confirmed: true, // BẮT BUỘC phải true, backend trả 400 nếu false
          }),
        },
      );
      setState({ phase: 'polling', jobId: job.job_id });
      void pollJobStatus(job.job_id);
    } catch (err) {
      setState({ phase: 'error', message: err instanceof Error ? err.message : 'Lỗi tạo export job' });
    }
  }

  async function pollJobStatus(jobId: string) {
    // Poll mỗi 2 giây, tối đa 30 lần (60 giây)
    for (let i = 0; i < 30; i++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      try {
        const job = await apiRequest<ExportJob>(`/v1/chat/exports/${jobId}`);
        if (job.status === 'DONE' && job.download_url) {
          setState({ phase: 'done', downloadUrl: job.download_url });
          triggerDownload(jobId);
          return;
        }
        if (job.status === 'FAILED') {
          setState({ phase: 'error', message: job.error ?? 'Export thất bại' });
          return;
        }
      } catch {
        // tiếp tục poll
      }
    }
    setState({ phase: 'error', message: 'Export timeout — thử lại sau' });
  }

  function triggerDownload(jobId: string) {
    // Dùng fetch với auth header để download file
    fetch(`/v1/chat/exports/${jobId}/download`, {
      headers: { Authorization: `Bearer ${auth.session?.accessToken}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const ext = selectedFormat === 'excel' ? 'xlsx' : selectedFormat;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `export-${requestId.slice(0, 8)}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => setState({ phase: 'error', message: 'Tải file thất bại' }));
  }

  // Render based on state.phase
  if (state.phase === 'idle') {
    return (
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.75rem' }}>
        <select
          value={selectedFormat}
          onChange={(e) => setSelectedFormat(e.target.value as ExportFormat)}
          style={{ padding: '0.4rem 0.6rem', borderRadius: '0.5rem', border: '1px solid rgba(117,94,60,0.2)', fontSize: '0.85rem' }}
        >
          <option value="csv">CSV</option>
          <option value="excel">Excel</option>
          <option value="pdf">PDF</option>
        </select>
        <button type="button" onClick={() => void handlePreview()} style={{ ...ghostButtonStyle, padding: '0.45rem 0.8rem', fontSize: '0.85rem' }}>
          Xuất kết quả
        </button>
      </div>
    );
  }

  if (state.phase === 'previewing') {
    return <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--color-neutral-500)' }}>Đang xem trước...</div>;
  }

  if (state.phase === 'confirming') {
    const { preview } = state;
    return (
      <div style={{ marginTop: '0.75rem', padding: '0.8rem', borderRadius: '0.75rem', background: 'rgba(246,241,232,0.9)', fontSize: '0.88rem' }}>
        <div>Xuất <strong>{preview.estimated_row_count} dòng</strong> dưới dạng <strong>{selectedFormat.toUpperCase()}</strong></div>
        {preview.sensitivity_warning && (
          <div style={{ color: '#92400e', marginTop: '0.3rem' }}>⚠ {preview.sensitivity_warning}</div>
        )}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem' }}>
          <button type="button" onClick={() => void handleConfirmExport(preview)} style={{ ...buttonStyle, padding: '0.45rem 0.8rem', fontSize: '0.85rem' }}>
            Xác nhận xuất
          </button>
          <button type="button" onClick={() => setState({ phase: 'idle' })} style={{ ...ghostButtonStyle, padding: '0.45rem 0.8rem', fontSize: '0.85rem' }}>
            Huỷ
          </button>
        </div>
      </div>
    );
  }

  if (state.phase === 'exporting' || state.phase === 'polling') {
    return <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--color-neutral-500)' }}>Đang tạo file xuất...</div>;
  }

  if (state.phase === 'done') {
    return (
      <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: '#166534' }}>
        ✓ Đã tải xuống.{' '}
        <button type="button" onClick={() => setState({ phase: 'idle' })} style={{ background: 'none', border: 'none', color: '#0f766e', cursor: 'pointer', textDecoration: 'underline' }}>
          Xuất lần nữa
        </button>
      </div>
    );
  }

  if (state.phase === 'error') {
    return (
      <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: '#991b1b' }}>
        {state.message}{' '}
        <button type="button" onClick={() => setState({ phase: 'idle' })} style={{ background: 'none', border: 'none', color: '#0f766e', cursor: 'pointer', textDecoration: 'underline' }}>
          Thử lại
        </button>
      </div>
    );
  }

  return null;
}
```

**Cách dùng trong ChatAssistantConsole** — sau mỗi assistant message có tabular data:
```tsx
{message.request_id && message.has_table_result && (
  <ExportButton requestId={message.request_id} />
)}
```

### 6.2 Forecast Download Button

**File cần sửa**: `apps/chat/src/components/epic7/ForecastStudio.tsx`

Tìm nơi `job.status === 'DONE'` (hoặc tương đương) — khi forecast hoàn tất. Thêm nút download:

```tsx
// Khi job done, thêm vào UI:
{jobStatus?.status === 'DONE' && jobId && (
  <button
    type="button"
    onClick={() => void handleDownload()}
    style={{ ...ghostButtonStyle, marginTop: '0.8rem' }}
  >
    Tải kết quả dự báo
  </button>
)}

async function handleDownload() {
  // jobId phải là state hiện tại trong ForecastStudio
  const res = await fetch(`/v1/forecast/${jobId}/download`, {
    headers: { Authorization: `Bearer ${auth.session?.accessToken}` },
  });
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') ?? '';
  const filename = disposition.match(/filename="(.+)"/)?.[1] ?? `forecast-${jobId}.xlsx`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

Import `useAuth` để lấy `auth.session?.accessToken`.

### 6.3 Trend Export (Client-side với xlsx)

**Cài package**:
```
pnpm -F chat add xlsx
```

**File cần sửa**: `apps/chat/src/components/epic7/TrendAnalysisPanel.tsx`

Tìm nơi hiện thị kết quả trend (drilldown array trong response). Thêm nút export:

```tsx
import * as XLSX from 'xlsx';

// Sau khi có result data, thêm:
{trendResult && trendResult.drilldown?.length > 0 && (
  <button type="button" onClick={handleExcelExport} style={{ ...ghostButtonStyle, marginTop: '0.8rem' }}>
    Xuất Excel
  </button>
)}

function handleExcelExport() {
  // trendResult.drilldown là array of objects từ API response
  const ws = XLSX.utils.json_to_sheet(trendResult.drilldown);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Trend Analysis');
  XLSX.writeFile(wb, `trend-${new Date().toISOString().slice(0, 10)}.xlsx`);
}
```

---

## 7. Những Thứ KHÔNG Làm Sprint Này

| Tính năng | Lý do | Khi nào làm |
|---|---|---|
| Approvals page | Không có backend REST endpoint | Sprint sau — cần thêm route vào `admin.py` trước |
| Security page (Guardrails + Data Masking) | Config hardcode, không có CRUD endpoint | Sprint sau — cần thiết kế DB schema |
| Delete data source | Không có DELETE endpoint trong backend | Sprint sau |
| Update roles (PATCH) | Không có PATCH endpoint cho roles | Sprint sau |

---

## 8. Checklist Trước Khi Merge

### Tất cả

- [ ] `pnpm -F chat build` — không có TypeScript error
- [ ] `pnpm -F chat check-types` — pass (nếu script này có)
- [ ] Không còn file nào import `Epic5BWorkspace`
- [ ] `/` redirect về `/chat` khi đã login
- [ ] `/` redirect về `/login` khi chưa login
- [ ] `/admin/*` với user role `user` → redirect về `/chat`
- [ ] Sidebar active state highlight đúng route hiện tại

### Dev B

- [ ] `GET /v1/admin/users` — dữ liệu hiện đúng trong bảng
- [ ] Tạo user → user xuất hiện trong danh sách ngay
- [ ] Xóa user → xác nhận trước khi xóa, soft delete
- [ ] Role create form: `name` validate pattern `/^[a-z0-9_]+$/`
- [ ] Data source: Không có nút Delete
- [ ] Audit log: CSV download thực sự tạo file có data
- [ ] Audit lifecycle drawer: hiển thị đúng các events

### Dev C

- [ ] Export button chỉ hiện khi message có `request_id` VÀ `has_table_result`
- [ ] `human_review_confirmed: true` trong body POST export — nếu thiếu sẽ nhận 400
- [ ] Poll loop dừng sau max 30 lần (60 giây)
- [ ] Forecast download: filename lấy từ `Content-Disposition` header
- [ ] Trend export: package `xlsx` đã được thêm vào `package.json`
- [ ] Analytics tab navigation active highlight đúng

---

## 9. Thứ Tự Làm Việc

```
Ngày 1 (sáng):  Dev A làm Bước 0 (3.1→3.3) — shared foundation
                Dev B & C đọc spec, xem code backend, cài xlsx

Ngày 1 (chiều): Dev A làm Phase 1 (4.1→4.12)
                Dev B bắt đầu AdminDashboard + UsersPage khi Dev A push Bước 0
                Dev C bắt đầu Analytics routes (4.6→4.9) — không cần chờ Dev A

Ngày 2:         Dev A làm 4.13 (dọn dẹp Epic5BWorkspace)
                Dev B làm RolesPage + DataSourcesPage
                Dev C làm ExportButton trong ChatAssistantConsole

Ngày 3:         Dev B làm AuditLogPage
                Dev C làm ForecastDownload + TrendExport

Ngày 4:         Dev A integration review, fix routing issues
                Dev B & C testing + checklist
                Merge
```
