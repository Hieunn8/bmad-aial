import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { useAuth } from '../../auth/AuthProvider';

export const Route = createFileRoute('/auth/callback')({
  component: AuthCallbackPage,
});

function AuthCallbackPage(): React.JSX.Element {
  const auth = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('Dang xac thuc, vui long cho...');

  useEffect(() => {
    let active = true;

    const run = async (): Promise<void> => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('error')) {
        setMessage('Dang nhap that bai. Dang quay lai man login...');
        void navigate({ to: '/login' });
        return;
      }

      try {
        await auth.handleAuthCallback(window.location.search);
        if (!active) {
          return;
        }
        void navigate({ to: '/' });
      } catch {
        if (active) {
          setMessage('Khong the hoan tat dang nhap. Dang quay lai man login...');
          window.setTimeout(() => {
            void navigate({ to: '/login' });
          }, 1200);
        }
      }
    };

    void run();
    return () => {
      active = false;
    };
  }, [auth, navigate]);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Dang xac thuc"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        fontFamily: 'var(--font-family-base)',
        color: 'var(--color-neutral-600)',
      }}
    >
      <p>{message}</p>
    </div>
  );
}
