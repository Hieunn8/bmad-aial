/**
 * ConnectionStatusBanner — Shows degraded-state message when SSE connection drops
 * Story 1.9 AC: frontend's ConnectionStatusBanner displays a degraded-state message
 * UX-DR21: appears within 3 seconds if SSE drops
 */
import { useEffect } from 'react';
import { useUIStore } from '../../stores/uiStore';

export function ConnectionStatusBanner(): React.JSX.Element | null {
  const isOnline = useUIStore((s) => s.isOnline);
  const setOnline = useUIStore((s) => s.setOnline);

  // Monitor browser online/offline events
  useEffect(() => {
    const handleOnline = (): void => setOnline(true);
    const handleOffline = (): void => setOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return (): void => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnline]);

  if (isOnline) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      style={{
        position: 'sticky',
        top: 'var(--header-height)',
        zIndex: 'var(--z-sticky)',
        backgroundColor: 'var(--color-warning-50)',
        borderBottom: '1px solid var(--color-warning-500)',
        padding: 'var(--space-2) var(--space-4)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        fontFamily: 'var(--font-family-base)',
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-warning-700)',
      }}
    >
      <span aria-hidden="true">⚠️</span>
      <span>
        Mất kết nối mạng. Đang thử kết nối lại...
      </span>
    </div>
  );
}
