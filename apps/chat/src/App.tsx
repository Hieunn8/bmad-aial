/**
 * App.tsx — TanStack Router + Query provider setup
 * Architecture: TanStack Router 1.168.23, defaultPreload: 'intent' (Story 1.7 AC)
 */
import { RouterProvider, createRouter } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { routeTree } from './routeTree.gen';
import { AppErrorBoundary } from './components/ErrorBoundaries';
import { AuthProvider, useAuth } from './auth/AuthProvider';

// ============================================================
// Query Client
// ============================================================

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, // 1 minute
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// ============================================================
// Router — TanStack Router with defaultPreload: 'intent'
// Story 1.7 AC: TanStack Router `defaultPreload: 'intent'` configured
// ============================================================

const router = createRouter({
  routeTree,
  defaultPreload: 'intent',   // AC requirement
  defaultPreloadStaleTime: 0,
  context: {
    queryClient,
    auth: {
      isAuthenticated: false,
      isReady: false,
      session: null,
      login: async () => {},
      loginWithPassword: async () => {
        throw new Error('Auth provider not ready');
      },
      logout: () => {},
      refreshSession: async () => null,
      handleAuthCallback: async () => {
        throw new Error('Auth provider not ready');
      },
    },
  },
});

// Register router for type-safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

// ============================================================
// App Component
// ============================================================

export function App(): React.JSX.Element {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

function AppShell(): React.JSX.Element {
  const auth = useAuth();
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} context={{ queryClient, auth }} />
      </QueryClientProvider>
    </AppErrorBoundary>
  );
}
