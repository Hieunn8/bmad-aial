import { createFileRoute } from '@tanstack/react-router';
import { TrendAnalysisPanel } from '../../components/epic7/TrendAnalysisPanel';
import { pageShell } from '../../styles/shared';

export const Route = createFileRoute('/analytics/trend')({
  component: () => (
    <div style={pageShell}>
      <TrendAnalysisPanel />
    </div>
  ),
});
