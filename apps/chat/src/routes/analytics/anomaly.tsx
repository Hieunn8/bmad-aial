import { createFileRoute } from '@tanstack/react-router';
import { AnomalyAlertsPanel } from '../../components/epic7/AnomalyAlertsPanel';
import { pageShell } from '../../styles/shared';

export const Route = createFileRoute('/analytics/anomaly')({
  component: () => (
    <div style={pageShell}>
      <AnomalyAlertsPanel />
    </div>
  ),
});
