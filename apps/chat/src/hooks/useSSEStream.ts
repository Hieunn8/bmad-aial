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

  const connect = useCallback(() => {
    abortControllerRef.current?.abort();
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    if (isMountedRef.current) {
      setState({ status: 'connecting', events: [], error: null, traceId: null } as StreamState<T>);
    }

    const headers: Record<string, string> = { Accept: 'text/event-stream' };
    if (tokenRef.current) {
      headers['Authorization'] = `Bearer ${tokenRef.current}`;
    }

    fetch(urlRef.current, { headers, signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(`SSE error: ${response.status}`);
        if (!response.body) throw new Error('No response body');
        if (isMountedRef.current) setStatus('streaming');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            try {
              const event = JSON.parse(trimmed.slice(5).trim()) as T;
              if (isMountedRef.current) {
                setState(prev => ({
                  ...prev,
                  events: [...prev.events, event],
                  traceId: (event as unknown as { trace_id?: string }).trace_id ?? prev.traceId,
                }));
              }
              onEvent?.(event);
              if ((event as unknown as { type: string }).type === 'done') {
                if (isMountedRef.current) setStatus('done');
                retryCountRef.current = 0;
                onClose?.();
                return;
              }
            } catch {
              // malformed SSE line — skip
            }
          }
        }
        if (isMountedRef.current) setStatus('done');
        retryCountRef.current = 0;
        onClose?.();
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return;
        const errorEvent: SSEErrorEvent = { type: 'error', error_code: 'stream-error', message: (err as Error).message };
        onError?.(errorEvent);
        if (retryCountRef.current < maxRetries && isMountedRef.current) {
          const delay = computeBackoffDelay(retryCountRef.current, baseRetryDelay);
          retryCountRef.current += 1;
          retryTimeoutRef.current = setTimeout(() => { if (isMountedRef.current) connect(); }, delay);
          if (isMountedRef.current) setStatus('reconnecting');
        } else if (isMountedRef.current) {
          setState(prev => ({ ...prev, status: 'error', error: errorEvent }));
        }
      });
  }, [maxRetries, baseRetryDelay, onEvent, onClose, onError, setStatus]);

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

  // Cleanup on unmount — isMountedRef is true at declaration, set false on cleanup
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  return { state, connect, abort, reset };
}
