import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';

import { useAuth } from '../auth/AuthProvider';
import { Epic5BWorkspace } from '../components/epic5b/Epic5BWorkspace';

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: IndexPage,
});

function IndexPage(): React.JSX.Element {
  const auth = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (auth.isReady && !auth.isAuthenticated) {
      void navigate({ to: '/login' });
    }
  }, [auth.isAuthenticated, auth.isReady, navigate]);

  if (!auth.isReady) {
    return <div style={{ padding: '2rem' }}>Dang kiem tra phien dang nhap...</div>;
  }
  if (!auth.isAuthenticated) {
    return <div style={{ padding: '2rem' }}>Dang chuyen den man dang nhap...</div>;
  }
  return <Epic5BWorkspace />;
}
