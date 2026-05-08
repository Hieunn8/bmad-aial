import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import {
  AuthSession,
  beginLoginRedirect,
  buildLogoutUrl,
  clearStoredAuthSession,
  completeLoginCallback,
  ensureFreshSession,
  getStoredAuthSession,
  loginWithPassword,
} from './session';

interface AuthContextValue {
  isAuthenticated: boolean;
  isReady: boolean;
  session: AuthSession | null;
  login: () => Promise<void>;
  loginWithPassword: (username: string, password: string) => Promise<AuthSession>;
  logout: () => void;
  refreshSession: () => Promise<AuthSession | null>;
  handleAuthCallback: (search: string) => Promise<AuthSession>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const anonymousAuthContext: AuthContextValue = {
  isAuthenticated: false,
  isReady: true,
  session: null,
  login: async () => {},
  loginWithPassword: async () => {
    throw new Error('Auth provider not available');
  },
  logout: () => {},
  refreshSession: async () => null,
  handleAuthCallback: async () => {
    throw new Error('Auth provider not available');
  },
};

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [session, setSession] = useState<AuthSession | null>(getStoredAuthSession());
  const [isReady, setIsReady] = useState(false);

  async function refreshSession(): Promise<AuthSession | null> {
    const nextSession = await ensureFreshSession();
    setSession(nextSession);
    return nextSession;
  }

  useEffect(() => {
    void refreshSession().finally(() => setIsReady(true));

    const intervalId = window.setInterval(() => {
      void refreshSession();
    }, 60_000);

    const handleStorage = (): void => {
      setSession(getStoredAuthSession());
    };
    window.addEventListener('storage', handleStorage);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(session?.accessToken),
      isReady,
      session,
      login: async () => {
        await beginLoginRedirect();
      },
      loginWithPassword: async (username: string, password: string) => {
        const nextSession = await loginWithPassword(username, password);
        flushSync(() => {
          setSession(nextSession);
          setIsReady(true);
        });
        return nextSession;
      },
      logout: () => {
        const logoutUrl = buildLogoutUrl(session);
        clearStoredAuthSession();
        setSession(null);
        if (session?.idToken) {
          window.location.href = logoutUrl;
        } else {
          window.location.href = `${window.location.origin}/login`;
        }
      },
      refreshSession,
      handleAuthCallback: async (search: string) => {
        const nextSession = await completeLoginCallback(search);
        setSession(nextSession);
        return nextSession;
      },
    }),
    [isReady, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext) ?? anonymousAuthContext;
}
