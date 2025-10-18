/**
 * Chat Interface Component
 *
 * Conversational interface for HP and HNP purchase flows.
 * Displays message history, streaming agent updates, and user input.
 *
 * AP2 Compliance:
 * - Shows agent reasoning in real-time (transparency)
 * - Displays mandate generation progress
 * - Streams payment processing status
 */
import React, { useState, useEffect, useRef } from 'react';
import { useSession } from '../context/SessionContext';
import { useSSE, useSSEEvent } from '../context/SSEContext';
import { api } from '../services/api';
import SignatureModal from './SignatureModal';
import MandateChainViz from './MandateChainViz';

export default function ChatInterface() {
  const { sessionId, userId, flowType, conversationState, setConversationState, setFlowType } = useSession();
  const { isConnected } = useSSE();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);
  const welcomeShown = useRef(false);

  // Signature Modal State
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [pendingMandate, setPendingMandate] = useState(null);
  const [mandateType, setMandateType] = useState(null);
  const [mandateFlow, setMandateFlow] = useState(null);
  const [mandateConstraints, setMandateConstraints] = useState(null);

  // Mandate Chain State
  const [mandateChain, setMandateChain] = useState(null);

  /**
   * Auto-scroll to bottom when new messages arrive
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /**
   * Add initial welcome message (only once)
   */
  useEffect(() => {
    if (!welcomeShown.current) {
      welcomeShown.current = true;
      addMessage({
        type: 'system',
        content: "Hi! I'm GhostCart, your AI shopping assistant. I can help you buy products right now or set up monitoring for price drops. What would you like to do?",
        timestamp: new Date()
      });
    }
  }, []);

  /**
   * Listen for SSE events and display in chat
   * Only showing essential user-facing events
   */

  // Only show clarification questions (important for user)
  useSSEEvent('clarification_needed', (data) => {
    addMessage({
      type: 'clarification',
      content: data.question,
      reasoning: data.reasoning,
      timestamp: new Date()
    });
  });

  useSSEEvent('product_results', (data) => {
    addMessage({
      type: 'products',
      content: `Found ${data.count} products`,
      products: data.products,
      timestamp: new Date()
    });
  });

  // Signature required - show modal
  useSSEEvent('signature_required', (data) => {
    setPendingMandate(data.mandate);
    setMandateType(data.mandate_type);
    setMandateFlow(data.flow);
    setMandateConstraints(data.mandate?.constraints || null);
    setShowSignatureModal(true);
  });

  // Payment complete - show mandate chain
  useSSEEvent('payment_complete', (data) => {
    setMandateChain(data.mandate_chain);
  });

  // Payment success/failure (user needs to see this)
  useSSEEvent('payment_authorized', (data) => {
    addMessage({
      type: 'success',
      content: `Payment authorized! Amount: $${(data.amount_cents / 100).toFixed(2)}`,
      timestamp: new Date()
    });
  });

  useSSEEvent('payment_declined', (data) => {
    addMessage({
      type: 'error',
      content: `Payment declined: ${data.errors.join(', ')}`,
      timestamp: new Date()
    });
  });

  /**
   * Add message to history
   */
  const addMessage = (message) => {
    setMessages(prev => [...prev, message]);
  };

  /**
   * Handle signature confirmation
   */
  const handleSignatureConfirm = async () => {
    // Close modal
    setShowSignatureModal(false);

    // Add system message
    addMessage({
      type: 'system',
      content: '✓ Signature confirmed. Processing payment...',
      timestamp: new Date()
    });

    // Send confirmation to backend (user's "yes" triggers payment processing)
    setInputMessage('');
    setIsSending(true);

    try {
      const response = await api.post('/chat', {
        message: 'yes, I confirm',
        session_id: sessionId,
        user_id: userId,
        conversation_state: conversationState
      });

      setConversationState(response.state);
      setFlowType(response.flow_type);

      addMessage({
        type: 'agent',
        content: response.response,
        timestamp: new Date()
      });
    } catch (error) {
      console.error('Failed to send confirmation:', error);
      addMessage({
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      });
    } finally {
      setIsSending(false);
    }
  };

  /**
   * Handle signature cancellation
   */
  const handleSignatureCancel = () => {
    setShowSignatureModal(false);
    addMessage({
      type: 'system',
      content: 'Signature cancelled. Feel free to start over or try something else.',
      timestamp: new Date()
    });
  };

  /**
   * Send user message
   */
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isSending) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);

    // Add user message to display
    addMessage({
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    });

    try {
      // Send to chat endpoint
      const response = await api.post('/chat', {
        message: userMessage,
        session_id: sessionId,
        user_id: userId,
        conversation_state: conversationState
      });

      // Update session context with new state and flow type
      setConversationState(response.state);
      setFlowType(response.flow_type);

      // Add agent response
      addMessage({
        type: 'agent',
        content: response.response,
        timestamp: new Date()
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      addMessage({
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      });
    } finally {
      setIsSending(false);
    }
  };

  /**
   * Handle Enter key
   */
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  /**
   * Render message based on type
   */
  const renderMessage = (msg, index) => {
    const baseClasses = "p-3 rounded-lg mb-2 max-w-[80%]";

    switch (msg.type) {
      case 'user':
        return (
          <div key={index} className="flex justify-end">
            <div className={`${baseClasses} bg-primary text-white`}>
              {msg.content}
            </div>
          </div>
        );

      case 'agent':
        return (
          <div key={index} className="flex justify-start">
            <div className={`${baseClasses} bg-gray-100 text-gray-800`}>
              {msg.content}
            </div>
          </div>
        );

      case 'system':
        return (
          <div key={index} className="flex justify-center">
            <div className={`${baseClasses} bg-blue-50 text-blue-800 border border-blue-200 text-sm`}>
              {msg.content}
            </div>
          </div>
        );

      case 'success':
        return (
          <div key={index} className="flex justify-center">
            <div className={`${baseClasses} bg-success-light text-success-dark border border-success text-sm font-medium`}>
              ✓ {msg.content}
            </div>
          </div>
        );

      case 'error':
        return (
          <div key={index} className="flex justify-center">
            <div className={`${baseClasses} bg-error-light text-error-dark border border-error text-sm`}>
              ✗ {msg.content}
            </div>
          </div>
        );

      case 'clarification':
        return (
          <div key={index} className="mb-4">
            <div className="flex justify-start">
              <div className={`${baseClasses} bg-orange-50 text-orange-900 border-2 border-orange-400 shadow-md max-w-full`}>
                <div className="flex items-start gap-2 mb-2">
                  <span className="text-2xl">❓</span>
                  <div className="flex-1">
                    <p className="font-semibold mb-1">Clarification Needed</p>
                    <p>{msg.content}</p>
                    {msg.reasoning && (
                      <p className="text-xs text-orange-700 mt-2 italic">
                        Reason: {msg.reasoning}
                      </p>
                    )}
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-orange-200">
                  <p className="text-xs text-orange-700">
                    💡 The Supervisor Agent needs more information to route your request correctly.
                    Please provide more details in your next message.
                  </p>
                </div>
              </div>
            </div>
          </div>
        );

      case 'products':
        return (
          <div key={index} className="mb-4">
            <div className="text-sm text-gray-600 mb-2">{msg.content}</div>
            {msg.products && msg.products.length > 0 && (
              <div className="grid gap-2">
                {msg.products.map((product, idx) => (
                  <div key={idx} className="p-3 bg-white border border-gray-200 rounded-lg hover:border-primary transition-colors">
                    <div className="font-medium">{product.name}</div>
                    <div className="text-sm text-gray-600">{product.description}</div>
                    <div className="flex justify-between items-center mt-2">
                      <span className="font-bold text-primary">
                        ${(product.price_cents / 100).toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {product.stock_status === 'in_stock' ? '✓ In Stock' : '✗ Out of Stock'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-primary to-primary-dark text-white">
        <h2 className="text-xl font-bold">GhostCart Assistant</h2>
        <div className="text-xs mt-1 flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          {flowType && (
            <span className="ml-2 px-2 py-0.5 bg-white bg-opacity-20 rounded">
              {flowType === 'hp' ? 'Immediate Purchase' :
               flowType === 'hnp' ? 'Monitoring' :
               flowType === 'clarification' ? 'Clarifying Intent' :
               flowType}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.map((msg, idx) => renderMessage(msg, idx))}

        {/* Mandate Chain Visualization */}
        {mandateChain && (
          <div className="mt-4">
            <MandateChainViz chain={mandateChain} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isSending}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSending || !inputMessage.trim()}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isSending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>

      {/* Signature Modal */}
      <SignatureModal
        isOpen={showSignatureModal}
        mandate={pendingMandate}
        mandateType={mandateType}
        flow={mandateFlow}
        constraints={mandateConstraints}
        onSign={handleSignatureConfirm}
        onCancel={handleSignatureCancel}
      />
    </div>
  );
}
