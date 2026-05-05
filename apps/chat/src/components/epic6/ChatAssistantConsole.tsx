import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SSEErrorEvent, SSEEvent, SSESource } from '@aial/types';
import { ExportConfirmationBar } from '@aial/ui/export-confirmation-bar';
import { ConfidenceBreakdownCard } from '@aial/ui/confidence-breakdown-card';
import { ProvenanceDrawer, ProvenanceSection } from '@aial/ui/provenance-drawer';
import { useSSEStream } from '../../hooks/useSSEStream';
import { ProgressiveDataTable } from '../streaming/ProgressiveDataTable';
import { API_BASE, apiRequest } from '../../api/client';

type ExportFormat = 'csv' | 'xlsx' | 'pdf';

type QueryHandle = {
  request_id: string;
  status: string;
  trace_id: string;
  message?: string | null;
  cache_hit?: boolean;
  cache_timestamp?: string | null;
  freshness_indicator?: string | null;
  cache_similarity?: number | null;
  force_refresh_available?: boolean;
};

type ExportPreview = {
  request_id: string;
  format: ExportFormat;
  estimated_row_count: number;
  sensitivity_tier: number;
  sensitivity_warning?: string | null;
  department_scope: string;
};

type ExportJobHandle = {
  job_id: string;
  status: string;
  queue_name: string;
  task_name: string;
};

type ExportJobStatus = {
  job_id: string;
  request_id: string;
  status: string;
  format: ExportFormat;
  row_count: number;
  department_scope: string;
  sensitivity_tier: number;
  download_url?: string | null;
  expires_at?: string | null;
  error?: string | null;
};

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

type CacheState = {
  cacheHit: boolean;
  freshnessIndicator: string | null;
  cacheSimilarity: number | null;
  cacheTimestamp: string | null;
  forceRefreshAvailable: boolean;
};

type CrossDomainConflictState = {
  open: boolean;
  detail: string | null;
  provenance: Array<{
    source: string;
    domain: string;
    department_code: string;
    period_key: string;
    value_label: string;
    value: number;
  }>;
};

type CitationDrawerState = {
  open: boolean;
  sources: SSESource[];
};

const initialCacheState: CacheState = {
  cacheHit: false,
  freshnessIndicator: null,
  cacheSimilarity: null,
  cacheTimestamp: null,
  forceRefreshAvailable: false,
};

function buildCacheState(source?: Partial<QueryHandle> | Partial<Extract<SSEEvent, { type: 'done' }>>): CacheState {
  return {
    cacheHit: source?.cache_hit ?? false,
    freshnessIndicator: source?.freshness_indicator ?? null,
    cacheSimilarity: source?.cache_similarity ?? null,
    cacheTimestamp: source?.cache_timestamp ?? null,
    forceRefreshAvailable: source?.force_refresh_available ?? false,
  };
}

export function ChatAssistantConsole(): React.JSX.Element {
  const [query, setQuery] = useState('Doanh thu HCM thang nay');
  const [requestId, setRequestId] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [answer, setAnswer] = useState('');
  const [exportFormat, setExportFormat] = useState<ExportFormat>('xlsx');
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [jobStatus, setJobStatus] = useState<ExportJobStatus | null>(null);
  const [jobHandle, setJobHandle] = useState<ExportJobHandle | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamPath, setStreamPath] = useState('');
  const [cacheState, setCacheState] = useState<CacheState>(initialCacheState);
  const [conflictState, setConflictState] = useState<CrossDomainConflictState>({
    open: false,
    detail: null,
    provenance: [],
  });
  const [citationState, setCitationState] = useState<CitationDrawerState>({
    open: false,
    sources: [],
  });

  const handleStreamEvent = useCallback((event: SSEEvent) => {
    if (event.type === 'row') {
      setRows((current) => [...current, ...event.rows]);
      return;
    }
    if (event.type === 'done') {
      setAnswer(event.answer ?? '');
      setCitationState({
        open: false,
        sources: event.sources ?? [],
      });
      setCacheState((current) => ({
        ...current,
        ...buildCacheState(event),
      }));
      if (event.confidence_state === 'cross-source-conflict') {
        setConflictState({
          open: false,
          detail: event.conflict_detail ?? null,
          provenance: event.provenance ?? [],
        });
      }
    }
  }, []);

  const handleStreamError = useCallback((streamError: SSEErrorEvent) => {
    setError(streamError.message);
  }, []);

  const { state: streamState, connect, reset } = useSSEStream<SSEEvent>(streamPath, {
    autoConnect: false,
    onEvent: handleStreamEvent,
    onError: handleStreamError,
  });

  useEffect(() => {
    if (streamPath) {
      connect();
    }
  }, [streamPath, connect]);

  useEffect(() => {
    if (!jobHandle?.job_id) {
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const nextStatus = await apiRequest<ExportJobStatus>(`/v1/chat/exports/${jobHandle.job_id}`);
        if (cancelled) {
          return;
        }
        setJobStatus(nextStatus);
        if (nextStatus.status === 'completed') {
          setStatusMessage('Bao cao da san sang. Ban co the tai xuong trong 24 gio.');
          return;
        }
        if (nextStatus.status === 'failed' || nextStatus.status === 'expired') {
          setError(nextStatus.error ?? 'Export job không thành công');
          return;
        }
        window.setTimeout(() => {
          void poll();
        }, 1200);
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError instanceof Error ? pollError.message : 'Không thể kiểm tra export job');
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, [jobHandle]);

  const visibleRowCount = useMemo(() => rows.length, [rows]);

  async function handleRunQuery(forceRefresh = false): Promise<void> {
    setError(null);
    setStatusMessage(null);
    setPreview(null);
    setShowConfirmation(false);
    setJobHandle(null);
    setJobStatus(null);
    setRows([]);
    setAnswer('');
    setCacheState(initialCacheState);
    setConflictState({ open: false, detail: null, provenance: [] });
    setCitationState({ open: false, sources: [] });
    reset();

    try {
      const handle = await apiRequest<QueryHandle>('/v1/chat/query', {
        method: 'POST',
        body: JSON.stringify({
          query,
          session_id: crypto.randomUUID(),
          force_refresh: forceRefresh,
        }),
      });
      setRequestId(handle.request_id);
      setStatusMessage(handle.message ?? 'Đang stream kết quả truy vấn...');
      setCacheState(buildCacheState(handle));
      setStreamPath(`/v1/chat/stream/${handle.request_id}`);
    } catch (queryError) {
      setError(queryError instanceof Error ? queryError.message : 'Không thể chạy truy vấn');
    }
  }

  async function handlePrepareExport(): Promise<void> {
    if (!requestId) {
      return;
    }
    setError(null);
    try {
      const nextPreview = await apiRequest<ExportPreview>(
        `/v1/chat/query/${requestId}/export-preview?format=${exportFormat}`,
      );
      setPreview(nextPreview);
      setShowConfirmation(true);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : 'Không thể tạo export preview');
    }
  }

  async function handleConfirmExport(): Promise<void> {
    if (!requestId) {
      return;
    }
    setError(null);
    setShowConfirmation(false);
    try {
      const job = await apiRequest<ExportJobHandle>(`/v1/chat/query/${requestId}/export`, {
        method: 'POST',
        body: JSON.stringify({
          format: exportFormat,
          human_review_confirmed: true,
        }),
      });
      setJobHandle(job);
      setStatusMessage(`Export job ${job.job_id} dang o hang doi ${job.queue_name}.`);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : 'Không thể tạo export job');
    }
  }

  return (
    <section id="chat-assistant" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Chat Assistant</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            Ask a governed question, receive a text answer with evidence, then export the structured result only if needed.
          </p>
        </div>
        <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
          {streamState.status === 'idle' ? 'Idle' : `Stream: ${streamState.status}`}
        </div>
      </div>

      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.85rem', gridTemplateColumns: '1fr auto' }}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={inputStyle}
          placeholder="Nhập câu hỏi cần giải đáp từ dữ liệu và tài liệu nội bộ"
        />
        <button type="button" style={buttonStyle} onClick={() => void handleRunQuery()}>
          Ask AI
        </button>
      </div>

      {cacheState.cacheHit ? (
        <div
          role="status"
          aria-label="Cache freshness"
          style={{
            marginTop: '0.85rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1rem',
            borderRadius: '1rem',
            background: 'rgba(217, 249, 157, 0.35)',
            border: '1px solid rgba(101, 163, 13, 0.24)',
            color: '#3f6212',
            padding: '0.85rem 0.95rem',
          }}
        >
          <div>
            <div style={{ fontWeight: 700 }}>Kết quả từ cache</div>
            <div style={{ marginTop: '0.2rem', fontSize: '0.92rem' }}>
              {cacheState.freshnessIndicator ?? 'Dữ liệu được phục vụ từ semantic cache.'}
            </div>
            {typeof cacheState.cacheSimilarity === 'number' ? (
              <div style={{ marginTop: '0.18rem', fontSize: '0.84rem', opacity: 0.88 }}>
                Độ tương đồng ngữ nghĩa: {(cacheState.cacheSimilarity * 100).toFixed(0)}%
              </div>
            ) : null}
          </div>
          {cacheState.forceRefreshAvailable ? (
            <button type="button" style={ghostButtonStyle} onClick={() => void handleRunQuery(true)}>
              Tải lại dữ liệu mới
            </button>
          ) : null}
        </div>
      ) : null}

      {(statusMessage || error) && (
        <div
          role={error ? 'alert' : 'status'}
          style={{
            marginTop: '1rem',
            borderRadius: '1rem',
            background: error ? 'rgba(153, 27, 27, 0.08)' : 'rgba(15,118,110,0.08)',
            color: error ? '#991b1b' : '#115e59',
            padding: '0.85rem 0.95rem',
          }}
        >
          {error ?? statusMessage}
        </div>
      )}

      <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1.35fr 0.85fr' }}>
        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.88)', padding: '1.05rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
              <div>
                <div style={{ fontWeight: 700 }}>Answer</div>
                <div style={{ marginTop: '0.25rem', color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                  Natural-language response synthesized from the current stream.
                </div>
              </div>
              {citationState.sources.length > 0 ? (
                <button
                  type="button"
                  style={ghostButtonStyle}
                  onClick={() => setCitationState((current) => ({ ...current, open: true }))}
                >
                  View citations
                </button>
              ) : null}
            </div>
            <p style={{ margin: '0.8rem 0 0', color: 'var(--color-neutral-700)', lineHeight: 1.7, minHeight: '7rem' }}>
              {answer || 'Cau tra loi se xuat hien khi stream done event ve toi client.'}
            </p>
            {cacheState.cacheTimestamp ? (
              <div style={{ marginTop: '0.7rem', color: 'var(--color-neutral-500)', fontSize: '0.84rem' }}>
                Cached at {cacheState.cacheTimestamp}
              </div>
            ) : null}
          </div>

          <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '0.8rem' }}>
              <strong>Structured rows</strong>
              <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>{visibleRowCount} rows buffered</span>
            </div>
            {rows.length === 0 ? (
              <div style={{ color: 'var(--color-neutral-500)' }}>No structured rows streamed yet.</div>
            ) : (
              <ProgressiveDataTable rows={rows} />
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Evidence</div>
            <div style={{ marginTop: '0.45rem', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
              {citationState.sources.length > 0
                ? `${citationState.sources.length} document citation(s) attached to this answer.`
                : 'No document citations attached to this answer yet.'}
            </div>
            {citationState.sources.length > 0 ? (
              <div style={{ marginTop: '0.8rem', display: 'grid', gap: '0.65rem' }}>
                {citationState.sources.slice(0, 3).map((source) => (
                  <div
                    key={`${source.doc_id}-${source.page}-${source.title}`}
                    style={{
                      borderRadius: '0.9rem',
                      background: 'rgba(15, 118, 110, 0.08)',
                      padding: '0.75rem 0.85rem',
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{source.title}</div>
                    <div style={{ marginTop: '0.2rem', color: 'var(--color-neutral-500)', fontSize: '0.86rem' }}>
                      Document {source.doc_id} · Page {source.page}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Export report</div>
            <div style={{ marginTop: '0.45rem', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
              {jobStatus?.status === 'completed'
                ? `Ready for download until ${jobStatus.expires_at ?? '24h'}`
                : jobHandle?.status === 'queued'
                  ? `Queued on ${jobHandle.queue_name}`
                  : 'Optional step after reviewing the answer and rows.'}
            </div>
            <div style={{ marginTop: '0.8rem', display: 'grid', gap: '0.8rem' }}>
              <select
                value={exportFormat}
                onChange={(event) => setExportFormat(event.target.value as ExportFormat)}
                style={inputStyle}
                aria-label="Export format"
              >
                <option value="xlsx">Excel</option>
                <option value="pdf">PDF</option>
                <option value="csv">CSV</option>
              </select>
              <button
                type="button"
                style={ghostButtonStyle}
                onClick={() => void handlePrepareExport()}
                disabled={!requestId || rows.length === 0}
              >
                Generate report
              </button>
            </div>
            {jobStatus?.download_url ? (
              <a
                href={`${API_BASE}${jobStatus.download_url}`}
                style={{ display: 'inline-block', marginTop: '0.8rem', ...ghostButtonStyle, textDecoration: 'none' }}
              >
                Download report
              </a>
            ) : null}
          </div>

          {conflictState.detail ? (
            <ConfidenceBreakdownCard
              type="cross-source-conflict"
              detail={conflictState.detail}
              onActions={[
                {
                  label: 'Xem chi tiết nguồn lệch',
                  onClick: () => setConflictState((current) => ({ ...current, open: true })),
                },
                {
                  label: 'Loại trừ một nguồn',
                  onClick: () => setStatusMessage('Luồng re-query loại trừ nguồn sẽ được nối ở bước tiếp theo.'),
                },
                {
                  label: 'Tạo ticket cho Data Owner',
                  onClick: () => setStatusMessage('Đã ghi nhận yêu cầu tạo ticket cho Data Owner.'),
                },
              ]}
            />
          ) : null}
        </div>
      </div>

      {showConfirmation && preview ? (
        <ExportConfirmationBar
          format={preview.format}
          rowCount={preview.estimated_row_count}
          sensitivityWarning={preview.sensitivity_warning ?? undefined}
          onConfirm={() => void handleConfirmExport()}
          onCancel={() => setShowConfirmation(false)}
        />
      ) : null}

      <ProvenanceDrawer
        open={citationState.open}
        onClose={() => setCitationState((current) => ({ ...current, open: false }))}
      >
        <ProvenanceSection title="Document citations">
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {citationState.sources.map((source) => (
              <div
                key={`${source.doc_id}-${source.page}-${source.title}`}
                style={{
                  borderRadius: '0.9rem',
                  border: '1px solid rgba(117, 94, 60, 0.16)',
                  background: 'rgba(255,255,255,0.78)',
                  padding: '0.85rem 0.9rem',
                }}
              >
                <div style={{ fontWeight: 700 }}>{source.title}</div>
                <div style={{ marginTop: '0.25rem', color: 'var(--color-neutral-600)', fontSize: '0.92rem' }}>
                  Document ID: {source.doc_id}
                </div>
                <div style={{ marginTop: '0.35rem' }}>
                  Page <strong>{source.page}</strong>
                </div>
              </div>
            ))}
          </div>
        </ProvenanceSection>
      </ProvenanceDrawer>

      <ProvenanceDrawer
        open={conflictState.open}
        onClose={() => setConflictState((current) => ({ ...current, open: false }))}
      >
        <ProvenanceSection title="Nguồn lệch">
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {conflictState.provenance.map((entry, index) => (
              <div
                key={`${entry.source}-${entry.value_label}-${index}`}
                style={{
                  borderRadius: '0.9rem',
                  border: '1px solid rgba(117, 94, 60, 0.16)',
                  background: 'rgba(255,255,255,0.78)',
                  padding: '0.85rem 0.9rem',
                }}
              >
                <div style={{ fontWeight: 700 }}>{entry.source}</div>
                <div style={{ marginTop: '0.25rem', color: 'var(--color-neutral-600)', fontSize: '0.92rem' }}>
                  {entry.domain} · {entry.department_code} · {entry.period_key}
                </div>
                <div style={{ marginTop: '0.35rem' }}>
                  {entry.value_label}: <strong>{entry.value}B</strong>
                </div>
              </div>
            ))}
          </div>
        </ProvenanceSection>
      </ProvenanceDrawer>
    </section>
  );
}
