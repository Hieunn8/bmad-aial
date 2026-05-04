/**
 * Root route — wraps the entire app
 * Architecture: TanStack Router 1.168.23 with file-based routes
 * UX-DR22: defaultPreload: 'intent' configured here
 */
import {
  createRootRouteWithContext,
  Outlet,
  useRouterState,
} from '@tanstack/react-router';
import { AppErrorBoundary, PageErrorBoundary } from '../components/ErrorBoundaries';
import { ConnectionStatusBanner } from '../components/streaming/ConnectionStatusBanner';
import { AppLayout } from '../components/AppLayout';
import type { AppRouterContext } from '../router-context';

export const Route = createRootRouteWithContext<AppRouterContext>()({
  component: RootComponent,
});

function RootComponent(): React.JSX.Element {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  if (pathname === '/login' || pathname === '/auth/callback') {
    return (
      <AppErrorBoundary>
        <PageErrorBoundary>
          <Outlet />
        </PageErrorBoundary>
      </AppErrorBoundary>
    );
  }
  return (
    <AppErrorBoundary>
      <AppLayout>
        <ConnectionStatusBanner />
        <PageErrorBoundary>
          <Outlet />
        </PageErrorBoundary>
      </AppLayout>
    </AppErrorBoundary>
  );
}
