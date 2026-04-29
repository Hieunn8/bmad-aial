/**
 * streamStore — Active stream state (Zustand slice)
 * Architecture: §ST-2 stores/streamStore.ts
 */
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { SSEEvent, StreamState, StreamStatus } from '@aial/types';

interface StreamStore {
  /** Active stream states keyed by session/query ID */
  streams: Record<string, StreamState>;

  /** Start tracking a stream */
  startStream: (id: string) => void;

  /** Update stream status */
  setStreamStatus: (id: string, status: StreamStatus) => void;

  /** Append a new SSE event to a stream */
  appendEvent: (id: string, event: SSEEvent) => void;

  /** Mark stream as complete */
  completeStream: (id: string, traceId: string) => void;

  /** Mark stream as errored */
  errorStream: (id: string, error: SSEEvent & { type: 'error' }) => void;

  /** Clear a stream from state */
  clearStream: (id: string) => void;
}

export const useStreamStore = create<StreamStore>()(
  devtools(
    (set) => ({
      streams: {},

      startStream: (id) =>
        set(
          (state) => ({
            streams: {
              ...state.streams,
              [id]: {
                status: 'connecting',
                events: [],
                error: null,
                traceId: null,
              },
            },
          }),
          false,
          'stream/start',
        ),

      setStreamStatus: (id, status) =>
        set(
          (state) => ({
            streams: {
              ...state.streams,
              [id]: state.streams[id]
                ? { ...state.streams[id], status }
                : {
                    status,
                    events: [],
                    error: null,
                    traceId: null,
                  },
            },
          }),
          false,
          'stream/setStatus',
        ),

      appendEvent: (id, event) =>
        set(
          (state) => {
            const existing = state.streams[id];
            if (!existing) return state;
            return {
              streams: {
                ...state.streams,
                [id]: {
                  ...existing,
                  status: 'streaming' as StreamStatus,
                  events: [...existing.events, event],
                },
              },
            };
          },
          false,
          'stream/appendEvent',
        ),

      completeStream: (id, traceId) =>
        set(
          (state) => {
            const existing = state.streams[id];
            if (!existing) return state;
            return {
              streams: {
                ...state.streams,
                [id]: {
                  ...existing,
                  status: 'done' as StreamStatus,
                  traceId,
                },
              },
            };
          },
          false,
          'stream/complete',
        ),

      errorStream: (id, error) =>
        set(
          (state) => {
            const existing = state.streams[id];
            if (!existing) return state;
            return {
              streams: {
                ...state.streams,
                [id]: {
                  ...existing,
                  status: 'error' as StreamStatus,
                  error,
                },
              },
            };
          },
          false,
          'stream/error',
        ),

      clearStream: (id) =>
        set(
          (state) => {
            const { [id]: _, ...rest } = state.streams;
            return { streams: rest };
          },
          false,
          'stream/clear',
        ),
    }),
    { name: 'StreamStore' },
  ),
);
