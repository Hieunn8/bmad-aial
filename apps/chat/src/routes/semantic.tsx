import { createFileRoute, redirect } from '@tanstack/react-router';
import { SemanticStudioPage } from '../pages/SemanticStudioPage';

export const Route = createFileRoute('/semantic')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
    const roles = context.auth.session?.claims.roles ?? [];
    if (!roles.includes('admin') && !roles.includes('data_owner')) {
      throw redirect({ to: '/chat' });
    }
  },
  component: SemanticStudioPage,
});
