/**
 * SSE Context
 *
 * Manages Server-Sent Events connection for real-time agent updates.
 *
 * AP2 Compliance:
 * - Provides real-time visibility into agent reasoning
 * - Streams mandate generation progress
 * - Shows payment processing status
 * - Enables transparent autonomous actions
 */
import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { createSSEConnection } from '../services/sse';
import { useSession } from './SessionContext';

const SSEContext = createContext();

/**
 * SSE connection states
 */
export const SSE_STATUS = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

/**
 * SSE provider component
 */
export function SSEProvider({ children }) {
  const { sessionId } = useSession();
  const [status, setStatus] = useState(SSE_STATUS.DISCONNECTED);
  const [events, setEvents] = useState([]); // Event history for debugging
  const [lastEvent, setLastEvent] = useState(null);
  const connectionRef = useRef(null);
  const listenersRef = useRef({});

  /**
   * Connect to SSE stream when session ID is available
   */
  useEffect(() => {
    if (!sessionId) return;

    console.log('Creating SSE connection for session:', sessionId);
    setStatus(SSE_STATUS.CONNECTING);

    // Create connection
    const connection = createSSEConnection(sessionId);
    connectionRef.current = connection;

    // Connection status listener
    connection.on('connection', (data) => {
      if (data.status === 'connected') {
        setStatus(SSE_STATUS.CONNECTED);
      } else if (data.status === 'error') {
        setStatus(SSE_STATUS.ERROR);
      } else if (data.status === 'disconnected') {
        setStatus(SSE_STATUS.DISCONNECTED);
      }
    });

    // Generic message listener for debugging
    connection.on('message', (data) => {
      console.log('SSE message received:', data);
      addEvent({ type: 'message', data, timestamp: new Date() });
      setLastEvent({ type: 'message', data, timestamp: new Date() });
    });

    // Connect
    connection.connect();

    // Register all existing listeners
    Object.entries(listenersRef.current).forEach(([eventType, callbacks]) => {
      callbacks.forEach(callback => {
        connection.on(eventType, callback);
      });
    });

    // Cleanup on unmount or session change
    return () => {
      console.log('Cleaning up SSE connection');
      if (connectionRef.current) {
        connectionRef.current.disconnect();
        connectionRef.current = null;
      }
    };
  }, [sessionId]);

  /**
   * Add event to history
   */
  const addEvent = (event) => {
    setEvents(prev => [...prev.slice(-99), event]); // Keep last 100 events
  };

  /**
   * Subscribe to specific event type
   *
   * @param {string} eventType - Event type to listen for
   * @param {function} callback - Callback function
   */
  const subscribe = (eventType, callback) => {
    // Store listener reference
    if (!listenersRef.current[eventType]) {
      listenersRef.current[eventType] = [];
    }
    listenersRef.current[eventType].push(callback);

    // Register with connection if it exists
    if (connectionRef.current) {
      connectionRef.current.on(eventType, callback);
    }

    // Return unsubscribe function
    return () => {
      // Remove from listeners ref
      if (listenersRef.current[eventType]) {
        listenersRef.current[eventType] = listenersRef.current[eventType].filter(
          cb => cb !== callback
        );
      }

      // Unregister from connection
      if (connectionRef.current) {
        connectionRef.current.off(eventType, callback);
      }
    };
  };

  /**
   * Clear event history
   */
  const clearEvents = () => {
    setEvents([]);
    setLastEvent(null);
  };

  /**
   * Reconnect SSE
   */
  const reconnect = () => {
    if (connectionRef.current) {
      connectionRef.current.disconnect();
      setTimeout(() => {
        if (connectionRef.current) {
          connectionRef.current.connect();
        }
      }, 1000);
    }
  };

  const value = {
    status,
    events,
    lastEvent,
    subscribe,
    clearEvents,
    reconnect,
    isConnected: status === SSE_STATUS.CONNECTED
  };

  return (
    <SSEContext.Provider value={value}>
      {children}
    </SSEContext.Provider>
  );
}

/**
 * Hook to use SSE context
 */
export function useSSE() {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSE must be used within SSEProvider');
  }
  return context;
}

/**
 * Hook to subscribe to specific event type
 *
 * @param {string} eventType - Event type to listen for
 * @param {function} callback - Callback function
 */
export function useSSEEvent(eventType, callback) {
  const { subscribe } = useSSE();

  useEffect(() => {
    const unsubscribe = subscribe(eventType, callback);
    return unsubscribe;
  }, [eventType, callback, subscribe]);
}
