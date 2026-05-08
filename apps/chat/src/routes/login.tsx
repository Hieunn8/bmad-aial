import { createFileRoute, redirect, useNavigate, useRouter } from '@tanstack/react-router';
import { useState } from 'react';
import { useAuth } from '../auth/AuthProvider';

export const Route = createFileRoute('/login')({
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) {
      throw redirect({ to: '/' });
    }
  },
  component: LoginPage,
});

function LoginPage(): React.JSX.Element {
  const auth = useAuth();
  const navigate = useNavigate();
  const router = useRouter();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123!');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handlePasswordLogin(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await auth.loginWithPassword(username, password);
      await router.invalidate();
      await navigate({ to: '/chat', replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Đăng nhập thất bại');
    } finally {
      setSubmitting(false);
    }
  }

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
      <div
        style={{
          width: '100%',
          maxWidth: '28rem',
          backgroundColor: 'var(--color-surface)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-8)',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--color-border)',
        }}
      >
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
          <h1 id="login-heading" style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>
            AIAL Enterprise
          </h1>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: 'var(--space-1)', textAlign: 'center' }}>
            Đăng nhập bằng tài khoản nội bộ hoặc SSO
          </p>
        </div>

        <form onSubmit={(event) => void handlePasswordLogin(event)} style={{ display: 'grid', gap: '0.85rem' }}>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Tên đăng nhập (username)"
            style={{
              width: '100%',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
            }}
          />
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Mật khẩu (password)"
            style={{
              width: '100%',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
            }}
          />
          <button
            type="submit"
            disabled={submitting}
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
            }}
          >
            {submitting ? 'Đang đăng nhập...' : 'Đăng nhập bằng user/pass'}
          </button>
        </form>

        <div style={{ marginTop: '1rem', display: 'grid', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={() => void auth.login()}
            style={{
              width: '100%',
              padding: 'var(--space-3) var(--space-4)',
              backgroundColor: 'white',
              color: 'var(--color-primary)',
              border: '1px solid var(--color-primary)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: 'var(--font-size-md)',
              fontWeight: 'var(--font-weight-medium)',
            }}
          >
            Đăng nhập bằng SSO
          </button>
          {error ? (
            <div role="alert" style={{ color: '#991b1b', fontSize: '0.9rem' }}>
              {error}
            </div>
          ) : null}
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-400)', textAlign: 'center' }}>
            Tài khoản mặc định local: <strong>admin / admin123!</strong>
          </div>
        </div>
      </div>
    </main>
  );
}
