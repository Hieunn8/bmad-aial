import type { QueryClient } from '@tanstack/react-query';
import type { AuthSession } from './auth/session';

export interface RouterAuthContext {
  isAuthenticated: boolean;
  isReady: boolean;
  session: AuthSession | null;
  login: () => Promise<void>;
  loginWithPassword: (username: string, password: string) => Promise<AuthSession>;
  logout: () => void;
  refreshSession: () => Promise<AuthSession | null>;
  handleAuthCallback: (search: string) => Promise<AuthSession>;
}

export interface AppRouterContext {
  queryClient: QueryClient;
  auth: RouterAuthContext;
}
