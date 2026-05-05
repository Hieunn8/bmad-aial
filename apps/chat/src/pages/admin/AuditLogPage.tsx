import { useEffect, useMemo, useState } from 'react';
import { API_BASE, apiRequest } from '../../api/client';
import { useAuth } from '../../auth/AuthProvider';
import { buttonStyle, ghostButtonStyle, inputStyle } from '../../styles/shared';
import { AdminPageShell, adminCard, cellStyle, tableStyle } from './AdminShared';

type AuditRecord = {
  request_id: string;
  user_id: string;
  department_id: string;
  session_id: string;
  timestamp: string;
  intent_type: string;
  sensitivity_tier: string;
  sql_hash: string | null;
  data_sources: string[];
  rows_returned: number;
  latency_ms: number;
  policy_decision: string;
  status: string;
  denial_reason: string | null;
  cerbos_rule: string | null;
  metadata: Record<string, unknown> | null;
};

type AuditResponse = { records: AuditRecord[]; total: number; page: number; page_size: number };

export function AuditLogPage(): React.JSX.Element {
  const auth = useAuth();
  const [filters, setFilters] = useState({ date_from: '', date_to: '', user_id: '', action: '', policy_decision: '' });
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AuditRecord | null>(null);
  const [lifecycle, setLifecycle] = useState<AuditRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const params = useMemo(() => {
    const next = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value) next.set(key, value);
    }
    next.set('page', String(page));
    next.set('page_size', '50');
    return next;
  }, [filters, page]);

  async function load(): Promise<void> {
    const data = await apiRequest<AuditResponse>(`/v1/admin/audit-logs?${params.toString()}`);
    setRecords(data.records);
    setTotal(data.total);
  }

  useEffect(() => {
    void load().catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Không tải được audit log'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  async function handleExportCsv(): Promise<void> {
    const exportParams = new URLSearchParams(params);
    exportParams.delete('page');
    exportParams.delete('page_size');
    const response = await fetch(`${API_BASE}/v1/admin/audit-logs/export?${exportParams.toString()}`, {
      headers: auth.session?.accessToken ? { Authorization: `Bearer ${auth.session.accessToken}` } : undefined,
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

  async function loadLifecycle(requestId: string): Promise<void> {
    const data = await apiRequest<{ events: AuditRecord[] }>(`/v1/admin/audit-logs/${encodeURIComponent(requestId)}/lifecycle`);
    setLifecycle(data.events);
  }

  const totalPages = Math.max(1, Math.ceil(total / 50));

  return (
    <AdminPageShell title="Audit Log - Nhật ký kiểm toán" actions={<button type="button" style={ghostButtonStyle} onClick={() => void handleExportCsv()}>Xuất CSV</button>}>
      {error && <div role="alert" style={{ ...adminCard, color: '#991b1b', marginBottom: '1rem' }}>{error}</div>}
      <div style={{ ...adminCard, display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: '0.8rem', marginBottom: '1rem' }}>
        <input type="date" value={filters.date_from} onChange={(event) => { setPage(1); setFilters((current) => ({ ...current, date_from: event.target.value })); }} style={inputStyle} />
        <input type="date" value={filters.date_to} onChange={(event) => { setPage(1); setFilters((current) => ({ ...current, date_to: event.target.value })); }} style={inputStyle} />
        <input value={filters.user_id} onChange={(event) => { setPage(1); setFilters((current) => ({ ...current, user_id: event.target.value })); }} style={inputStyle} placeholder="Mã người dùng (User ID)" />
        <input value={filters.action} onChange={(event) => { setPage(1); setFilters((current) => ({ ...current, action: event.target.value })); }} style={inputStyle} placeholder="Hành động (Action)" />
        <select value={filters.policy_decision} onChange={(event) => { setPage(1); setFilters((current) => ({ ...current, policy_decision: event.target.value })); }} style={inputStyle}>
          <option value="">Policy - Quyết định</option>
          <option value="ALLOW">ALLOW</option>
          <option value="DENY">DENY</option>
        </select>
        <button type="button" style={buttonStyle} onClick={() => void load()}>Tìm kiếm</button>
      </div>
      <div style={adminCard}>
        <table style={tableStyle}>
          <thead>
            <tr><th style={cellStyle}>Thời gian</th><th style={cellStyle}>Người dùng</th><th style={cellStyle}>Hành động</th><th style={cellStyle}>Nguồn dữ liệu</th><th style={cellStyle}>Dòng</th><th style={cellStyle}>Độ trễ</th><th style={cellStyle}>Policy</th><th style={cellStyle}>Chi tiết</th></tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={`${record.request_id}-${record.timestamp}`}>
                <td style={cellStyle}>{new Date(record.timestamp).toLocaleString('vi-VN')}</td>
                <td style={cellStyle}>{record.user_id}</td>
                <td style={cellStyle}>{record.intent_type}</td>
                <td style={cellStyle}>{record.data_sources.join(', ')}</td>
                <td style={cellStyle}>{record.rows_returned}</td>
                <td style={cellStyle}>{record.latency_ms}ms</td>
                <td style={{ ...cellStyle, color: record.policy_decision === 'ALLOW' ? '#166534' : '#991b1b', fontWeight: 700 }}>{record.policy_decision}</td>
                <td style={cellStyle}><button type="button" style={ghostButtonStyle} onClick={() => { setSelected(record); setLifecycle([]); }}>Chi tiết</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button type="button" style={ghostButtonStyle} disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</button>
          <span>Trang {page} / {totalPages}</span>
          <button type="button" style={ghostButtonStyle} disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>Tiếp theo</button>
        </div>
      </div>
      {selected && (
        <aside style={{ position: 'fixed', top: 'var(--header-height)', right: 0, bottom: 0, width: '30rem', overflowY: 'auto', background: 'white', borderLeft: '1px solid rgba(117,94,60,0.16)', padding: '1.2rem', zIndex: 20, boxShadow: '-18px 0 40px rgba(99,74,45,0.12)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Chi tiết audit</h2>
            <button type="button" style={ghostButtonStyle} onClick={() => setSelected(null)}>Đóng</button>
          </div>
          <dl style={{ display: 'grid', gap: '0.7rem', marginTop: '1rem' }}>
            <dt>Request ID</dt><dd>{selected.request_id} <button type="button" onClick={() => void navigator.clipboard.writeText(selected.request_id)}>Sao chép</button></dd>
            <dt>Thời gian</dt><dd>{new Date(selected.timestamp).toLocaleString('vi-VN')}</dd>
            <dt>Người dùng / Phòng ban</dt><dd>{selected.user_id} / {selected.department_id}</dd>
            <dt>Hành động</dt><dd>{selected.intent_type}</dd>
            <dt>Nguồn dữ liệu</dt><dd>{selected.data_sources.join(', ')}</dd>
            <dt>SQL hash</dt><dd>{selected.sql_hash ?? 'none'}</dd>
            <dt>Dòng / Độ trễ</dt><dd>{selected.rows_returned} / {selected.latency_ms}ms</dd>
            <dt>Policy</dt><dd style={{ color: selected.policy_decision === 'ALLOW' ? '#166534' : '#991b1b', fontWeight: 700 }}>{selected.policy_decision}</dd>
            {selected.denial_reason && <><dt>Lý do từ chối</dt><dd>{selected.denial_reason}</dd></>}
          </dl>
          <pre style={{ borderRadius: '0.9rem', background: 'rgba(26,31,44,0.94)', color: '#d7f9f1', padding: '0.9rem', whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(selected.metadata ?? {}, null, 2)}
          </pre>
          <button type="button" style={buttonStyle} onClick={() => void loadLifecycle(selected.request_id)}>Xem lifecycle</button>
          {lifecycle.map((event) => (
            <div key={`${event.request_id}-${event.timestamp}-${event.intent_type}`} style={{ marginTop: '0.7rem', borderRadius: '0.9rem', background: 'rgba(246,241,232,0.82)', padding: '0.8rem' }}>
              <strong>{event.intent_type}</strong>
              <div>{new Date(event.timestamp).toLocaleString('vi-VN')} - {event.status}</div>
            </div>
          ))}
        </aside>
      )}
    </AdminPageShell>
  );
}
