import { createFileRoute, redirect } from '@tanstack/react-router';
import { MemoryStudioPage } from '../pages/MemoryStudioPage';

export const Route = createFileRoute('/memory')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: MemoryStudioPage,
});
