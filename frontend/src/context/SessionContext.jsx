/**
 * Session Context
 *
 * Manages session state across the application:
 * - session_id for SSE connection
 * - user_id for API calls
 * - current_flow_type (hp, hnp, clarification)
 *
 * AP2 Compliance:
 * - Session tracks flow type for proper mandate handling
 * - User ID links mandates to authenticated user
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { generateSessionId } from '../services/sse';

const SessionContext = createContext();

/**
 * Session provider component
 */
export function SessionProvider({ children }) {
  const [sessionId, setSessionId] = useState(null);
  const [userId, setUserId] = useState('user_demo_001'); // Hardcoded for demo per spec Assumption 3
  const [flowType, setFlowType] = useState(null); // 'hp', 'hnp', 'clarification', null
  const [conversationState, setConversationState] = useState({
    intent: null,
    cart: null,
    products: [],
    stage: 'initial' // initial, searching, cart_building, payment, complete
  });

  // Initialize session on mount
  useEffect(() => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    console.log('Session initialized:', newSessionId);
  }, []);

  /**
   * Reset session (start new conversation)
   */
  const resetSession = () => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    setFlowType(null);
    setConversationState({
      intent: null,
      cart: null,
      products: [],
      stage: 'initial'
    });
    console.log('Session reset:', newSessionId);
  };

  /**
   * Update conversation state
   */
  const updateState = (updates) => {
    setConversationState(prev => ({
      ...prev,
      ...updates
    }));
  };

  const value = {
    sessionId,
    setSessionId,  // Add setSessionId so ChatInterface can update session
    userId,
    setUserId,
    flowType,
    setFlowType,
    conversationState,
    setConversationState,
    updateState,
    resetSession
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

/**
 * Hook to use session context
 */
export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
}
