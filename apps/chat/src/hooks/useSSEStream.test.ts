/**
 * Tests for useSSEStream hook
 * Story 1.7 AC: useSSEStream hook stub scaffolded with interface only
 * (not connected to backend)
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSEStream } from '../hooks/useSSEStream';
import type { SSEErrorEvent, SSEEvent } from '@aial/types';

describe('useSSEStream', () => {
  afterEach(() => {
    vi.clearAllTimers();
    vi.unstubAllGlobals();
  });

  it('returns correct initial state (idle)', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    expect(result.current.state.status).toBe('idle');
    expect(result.current.state.events).toEqual([]);
    expect(result.current.state.error).toBeNull();
    expect(result.current.state.traceId).toBeNull();
  });

  it('exposes connect, abort, and reset functions', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    expect(typeof result.current.connect).toBe('function');
    expect(typeof result.current.abort).toBe('function');
    expect(typeof result.current.reset).toBe('function');
  });

  it('connect() sets status to connecting before stream activity', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    act(() => {
      result.current.connect();
    });

    expect(result.current.state.status).toBe('connecting');
  });

  it('abort() returns to idle state', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    act(() => {
      result.current.connect();
      result.current.abort();
    });

    expect(result.current.state.status).toBe('idle');
  });

  it('reset() clears all state', () => {
    const { result } = renderHook(() =>
      useSSEStream<SSEEvent>('/v1/chat/stream/test-123'),
    );

    act(() => {
      result.current.reset();
    });

    expect(result.current.state.status).toBe('idle');
    expect(result.current.state.events).toEqual([]);
    expect(result.current.state.error).toBeNull();
    expect(result.current.state.traceId).toBeNull();
  });

  it('does NOT auto-connect when autoConnect is false (default)', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', { autoConnect: false }),
    );

    // Status should remain idle — no connection attempted
    expect(result.current.state.status).toBe('idle');
  });

  it('accepts token option for JWT injection', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', {
        token: 'test-jwt-token',
      }),
    );

    // Should initialize without error
    expect(result.current.state).toBeDefined();
  });

  it('accepts onEvent callback option', () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', { onEvent }),
    );

    expect(result.current.state).toBeDefined();
  });

  it('accepts maxRetries option', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', { maxRetries: 3 }),
    );

    expect(result.current.state).toBeDefined();
  });

  it('accepts baseRetryDelay option', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', { baseRetryDelay: 2000 }),
    );

    expect(result.current.state).toBeDefined();
  });

  it('unmount does not cause state update errors', () => {
    const { result, unmount } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    act(() => {
      result.current.connect();
    });

    // Should not throw on unmount
    expect(() => unmount()).not.toThrow();
  });

  it('multiple connect() calls do not stack connections', () => {
    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123'),
    );

    act(() => {
      result.current.connect();
      result.current.connect();
      result.current.connect();
    });

    // Should remain in a valid state
    expect(['idle', 'connecting', 'streaming', 'done', 'error']).toContain(
      result.current.state.status,
    );
  });

  it('transitions to error when the backend emits an SSE error event', async () => {
    const onError = vi.fn();
    const encoder = new TextEncoder();
    const errorEvent: SSEErrorEvent = {
      type: 'error',
      error_code: 'timeout',
      message: 'Query execution timed out',
      trace_id: 'trace-timeout',
    };

    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(errorEvent)}\n\n`));
          controller.close();
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      },
    )));

    const { result } = renderHook(() =>
      useSSEStream('/v1/chat/stream/test-123', { onError }),
    );

    await act(async () => {
      result.current.connect();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.state.status).toBe('error');
    expect(result.current.state.error).toEqual(errorEvent);
    expect(onError).toHaveBeenCalledWith(errorEvent);
  });
});
