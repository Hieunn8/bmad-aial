/**
 * Error Boundary Hierarchy
 * Architecture: AppErrorBoundary > PageErrorBoundary > StreamErrorBoundary
 * UX-DR18: Mandatory before streaming components
 *
 * @see architecture.md §PR-2 Error Handling Frontend
 */
import React, { Component, type ReactNode, type ErrorInfo } from 'react';

// ============================================================
// Types
// ============================================================

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

// ============================================================
// Base Error Boundary
// ============================================================

class BaseErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  protected reset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError || !this.state.error) {
      return this.props.children;
    }

    const { fallback } = this.props;
    if (typeof fallback === 'function') {
      return fallback(this.state.error, this.reset);
    }
    return fallback ?? null;
  }
}

// ============================================================
// AppErrorBoundary — Root safety net
// Shows full-page error when app-level failure occurs
// ============================================================

const AppErrorFallback = ({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}): React.JSX.Element => (
  <div
    role="alert"
    aria-live="assertive"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem',
      fontFamily: 'var(--font-family-base, sans-serif)',
      backgroundColor: 'var(--color-background, #fafaf9)',
      color: 'var(--color-neutral-900, #1a1a18)',
    }}
  >
    <h1
      style={{
        fontSize: '1.5rem',
        fontWeight: 600,
        marginBottom: '0.75rem',
        color: 'var(--color-error-500, #c53030)',
      }}
    >
      Đã xảy ra lỗi nghiêm trọng
    </h1>
    <p
      style={{
        fontSize: '0.875rem',
        color: 'var(--color-neutral-600, #4a4a44)',
        marginBottom: '1.5rem',
        maxWidth: '40rem',
        textAlign: 'center',
      }}
    >
      Ứng dụng gặp sự cố không mong muốn. Vui lòng thử tải lại trang.
    </p>
    <p
      style={{
        fontSize: '0.75rem',
        color: 'var(--color-neutral-400, #6b6b65)',
        marginBottom: '1.5rem',
        fontFamily: 'monospace',
        padding: '0.5rem 1rem',
        backgroundColor: 'var(--color-surface-muted, #f5f5f0)',
        borderRadius: '0.375rem',
      }}
    >
      {error.message}
    </p>
    <button
      onClick={reset}
      style={{
        padding: '0.5rem 1.5rem',
        backgroundColor: 'var(--color-primary, #0F7B6C)',
        color: 'white',
        border: 'none',
        borderRadius: '0.375rem',
        cursor: 'pointer',
        fontSize: '0.875rem',
        fontWeight: 500,
      }}
    >
      Tải lại trang
    </button>
  </div>
);

export class AppErrorBoundary extends BaseErrorBoundary {
  override render(): ReactNode {
    if (!this.state.hasError || !this.state.error) {
      return this.props.children;
    }

    const { fallback } = this.props;
    if (typeof fallback === 'function') {
      return fallback(this.state.error, this.reset);
    }
    if (fallback) return fallback;

    return <AppErrorFallback error={this.state.error} reset={this.reset} />;
  }
}

// ============================================================
// PageErrorBoundary — Page-level errors within layout
// Shows error within the page layout (not full-screen)
// ============================================================

const PageErrorFallback = ({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}): React.JSX.Element => (
  <div
    role="alert"
    aria-live="polite"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '3rem 2rem',
      fontFamily: 'var(--font-family-base, sans-serif)',
    }}
  >
    <h2
      style={{
        fontSize: '1.125rem',
        fontWeight: 600,
        marginBottom: '0.5rem',
        color: 'var(--color-error-500, #c53030)',
      }}
    >
      Không thể tải trang này
    </h2>
    <p
      style={{
        fontSize: '0.875rem',
        color: 'var(--color-neutral-600, #4a4a44)',
        marginBottom: '1rem',
        textAlign: 'center',
      }}
    >
      {error.message}
    </p>
    <button
      onClick={reset}
      style={{
        padding: '0.375rem 1rem',
        backgroundColor: 'var(--color-primary, #0F7B6C)',
        color: 'white',
        border: 'none',
        borderRadius: '0.375rem',
        cursor: 'pointer',
        fontSize: '0.875rem',
      }}
    >
      Thử lại
    </button>
  </div>
);

export class PageErrorBoundary extends BaseErrorBoundary {
  override render(): ReactNode {
    if (!this.state.hasError || !this.state.error) {
      return this.props.children;
    }

    const { fallback } = this.props;
    if (typeof fallback === 'function') {
      return fallback(this.state.error, this.reset);
    }
    if (fallback) return fallback;

    return <PageErrorFallback error={this.state.error} reset={this.reset} />;
  }
}

// ============================================================
// StreamErrorBoundary — Streaming-specific fallback
// Shows retry/fallback for stream-related errors
// ============================================================

const StreamErrorFallback = ({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}): React.JSX.Element => (
  <div
    role="alert"
    aria-live="polite"
    aria-label="Lỗi kết nối streaming"
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 1rem',
      backgroundColor: 'var(--color-error-50, #fff5f5)',
      border: '1px solid var(--color-error-500, #c53030)',
      borderRadius: '0.5rem',
      fontFamily: 'var(--font-family-base, sans-serif)',
    }}
  >
    <span
      aria-hidden="true"
      style={{ fontSize: '1.125rem' }}
    >
      ⚠️
    </span>
    <div style={{ flex: 1 }}>
      <p
        style={{
          fontSize: '0.875rem',
          fontWeight: 500,
          margin: 0,
          color: 'var(--color-error-700, #9b2c2c)',
        }}
      >
        Lỗi kết nối
      </p>
      <p
        style={{
          fontSize: '0.75rem',
          margin: '0.25rem 0 0',
          color: 'var(--color-error-500, #c53030)',
        }}
      >
        {error.message}
      </p>
    </div>
    <button
      onClick={reset}
      aria-label="Thử kết nối lại"
      style={{
        padding: '0.25rem 0.75rem',
        backgroundColor: 'transparent',
        color: 'var(--color-error-700, #9b2c2c)',
        border: '1px solid var(--color-error-500, #c53030)',
        borderRadius: '0.375rem',
        cursor: 'pointer',
        fontSize: '0.75rem',
        whiteSpace: 'nowrap',
      }}
    >
      Thử lại
    </button>
  </div>
);

export class StreamErrorBoundary extends BaseErrorBoundary {
  override render(): ReactNode {
    if (!this.state.hasError || !this.state.error) {
      return this.props.children;
    }

    const { fallback } = this.props;
    if (typeof fallback === 'function') {
      return fallback(this.state.error, this.reset);
    }
    if (fallback) return fallback;

    return <StreamErrorFallback error={this.state.error} reset={this.reset} />;
  }
}
