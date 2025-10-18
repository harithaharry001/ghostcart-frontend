/**
 * GhostCart App
 * AP2-compliant mandate-based payment demonstration
 *
 * Note: SSEProvider removed - ChatInterface now manages its own EventSource connection
 * via the unified /api/chat/stream endpoint
 */
import React from 'react';
import { SessionProvider } from './context/SessionContext';
import Home from './pages/Home';
import './index.css';

export default function App() {
  return (
    <SessionProvider>
      <Home />
    </SessionProvider>
  );
}
