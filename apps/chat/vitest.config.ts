import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
      },
      exclude: [
        'src/routeTree.gen.ts',
        'src/test/**',
        '**/*.d.ts',
      ],
    },
  },
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      '@': resolve(__dirname, 'src'),
      '@aial/types': resolve(__dirname, '../../packages/types/src'),
      '@aial/ui/export-confirmation-bar': resolve(__dirname, '../../packages/ui/src/components/ExportConfirmationBar.tsx'),
      '@aial/ui/export-job-status': resolve(__dirname, '../../packages/ui/src/components/ExportJobStatus.tsx'),
      '@aial/ui/chart-reveal': resolve(__dirname, '../../packages/ui/src/components/ChartReveal.tsx'),
      '@aial/ui/confidence-breakdown-card': resolve(__dirname, '../../packages/ui/src/components/ConfidenceBreakdownCard.tsx'),
      '@aial/ui/provenance-drawer': resolve(__dirname, '../../packages/ui/src/components/ProvenanceDrawer.tsx'),
    },
  },
});
