import { createFileRoute } from '@tanstack/react-router';
import { DepartmentsPage } from '../../pages/admin/DepartmentsPage';

export const Route = createFileRoute('/admin/departments')({
  component: DepartmentsPage,
});
