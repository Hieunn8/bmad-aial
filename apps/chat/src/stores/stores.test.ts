/**
 * Tests for Zustand stores
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useStreamStore } from '../stores/streamStore';
import { useUIStore } from '../stores/uiStore';

// ============================================================
// Stream Store
// ============================================================

describe('streamStore', () => {
  beforeEach(() => {
    // Reset store between tests
    useStreamStore.setState({ streams: {} });
  });

  it('starts with empty streams', () => {
    const { streams } = useStreamStore.getState();
    expect(streams).toEqual({});
  });

  it('startStream creates a stream in connecting state', () => {
    const { startStream } = useStreamStore.getState();
    startStream('session-1');

    const { streams } = useStreamStore.getState();
    expect(streams['session-1']).toBeDefined();
    expect(streams['session-1'].status).toBe('connecting');
    expect(streams['session-1'].events).toEqual([]);
    expect(streams['session-1'].error).toBeNull();
  });

  it('setStreamStatus updates stream status', () => {
    const { startStream, setStreamStatus } = useStreamStore.getState();
    startStream('session-1');
    setStreamStatus('session-1', 'streaming');

    const { streams } = useStreamStore.getState();
    expect(streams['session-1'].status).toBe('streaming');
  });

  it('appendEvent adds events to stream', () => {
    const { startStream, appendEvent } = useStreamStore.getState();
    startStream('session-1');

    const event = {
      type: 'chunk' as const,
      content: 'Hello',
      index: 0,
      trace_id: 'trace-1',
    };
    appendEvent('session-1', event);

    const { streams } = useStreamStore.getState();
    expect(streams['session-1'].events).toHaveLength(1);
    expect(streams['session-1'].events[0]).toEqual(event);
  });

  it('completeStream marks stream as done with traceId', () => {
    const { startStream, completeStream } = useStreamStore.getState();
    startStream('session-1');
    completeStream('session-1', 'trace-abc-123');

    const { streams } = useStreamStore.getState();
    expect(streams['session-1'].status).toBe('done');
    expect(streams['session-1'].traceId).toBe('trace-abc-123');
  });

  it('errorStream marks stream as errored', () => {
    const { startStream, errorStream } = useStreamStore.getState();
    startStream('session-1');

    const errorEvent = {
      type: 'error' as const,
      error_code: 'timeout' as const,
      message: 'Request timed out',
      trace_id: 'trace-1',
    };
    errorStream('session-1', errorEvent);

    const { streams } = useStreamStore.getState();
    expect(streams['session-1'].status).toBe('error');
    expect(streams['session-1'].error).toEqual(errorEvent);
  });

  it('clearStream removes stream from state', () => {
    const { startStream, clearStream } = useStreamStore.getState();
    startStream('session-1');
    clearStream('session-1');

    const { streams } = useStreamStore.getState();
    expect(streams['session-1']).toBeUndefined();
  });

  it('appendEvent is immutable — does not mutate previous events array', () => {
    const { startStream, appendEvent } = useStreamStore.getState();
    startStream('session-1');

    const event1 = { type: 'chunk' as const, content: 'A', index: 0, trace_id: 't1' };
    const event2 = { type: 'chunk' as const, content: 'B', index: 1, trace_id: 't1' };

    appendEvent('session-1', event1);
    const prevEvents = useStreamStore.getState().streams['session-1'].events;

    appendEvent('session-1', event2);
    const nextEvents = useStreamStore.getState().streams['session-1'].events;

    // Immutability check — different array reference
    expect(prevEvents).not.toBe(nextEvents);
    expect(prevEvents).toHaveLength(1);
    expect(nextEvents).toHaveLength(2);
  });
});

// ============================================================
// UI Store
// ============================================================

describe('uiStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      isSidebarOpen: true,
      activeModal: null,
      isOnline: true,
    });
  });

  it('sidebar is open by default', () => {
    const { isSidebarOpen } = useUIStore.getState();
    expect(isSidebarOpen).toBe(true);
  });

  it('toggleSidebar flips sidebar state', () => {
    const { toggleSidebar } = useUIStore.getState();
    toggleSidebar();

    expect(useUIStore.getState().isSidebarOpen).toBe(false);
    toggleSidebar();
    expect(useUIStore.getState().isSidebarOpen).toBe(true);
  });

  it('setSidebarOpen sets explicit value', () => {
    const { setSidebarOpen } = useUIStore.getState();
    setSidebarOpen(false);
    expect(useUIStore.getState().isSidebarOpen).toBe(false);
    setSidebarOpen(true);
    expect(useUIStore.getState().isSidebarOpen).toBe(true);
  });

  it('openModal sets active modal', () => {
    const { openModal } = useUIStore.getState();
    openModal('confirm-delete');
    expect(useUIStore.getState().activeModal).toBe('confirm-delete');
  });

  it('closeModal clears active modal', () => {
    const { openModal, closeModal } = useUIStore.getState();
    openModal('some-modal');
    closeModal();
    expect(useUIStore.getState().activeModal).toBeNull();
  });

  it('setOnline updates connection state', () => {
    const { setOnline } = useUIStore.getState();
    setOnline(false);
    expect(useUIStore.getState().isOnline).toBe(false);
    setOnline(true);
    expect(useUIStore.getState().isOnline).toBe(true);
  });
});
