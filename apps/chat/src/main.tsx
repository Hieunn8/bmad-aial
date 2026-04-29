/**
 * main.tsx — Application entry point
 * Loads design tokens CSS, mounts React app
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@aial/ui/styles/tokens.css';
import './styles/global.css';
import { App } from './App';

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('[AIAL] Root element #root not found in DOM');
}

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
