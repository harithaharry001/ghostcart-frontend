/**
 * GhostCart App
 * AP2-compliant mandate-based payment demonstration
 *
 * Note: SSE events are handled through ChatInterface's /api/chat/stream connection
 * No separate SSEProvider needed
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
