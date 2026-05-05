import { createFileRoute } from '@tanstack/react-router';
import { ForecastStudio } from '../../components/epic7/ForecastStudio';
import { pageShell } from '../../styles/shared';

export const Route = createFileRoute('/analytics/forecast')({
  component: () => (
    <div style={pageShell}>
      <ForecastStudio />
    </div>
  ),
});
