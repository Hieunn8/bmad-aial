/**
 * Auth callback route — handles Keycloak OIDC redirect
 * Exchanges authorization code for tokens
 */
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';

export const Route = createFileRoute('/auth/callback')({
  component: AuthCallbackPage,
});

function AuthCallbackPage(): React.JSX.Element {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');
    const returnedState = params.get('state');
    const storedState = sessionStorage.getItem('oidc_state');

    if (error) {
      void navigate({ to: '/login' });
      return;
    }

    // Validate OIDC state parameter to prevent CSRF against the auth flow
    if (!returnedState || returnedState !== storedState) {
      void navigate({ to: '/login' });
      return;
    }

    sessionStorage.removeItem('oidc_state');

    if (!code) {
      void navigate({ to: '/login' });
      return;
    }

    // STUB: Token exchange to be implemented in Epic 2A
    void navigate({ to: '/' });
  }, [navigate]);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Đang xác thực..."
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        fontFamily: 'var(--font-family-base)',
        color: 'var(--color-neutral-600)',
      }}
    >
      <p>Đang xác thực, vui lòng chờ...</p>
    </div>
  );
}
