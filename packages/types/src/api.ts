/**
 * Shared API types — used by both chat and admin apps
 * §FMT-1 API Response Format
 */

// ============================================================
// API Response Envelope
// ============================================================

/** Single resource response */
export interface ApiResponse<T> {
  data: T;
  meta: ApiMeta;
}

/** List / paginated response */
export interface ApiListResponse<T> {
  data: T[];
  meta: ApiListMeta;
}

/** Error response — RFC 9457 (Phase 1 simple envelope) */
export interface ApiErrorResponse {
  success: false;
  error: string;
  trace_id: string;
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
}

export interface ApiMeta {
  generatedAt: string;
}

export interface ApiListMeta extends ApiMeta {
  total: number;
  page: number;
  limit: number;
}

// ============================================================
// SSE Event Types — §FMT-2
// ============================================================

export type SSEEventType = 'chunk' | 'tool_call' | 'done' | 'error' | 'thinking' | 'step' | 'row';

export interface SSEChunkEvent {
  type: 'chunk';
  content: string;
  index: number;
  trace_id: string;
}

export interface SSEToolCallEvent {
  type: 'tool_call';
  tool: string;
  status: 'running' | 'complete' | 'failed';
  trace_id: string;
}

export interface SSEDoneEvent {
  type: 'done';
  trace_id: string;
  answer?: string;
  query_id?: string;
  sources?: SSESource[];
  generated_at?: string;
}

export interface SSEThinkingEvent {
  type: 'thinking';
  phase: 1 | 2;
  message: string;
}

export interface SSEStepEvent {
  type: 'step';
  step: number;
  total: number;
  description: string;
}

export interface SSERowEvent {
  type: 'row';
  rows: Record<string, unknown>[];
  chunk_index: number;
}

export interface SSEErrorEvent {
  type: 'error';
  /** Semantic error category for UI routing */
  error_code: 'timeout' | 'permission-denied' | 'llm-unavailable' | 'stream-error';
  message: string;
  trace_id?: string;
}

export interface SSESource {
  doc_id: string;
  title: string;
  page: number;
}

export type SSEEvent =
  | SSEChunkEvent
  | SSEToolCallEvent
  | SSEDoneEvent
  | SSEThinkingEvent
  | SSEStepEvent
  | SSERowEvent
  | SSEErrorEvent;

// ============================================================
// Stream State — for useSSEStream hook
// ============================================================

export type StreamStatus = 'idle' | 'connecting' | 'thinking' | 'streaming' | 'done' | 'error' | 'reconnecting';

export interface StreamState<T = SSEEvent> {
  status: StreamStatus;
  events: T[];
  error: SSEErrorEvent | null;
  traceId: string | null;
}

// ============================================================
// User / Auth types
// ============================================================

export interface JwtPrincipal {
  sub: string;
  email: string;
  name: string;
  roles: string[];
  department: string;  // UX-DR per arch: must always be present
  clearance: string;   // UX-DR per arch: must always be present
}

// ============================================================
// TanStack Query key factory
// ============================================================

export const queryKeys = {
  sessions: {
    all: () => ['sessions'] as const,
    list: () => ['sessions', 'list'] as const,
    detail: (id: string) => ['sessions', id] as const,
  },
  chat: {
    all: () => ['chat'] as const,
    query: (sessionId: string) => ['chat', sessionId] as const,
  },
} as const;
