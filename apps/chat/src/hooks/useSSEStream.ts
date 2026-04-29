/**
 * useSSEStream — SINGLE SOURCE OF TRUTH for SSE connections
 *
 * Architecture: UX-DR21 — JWT injection; reconnect with exponential backoff;
 * cleanup on unmount. All streaming components MUST use this hook.
 *
 * Story 1.7: Stub only — interface defined, NOT connected to backend.
 * Full SSE implementation happens in Epic 2A (Story 2A.5).
 *
 * @see architecture.md §FMT-2 SSE Event Format
 * @see architecture.md — Shared SSE Hook — `useSSEStream` (bắt buộc)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { SSEEvent, SSEErrorEvent, StreamState, StreamStatus } from '@aial/types';

// ============================================================
// Types
// ============================================================

export interface SSEOptions {
  /** Bearer JWT token — injected into EventSource headers via fetch polyfill */
  token?: string;
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Max reconnect attempts (default: 5) */
  maxRetries?: number;
  /** Base delay for exponential backoff in ms (default: 1000) */
  baseRetryDelay?: number;
  /** Callback when a new event arrives */
  onEvent?: (event: SSEEvent) => void;
  /** Callback when stream closes */
  onClose?: () => void;
  /** Callback on error */
  onError?: (error: SSEErrorEvent) => void;
}

export interface UseSSEStreamReturn<T extends SSEEvent = SSEEvent> {
  /** Current stream state */
  state: StreamState<T>;
  /** Start or restart the SSE connection */
  connect: () => void;
  /** Abort the current SSE stream */
  abort: () => void;
  /** Reset state to idle */
  reset: () => void;
}

// ============================================================
// Internal helpers
// ============================================================

const INITIAL_STATE: StreamState = {
  status: 'idle',
  events: [],
  error: null,
  traceId: null,
};

function computeBackoffDelay(attempt: number, baseDelay: number): number {
  // Exponential backoff: baseDelay * 2^attempt, capped at 30s
  const delay = baseDelay * Math.pow(2, attempt);
  return Math.min(delay, 30_000);
}

// ============================================================
// Hook
// ============================================================

/**
 * SSE Stream hook — stub implementation (Story 1.7)
 *
 * In Story 1.7 this hook defines the full interface contract.
 * The actual EventSource connection is scaffolded but NOT wired to backend.
 * Epic 2A will provide a real backend endpoint to connect to.
 *
 * @param url - SSE endpoint URL (e.g. `/v1/chat/stream/{id}`)
 * @param options - SSE configuration options
 */
export function useSSEStream<T extends SSEEvent = SSEEvent>(
  url: string,
  options: SSEOptions = {},
): UseSSEStreamReturn<T> {
  const {
    token,
    autoConnect = false,
    maxRetries = 5,
    baseRetryDelay = 1_000,
    onEvent,
    onClose,
    onError,
  } = options;

  const [state, setState] = useState<StreamState<T>>({ ...INITIAL_STATE } as StreamState<T>);

  // Track abort controller and retry count in refs (not state — no re-render needed)
  const abortControllerRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  // Stable URL + token refs to avoid stale closures
  const urlRef = useRef(url);
  const tokenRef = useRef(token);
  urlRef.current = url;
  tokenRef.current = token;

  const setStatus = useCallback((status: StreamStatus) => {
    if (isMountedRef.current) {
      setState(prev => ({ ...prev, status }));
    }
  }, []);

  // ============================================================
  // STUB: connect — scaffolded interface, not wired to backend
  // Full implementation: Epic 2A / Story 2A.5
  // ============================================================
  const connect = useCallback(() => {
    // Cancel any in-flight connection
    abortControllerRef.current?.abort();

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setState({
      status: 'connecting',
      events: [],
      error: null,
      traceId: null,
    } as StreamState<T>);

    // STUB: In Story 1.7, we do NOT open a real SSE connection.
    // The interface (connect/abort/reset + state shape) is defined here.
    // Epic 2A will implement the actual fetch + ReadableStream parsing below:
    //
    // fetch(urlRef.current, {
    //   headers: {
    //     Authorization: `Bearer ${tokenRef.current}`,
    //     Accept: 'text/event-stream',
    //   },
    //   signal: controller.signal,
    // })
    //   .then(response => {
    //     if (!response.ok) throw new Error(`SSE error: ${response.status}`);
    //     // parse SSE events from response.body ReadableStream...
    //   })
    //   .catch(err => { /* handle error + exponential backoff reconnect */ });

    console.debug('[useSSEStream] STUB — connect called for URL:', urlRef.current);
    console.debug('[useSSEStream] Full SSE implementation deferred to Epic 2A / Story 2A.5');

    // Immediately move to 'idle' in stub mode (no actual connection)
    if (isMountedRef.current) {
      setState({
        status: 'idle',
        events: [],
        error: null,
        traceId: null,
      } as StreamState<T>);
    }
  }, []);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    retryCountRef.current = 0;
    setStatus('idle');
    onClose?.();
  }, [onClose, setStatus]);

  const reset = useCallback(() => {
    abort();
    setState({ ...INITIAL_STATE } as StreamState<T>);
  }, [abort]);

  // Auto-connect on mount if configured
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally only on mount

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // Suppress unused var warnings for stub
  void maxRetries;
  void baseRetryDelay;
  void onEvent;
  void onError;
  void computeBackoffDelay;

  return { state, connect, abort, reset };
}
