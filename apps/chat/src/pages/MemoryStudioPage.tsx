import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import { buttonStyle, cardStyle, ghostButtonStyle, inputStyle, pageShell, pageTitle } from '../styles/shared';

type Suggestion = { type: 'kpi' | 'template'; label: string; uses?: number; template_id?: string };
type SavedTemplate = {
  template_id: string;
  name: string;
  query_intent: string;
  filters: string;
  time_range: string;
  output_format: string;
  created_at: string;
};
type HistoryEntry = {
  entry_id: string;
  created_at: string;
  intent_type: string;
  topic: string;
  filter_context: string;
  key_result_summary: string;
};
type MemoryViolation = { user_id: string; entry_type: string; field: string };
type MemoryContextBundle = {
  summaries: Array<{
    summary_id: string;
    topic: string;
    filter_context: string;
    summary_text: string;
    created_at: string;
  }>;
  token_budget_increase_percent: number;
  threshold: number;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
}

export function MemoryStudioPage(): React.JSX.Element {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [templates, setTemplates] = useState<SavedTemplate[]>([]);
  const [historyEntries, setHistoryEntries] = useState<HistoryEntry[]>([]);
  const [memoryAudit, setMemoryAudit] = useState<MemoryViolation[]>([]);
  const [memoryProbe, setMemoryProbe] = useState<MemoryContextBundle | null>(null);
  const [contextQuery, setContextQuery] = useState('monthly revenue trend');
  const [historyKeyword, setHistoryKeyword] = useState('');
  const [historyTopic, setHistoryTopic] = useState('');
  const [draftPrompt, setDraftPrompt] = useState('');
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [templateForm, setTemplateForm] = useState({
    name: 'Revenue Monthly',
    query_intent: 'revenue trend',
    filters: 'month filter',
    time_range: 'last_30_days',
    output_format: 'table',
  });

  async function loadMemorySurfaces(): Promise<void> {
    const [suggestionData, templateData, auditData] = await Promise.all([
      apiRequest<{ suggestions: Suggestion[] }>('/v1/chat/suggestions'),
      apiRequest<{ templates: SavedTemplate[] }>('/v1/chat/templates'),
      apiRequest<{ violations: MemoryViolation[] }>('/v1/chat/history/audit'),
    ]);
    setSuggestions(suggestionData.suggestions);
    setTemplates(templateData.templates);
    setMemoryAudit(auditData.violations);
  }

  async function probeContext(query: string): Promise<void> {
    const data = await apiRequest<MemoryContextBundle>(`/v1/chat/memory/context?query=${encodeURIComponent(query)}`);
    setMemoryProbe(data);
  }

  async function loadHistory(): Promise<void> {
    const params = new URLSearchParams();
    if (historyKeyword.trim()) params.set('keyword', historyKeyword.trim());
    if (historyTopic.trim()) params.set('topic', historyTopic.trim());
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const data = await apiRequest<{ results: HistoryEntry[] }>(`/v1/chat/history/search${suffix}`);
    setHistoryEntries(data.results);
  }

  async function handleSaveTemplate(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest<{ template: SavedTemplate }>('/v1/chat/templates', {
        method: 'POST',
        body: JSON.stringify(templateForm),
      });
      setFlash(`Đã lưu mẫu ${templateForm.name}`);
      await loadMemorySurfaces();
    } catch (templateError) {
      setError(templateError instanceof Error ? templateError.message : 'Lưu mẫu thất bại');
    }
  }

  async function handleReuse(entryId: string): Promise<void> {
    setError(null);
    try {
      const data = await apiRequest<{ preload: { topic: string; filters: string; intent_type: string } }>(
        `/v1/chat/history/${encodeURIComponent(entryId)}/reuse`,
        { method: 'POST' },
      );
      setDraftPrompt(`${data.preload.topic} | ${data.preload.filters}`);
      setFlash('Đã nạp lại intent vào khung soạn thảo');
    } catch (reuseError) {
      setError(reuseError instanceof Error ? reuseError.message : 'Không dùng lại được truy vấn');
    }
  }

  useEffect(() => {
    void Promise.all([loadMemorySurfaces(), loadHistory(), probeContext(contextQuery)]).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Không tải được Memory Studio');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section style={pageShell}>
      <h1 style={pageTitle}>Memory Studio</h1>
      <p style={{ margin: '0.45rem 0 1.2rem', color: 'var(--color-neutral-600)' }}>
        Kiểm tra selective recall, saved templates, suggestions và lịch sử hội thoại.
      </p>
      {(flash || error) && (
        <div role={error ? 'alert' : 'status'} style={{ ...cardStyle, padding: '0.9rem 1rem', marginBottom: '1rem', color: error ? '#991b1b' : '#115e59' }}>
          {error ?? flash}
        </div>
      )}
      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: '1.2fr 0.8fr' }}>
        <section style={{ ...cardStyle, padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Context probe - Kiểm tra ngữ cảnh</h2>
            <button type="button" style={ghostButtonStyle} onClick={() => void probeContext(contextQuery)}>Probe</button>
          </div>
          <input value={contextQuery} onChange={(event) => setContextQuery(event.target.value)} style={{ ...inputStyle, marginTop: '0.9rem' }} />
          <p style={{ color: 'var(--color-neutral-600)' }}>Token delta - mức tăng token: {memoryProbe?.token_budget_increase_percent ?? 0}%</p>
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {(memoryProbe?.summaries ?? []).map((summary) => (
              <article key={summary.summary_id} style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '0.9rem' }}>
                <strong>{summary.topic}</strong>
                <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>{summary.filter_context}</div>
                <p style={{ marginBottom: 0 }}>{summary.summary_text}</p>
              </article>
            ))}
          </div>
        </section>
        <aside style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ ...cardStyle, padding: '1.25rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Suggestions - Gợi ý</h2>
            {suggestions.map((suggestion) => (
              <div key={`${suggestion.type}-${suggestion.label}`} style={{ marginTop: '0.75rem', borderRadius: '0.9rem', background: 'rgba(15,118,110,0.08)', padding: '0.8rem' }}>
                <strong>{suggestion.label}</strong>
                <div style={{ color: 'var(--color-neutral-500)' }}>{suggestion.type === 'kpi' ? `${suggestion.uses ?? 0} lần dùng` : 'Saved template - Mẫu đã lưu'}</div>
              </div>
            ))}
          </div>
          <div style={{ ...cardStyle, padding: '1.25rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Memory self-audit - Tự kiểm tra bộ nhớ</h2>
            <p style={{ color: memoryAudit.length ? '#991b1b' : '#166534' }}>
              {memoryAudit.length === 0 ? 'Không có vi phạm raw-value cho người dùng hiện tại.' : `${memoryAudit.length} vi phạm`}
            </p>
          </div>
        </aside>
      </div>

      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: '1.2fr 0.8fr', marginTop: '1rem' }}>
        <form onSubmit={(event) => void handleSaveTemplate(event)} style={{ ...cardStyle, padding: '1.25rem', display: 'grid', gap: '0.8rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Lưu mẫu - Save template</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
            <input value={templateForm.name} onChange={(event) => setTemplateForm((current) => ({ ...current, name: event.target.value }))} style={inputStyle} placeholder="Tên mẫu (Template name)" />
            <input value={templateForm.output_format} onChange={(event) => setTemplateForm((current) => ({ ...current, output_format: event.target.value }))} style={inputStyle} placeholder="Định dạng đầu ra (Output format)" />
            <input value={templateForm.query_intent} onChange={(event) => setTemplateForm((current) => ({ ...current, query_intent: event.target.value }))} style={inputStyle} placeholder="Ý định truy vấn (Query intent)" />
            <input value={templateForm.time_range} onChange={(event) => setTemplateForm((current) => ({ ...current, time_range: event.target.value }))} style={inputStyle} placeholder="Khoảng thời gian (Time range)" />
          </div>
          <textarea value={templateForm.filters} onChange={(event) => setTemplateForm((current) => ({ ...current, filters: event.target.value }))} style={{ ...inputStyle, minHeight: '4.5rem' }} placeholder="Bộ lọc (Filters)" />
          <button type="submit" style={buttonStyle}>Lưu mẫu</button>
        </form>
        <aside style={{ ...cardStyle, padding: '1.25rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Saved templates - Mẫu đã lưu</h2>
          {templates.map((template) => (
            <article key={template.template_id} style={{ marginTop: '0.8rem', borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '0.9rem' }}>
              <strong>{template.name}</strong>
              <div style={{ color: 'var(--color-neutral-500)' }}>{template.query_intent} - {template.time_range}</div>
              <p style={{ marginBottom: 0 }}>{template.filters}</p>
            </article>
          ))}
        </aside>
      </div>

      <section style={{ ...cardStyle, padding: '1.25rem', marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Conversation History - Lịch sử hội thoại</h2>
          <button type="button" style={ghostButtonStyle} onClick={() => void loadHistory()}>Tìm kiếm</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '0.8rem', marginTop: '1rem' }}>
          <input value={historyKeyword} onChange={(event) => setHistoryKeyword(event.target.value)} style={inputStyle} placeholder="Từ khóa (Keyword)" />
          <input value={historyTopic} onChange={(event) => setHistoryTopic(event.target.value)} style={inputStyle} placeholder="Chủ đề (Topic)" />
          <button type="button" style={buttonStyle} onClick={() => void loadHistory()}>Chạy tìm kiếm</button>
        </div>
        {historyEntries.map((entry) => (
          <article key={entry.entry_id} style={{ marginTop: '0.85rem', borderRadius: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)', padding: '0.95rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <strong>{entry.topic}</strong>
                <div style={{ color: 'var(--color-neutral-500)' }}>{entry.intent_type} - {formatDate(entry.created_at)}</div>
              </div>
              <button type="button" style={ghostButtonStyle} onClick={() => void handleReuse(entry.entry_id)}>Dùng lại</button>
            </div>
            <p>{entry.filter_context}</p>
            <p>{entry.key_result_summary}</p>
          </article>
        ))}
        <div style={{ marginTop: '1rem', borderRadius: '1rem', background: 'rgba(26,31,44,0.95)', color: '#d7f9f1', padding: '1rem' }}>
          <strong>Preloaded draft - Bản nháp đã nạp</strong>
          <div style={{ marginTop: '0.4rem' }}>{draftPrompt || 'Chưa có intent nào được nạp lại.'}</div>
        </div>
      </section>
    </section>
  );
}
