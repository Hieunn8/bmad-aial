import { createFileRoute } from '@tanstack/react-router';
import { DrilldownExplainabilityPanel } from '../../components/epic7/DrilldownExplainabilityPanel';
import { pageShell } from '../../styles/shared';

export const Route = createFileRoute('/analytics/drilldown')({
  component: () => (
    <div style={pageShell}>
      <DrilldownExplainabilityPanel />
    </div>
  ),
});
