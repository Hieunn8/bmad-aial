/**
 * Root route — wraps the entire app
 * Architecture: TanStack Router 1.168.23 with file-based routes
 * UX-DR22: defaultPreload: 'intent' configured here
 */
import {
  createRootRoute,
  Outlet,
} from '@tanstack/react-router';
import { AppErrorBoundary, PageErrorBoundary } from '../components/ErrorBoundaries';
import { ConnectionStatusBanner } from '../components/streaming/ConnectionStatusBanner';
import { AppLayout } from '../components/AppLayout';

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent(): React.JSX.Element {
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
