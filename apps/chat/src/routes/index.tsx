/**
 * Index route — redirects to authenticated chat or login
 */
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    // For now redirect to login — auth middleware will handle in Story 1.3
    throw redirect({ to: '/login' });
  },
  component: () => null,
});
