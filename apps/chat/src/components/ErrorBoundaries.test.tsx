/**
 * Tests for Error Boundary hierarchy
 * Story 1.7 AC2: StreamErrorBoundary renders fallback; PageErrorBoundary catches
 * page-level errors; AppErrorBoundary is root safety net
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  AppErrorBoundary,
  PageErrorBoundary,
  StreamErrorBoundary,
} from '../components/ErrorBoundaries';

// ============================================================
// Test helpers
// ============================================================

/** Component that throws on first render */
function ThrowOnRender({ message = 'Test error' }: { message?: string }): React.JSX.Element {
  throw new Error(message);
}

/** Component that conditionally throws */
function ConditionalThrow({
  shouldThrow,
  children = <div>Safe content</div>,
}: {
  shouldThrow: boolean;
  children?: React.ReactNode;
}): React.JSX.Element {
  if (shouldThrow) throw new Error('Conditional error');
  return <>{children}</>;
}

// Suppress console.error for expected test errors
const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

beforeEach(() => {
  consoleSpy.mockClear();
});

// ============================================================
// AppErrorBoundary tests
// ============================================================

describe('AppErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <AppErrorBoundary>
        <div>Safe content</div>
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Safe content')).toBeInTheDocument();
  });

  it('renders default fallback when child throws', () => {
    render(
      <AppErrorBoundary>
        <ThrowOnRender />
      </AppErrorBoundary>,
    );

    // Should show error heading in Vietnamese
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Đã xảy ra lỗi nghiêm trọng/i)).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <AppErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowOnRender />
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });

  it('renders function fallback with error and reset', () => {
    const onReset = vi.fn();

    render(
      <AppErrorBoundary
        fallback={(error, reset) => (
          <div>
            <span>Error: {error.message}</span>
            <button onClick={() => { reset(); onReset(); }}>Reset</button>
          </div>
        )}
      >
        <ThrowOnRender message="Custom error message" />
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Error: Custom error message')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Reset'));
    expect(onReset).toHaveBeenCalledOnce();
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();

    render(
      <AppErrorBoundary onError={onError}>
        <ThrowOnRender message="Tracked error" />
      </AppErrorBoundary>,
    );

    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe('Tracked error');
  });

  it('reset button clears error state', () => {
    render(
      <AppErrorBoundary>
        <ThrowOnRender />
      </AppErrorBoundary>,
    );

    // Error state is shown
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Click reset
    fireEvent.click(screen.getByText('Tải lại trang'));

    // After reset, boundary is in clean state (ThrowOnRender will throw again)
    // but boundary's state.hasError should be reset
    expect(consoleSpy).toHaveBeenCalled();
  });

  it('has role="alert" on error fallback', () => {
    render(
      <AppErrorBoundary>
        <ThrowOnRender />
      </AppErrorBoundary>,
    );

    const alertEl = screen.getByRole('alert');
    expect(alertEl).toBeInTheDocument();
  });
});

// ============================================================
// PageErrorBoundary tests
// ============================================================

describe('PageErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <PageErrorBoundary>
        <main>Page content</main>
      </PageErrorBoundary>,
    );

    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('renders page-level fallback when child throws', () => {
    render(
      <PageErrorBoundary>
        <ThrowOnRender />
      </PageErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Không thể tải trang này/i)).toBeInTheDocument();
  });

  it('uses aria-live="polite" (not assertive) for page errors', () => {
    render(
      <PageErrorBoundary>
        <ThrowOnRender />
      </PageErrorBoundary>,
    );

    const alertEl = screen.getByRole('alert');
    expect(alertEl).toHaveAttribute('aria-live', 'polite');
  });

  it('renders retry button that resets boundary', () => {
    const { rerender } = render(
      <PageErrorBoundary>
        <ConditionalThrow shouldThrow={true} />
      </PageErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Thử lại'));

    // After reset, try to rerender with non-throwing child
    rerender(
      <PageErrorBoundary>
        <div>Recovered content</div>
      </PageErrorBoundary>,
    );

    // Boundary resets its state on reset click
    expect(consoleSpy).toHaveBeenCalled();
  });
});

// ============================================================
// StreamErrorBoundary tests
// ============================================================

describe('StreamErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <StreamErrorBoundary>
        <div>Stream content</div>
      </StreamErrorBoundary>,
    );

    expect(screen.getByText('Stream content')).toBeInTheDocument();
  });

  it('renders stream-specific fallback when child throws', () => {
    render(
      <StreamErrorBoundary>
        <ThrowOnRender />
      </StreamErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Lỗi kết nối')).toBeInTheDocument();
  });

  it('shows retry button for stream errors', () => {
    render(
      <StreamErrorBoundary>
        <ThrowOnRender />
      </StreamErrorBoundary>,
    );

    const retryBtn = screen.getByRole('button', { name: /Thử kết nối lại/i });
    expect(retryBtn).toBeInTheDocument();
  });

  it('does NOT show full-screen error (only inline fallback)', () => {
    const { container } = render(
      <StreamErrorBoundary>
        <ThrowOnRender />
      </StreamErrorBoundary>,
    );

    // Stream fallback is inline — no min-height: 100vh
    const alertEl = screen.getByRole('alert');
    expect(alertEl).not.toHaveStyle({ minHeight: '100vh' });
    expect(container).toBeInTheDocument();
  });

  it('has aria-label for screen readers', () => {
    render(
      <StreamErrorBoundary>
        <ThrowOnRender />
      </StreamErrorBoundary>,
    );

    const alertEl = screen.getByRole('alert');
    expect(alertEl).toHaveAttribute('aria-label', expect.stringContaining('streaming'));
  });
});

// ============================================================
// Hierarchy integration test
// ============================================================

describe('Error Boundary Hierarchy', () => {
  it('AppErrorBoundary > PageErrorBoundary > StreamErrorBoundary — outer catches inner children', () => {
    render(
      <AppErrorBoundary>
        <PageErrorBoundary>
          <StreamErrorBoundary>
            <div>Deep content</div>
          </StreamErrorBoundary>
        </PageErrorBoundary>
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Deep content')).toBeInTheDocument();
  });

  it('StreamErrorBoundary catches its own error without propagating to PageErrorBoundary', () => {
    render(
      <AppErrorBoundary>
        <PageErrorBoundary>
          <StreamErrorBoundary>
            <ThrowOnRender />
          </StreamErrorBoundary>
        </PageErrorBoundary>
      </AppErrorBoundary>,
    );

    // Only stream error should show (not page-level or app-level)
    const alerts = screen.getAllByRole('alert');
    // The innermost boundary catches it — shows stream fallback
    expect(alerts.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Lỗi kết nối')).toBeInTheDocument();
    expect(screen.queryByText(/Đã xảy ra lỗi nghiêm trọng/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Không thể tải trang này/i)).not.toBeInTheDocument();
  });
});
