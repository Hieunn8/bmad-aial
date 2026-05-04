import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { TanStackRouterVite } from '@tanstack/router-vite-plugin';
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    TanStackRouterVite(),
  ],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      '@': resolve(__dirname, 'src'),
      '@aial/ui/export-confirmation-bar': resolve(__dirname, '../../packages/ui/src/components/ExportConfirmationBar.tsx'),
      '@aial/ui/export-job-status': resolve(__dirname, '../../packages/ui/src/components/ExportJobStatus.tsx'),
      '@aial/ui/chart-reveal': resolve(__dirname, '../../packages/ui/src/components/ChartReveal.tsx'),
      '@aial/ui/confidence-breakdown-card': resolve(__dirname, '../../packages/ui/src/components/ConfidenceBreakdownCard.tsx'),
      '@aial/ui/provenance-drawer': resolve(__dirname, '../../packages/ui/src/components/ProvenanceDrawer.tsx'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    proxy: {
      '/v1': {
        // Local dev proxies API traffic straight to FastAPI because Kong only
        // exposes a subset of routes in this workspace.
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2020',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['@tanstack/react-router'],
          query: ['@tanstack/react-query'],
          state: ['zustand'],
        },
      },
    },
  },
});
