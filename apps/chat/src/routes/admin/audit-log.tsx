import { createFileRoute } from '@tanstack/react-router';
import { AuditLogPage } from '../../pages/admin/AuditLogPage';

export const Route = createFileRoute('/admin/audit-log')({ component: AuditLogPage });
