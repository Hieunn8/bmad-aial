import { createFileRoute } from '@tanstack/react-router';
import { DocumentAdminPanel } from '../../components/rag/DocumentAdminPanel';
import { pageShell } from '../../styles/shared';

export const Route = createFileRoute('/admin/documents')({
  component: () => (
    <div style={pageShell}>
      <DocumentAdminPanel />
    </div>
  ),
});
