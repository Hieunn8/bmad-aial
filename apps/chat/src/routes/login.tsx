/**
 * Login route — public, redirects to Keycloak OIDC
 * Architecture: FR-A1 SSO via Keycloak
 * Story 1.7 AC: auth redirect to Keycloak login page works
 */
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/login')({
  // If already authenticated, redirect to home
  beforeLoad: ({ context }) => {
    // Type-safe auth context check — auth context injected in main.tsx
    const authContext = context as { isAuthenticated?: boolean };
    if (authContext.isAuthenticated) {
      throw redirect({ to: '/' });
    }
  },
  component: LoginPage,
});

/** Keycloak OIDC redirect URL builder */
function buildKeycloakLoginUrl(): string {
  const keycloakBase =
    import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080';
  const realm = import.meta.env.VITE_KEYCLOAK_REALM ?? 'aial';
  const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'aial-frontend';
  const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);

  return (
    `${keycloakBase}/realms/${realm}/protocol/openid-connect/auth` +
    `?client_id=${clientId}` +
    `&redirect_uri=${redirectUri}` +
    `&response_type=code` +
    `&scope=openid+profile+email` +
    `&prompt=login`
  );
}

function LoginPage(): React.JSX.Element {
  const handleLogin = (): void => {
    window.location.href = buildKeycloakLoginUrl();
  };

  return (
    <main
      aria-labelledby="login-heading"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: 'var(--space-6)',
        backgroundColor: 'var(--color-background)',
        fontFamily: 'var(--font-family-base)',
      }}
    >
      {/* ARIA landmark: main login content */}
      <div
        style={{
          width: '100%',
          maxWidth: '24rem',
          backgroundColor: 'var(--color-surface)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-8)',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Logo / Brand */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            marginBottom: 'var(--space-6)',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: '3rem',
              height: '3rem',
              backgroundColor: 'var(--color-primary)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 'var(--space-3)',
              color: 'white',
              fontSize: '1.5rem',
              fontWeight: 700,
            }}
          >
            AI
          </div>

          <h1
            id="login-heading"
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-neutral-900)',
              margin: 0,
              textAlign: 'center',
            }}
          >
            AIAL Enterprise
          </h1>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-neutral-500)',
              marginTop: 'var(--space-1)',
              textAlign: 'center',
            }}
          >
            Trợ lý AI doanh nghiệp
          </p>
        </div>

        {/* Login Button — triggers Keycloak SSO */}
        <button
          type="button"
          onClick={handleLogin}
          style={{
            width: '100%',
            padding: 'var(--space-3) var(--space-4)',
            backgroundColor: 'var(--color-primary)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontSize: 'var(--font-size-md)',
            fontWeight: 'var(--font-weight-medium)',
            fontFamily: 'var(--font-family-base)',
            transition: 'background-color var(--animation-duration-fast) var(--animation-ease-out)',
          }}
          aria-label="Đăng nhập bằng SSO"
        >
          Đăng nhập bằng SSO
        </button>

        <p
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-neutral-400)',
            textAlign: 'center',
            marginTop: 'var(--space-4)',
          }}
        >
          Sử dụng tài khoản tổ chức (LDAP/AD) để đăng nhập
        </p>
      </div>
    </main>
  );
}
