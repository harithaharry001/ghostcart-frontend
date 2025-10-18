/**
 * Chat Interface Component (Streaming Version)
 *
 * Uses the unified /api/chat/stream endpoint for real-time streaming.
 * Single EventSource connection handles both chat and events.
 *
 * AP2 Compliance:
 * - Real-time agent transparency via streaming
 * - Displays mandate generation progress
 * - Streams payment processing status
 */
import React, { useState, useEffect, useRef } from 'react';
import { useSession } from '../context/SessionContext';
import SignatureModal from './SignatureModal';
import MandateChainViz from './MandateChainViz';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function ChatInterface() {
  const { sessionId, setSessionId, userId, flowType, setFlowType } = useSession();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const messagesEndRef = useRef(null);
  const welcomeShown = useRef(null);
  const eventSourceRef = useRef(null);

  // Signature Modal State
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [pendingMandate, setPendingMandate] = useState(null);
  const [pendingCartData, setPendingCartData] = useState(null); // Store full cart for signing (HP flow)
  const [pendingIntentData, setPendingIntentData] = useState(null); // Store full intent for signing (HNP flow)
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
  }, [messages, currentStreamingMessage]);

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
   * Cleanup EventSource on unmount
   */
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  /**
   * Add message to chat history
   */
  const addMessage = (message) => {
    setMessages(prev => [...prev, { id: Date.now(), ...message }]);
  };

  /**
   * Send message using streaming endpoint
   */
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isSending) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);
    setIsStreaming(true);
    setCurrentStreamingMessage('');

    // Add user message to display
    addMessage({
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    });

    try {
      // Build streaming URL
      const params = new URLSearchParams({
        message: userMessage,
        user_id: userId,
      });

      if (sessionId) {
        params.append('session_id', sessionId);
      }

      const url = `${API_BASE_URL}/chat/stream?${params.toString()}`;
      console.log('Opening streaming connection:', url);

      // Create EventSource for streaming
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      let streamedResponse = '';
      let tempSessionId = sessionId;

      // Handle connection events
      eventSource.addEventListener('connected', (e) => {
        const data = JSON.parse(e.data);
        console.log('Connected:', data);
        if (data.session_id && !tempSessionId) {
          tempSessionId = data.session_id;
          setSessionId(data.session_id);
        }
      });

      // Handle agent thinking
      eventSource.addEventListener('agent_thinking', (e) => {
        const data = JSON.parse(e.data);
        console.log('Agent thinking:', data);
        // Optionally show thinking indicator
      });

      // Handle streaming text chunks
      eventSource.addEventListener('agent_chunk', (e) => {
        const data = JSON.parse(e.data);
        const textChunk = data.text || '';
        streamedResponse += textChunk;
        setCurrentStreamingMessage(streamedResponse);
      });

      // Handle tool use
      eventSource.addEventListener('tool_use', (e) => {
        const data = JSON.parse(e.data);
        console.log('Tool use:', data);

        // Show tool execution message
        if (data.tool_name === 'search_products') {
          addMessage({
            type: 'system',
            content: '🔍 Searching products...',
            timestamp: new Date()
          });
        } else if (data.tool_name === 'shopping_assistant') {
          addMessage({
            type: 'system',
            content: '🛍️ Routing to shopping assistant...',
            timestamp: new Date()
          });
        }
      });

      // Handle product results
      eventSource.addEventListener('product_results', (e) => {
        const data = JSON.parse(e.data);
        console.log('Product results:', data);

        addMessage({
          type: 'products',
          content: `Found ${data.count} products`,
          products: data.products,
          timestamp: new Date()
        });
      });

      // Handle cart created
      eventSource.addEventListener('cart_created', (e) => {
        const data = JSON.parse(e.data);
        console.log('Cart created:', data);

        // Store cart data for signing later
        setPendingCartData(data);

        // Extract total_cents from total object
        const totalCents = data.total?.total_cents || 0;

        addMessage({
          type: 'system',
          content: `✓ Cart created: ${data.items && data.items.length} item(s), Total: $${(totalCents / 100).toFixed(2)}`,
          timestamp: new Date()
        });
      });

      // Handle signature requested
      eventSource.addEventListener('signature_requested', (e) => {
        const data = JSON.parse(e.data);
        console.log('Signature requested:', data);

        // Store the full mandate data (not just ID)
        setPendingMandate({
          mandate_id: data.mandate_id,
          summary: data.summary,
          ...data  // Include any additional fields
        });
        setMandateType(data.mandate_type);

        // Determine flow type and store appropriate mandate data
        if (data.mandate_type === 'intent') {
          setMandateFlow('hnp');
          setPendingIntentData(data.mandate_data); // Store Intent data for signing
        } else {
          setMandateFlow('hp');
          // pendingCartData already set from cart_created event
        }

        setMandateConstraints(data.constraints || null);
        setShowSignatureModal(true);

        addMessage({
          type: 'system',
          content: '🔐 Signature required - please review and approve',
          timestamp: new Date()
        });
      });

      // Handle complete response
      eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Complete:', data);

        // Add final agent response
        if (streamedResponse) {
          addMessage({
            type: 'agent',
            content: streamedResponse,
            timestamp: new Date()
          });
        } else if (data.response) {
          addMessage({
            type: 'agent',
            content: data.response,
            timestamp: new Date()
          });
        }

        // Update session state
        if (data.session_id) {
          setSessionId(data.session_id);
        }
        if (data.flow_type) {
          setFlowType(data.flow_type);
        }

        // Close connection
        eventSource.close();
        setIsStreaming(false);
        setCurrentStreamingMessage('');
        setIsSending(false);
      });

      // Handle errors
      eventSource.addEventListener('error', (e) => {
        console.error('Streaming error:', e);

        let errorMessage = 'Connection error occurred';
        try {
          const data = JSON.parse(e.data);
          errorMessage = data.message || errorMessage;
        } catch {}

        addMessage({
          type: 'error',
          content: errorMessage,
          timestamp: new Date()
        });

        eventSource.close();
        setIsStreaming(false);
        setCurrentStreamingMessage('');
        setIsSending(false);
      });

      // Handle EventSource errors (connection issues)
      eventSource.onerror = (e) => {
        console.error('EventSource error:', e);

        addMessage({
          type: 'error',
          content: 'Connection lost. Please try again.',
          timestamp: new Date()
        });

        eventSource.close();
        setIsStreaming(false);
        setCurrentStreamingMessage('');
        setIsSending(false);
      };

    } catch (error) {
      console.error('Failed to send message:', error);
      addMessage({
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date()
      });
      setIsSending(false);
      setIsStreaming(false);
    }
  };

  /**
   * Handle Enter key to send message
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  /**
   * Handle signature confirmation
   */
  const handleSignatureConfirm = async () => {
    try {
      // Close modal
      setShowSignatureModal(false);

      // Add system message
      addMessage({
        type: 'system',
        content: '✓ Signing mandate...',
        timestamp: new Date()
      });

      // Determine which mandate data to send based on type
      const mandateData = mandateType === 'intent' ? pendingIntentData : pendingCartData;

      if (!mandateData) {
        throw new Error(`No ${mandateType} data available for signing`);
      }

      // Call backend API to sign the mandate
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/mandates/sign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mandate_id: pendingMandate?.mandate_id,
          mandate_type: mandateType,
          mandate_data: mandateData,
          signer_id: userId,
          signer_type: 'user'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to sign mandate');
      }

      const signedData = await response.json();
      console.log('Mandate signed:', signedData);

      // Add success message based on mandate type
      const successMessage = mandateType === 'intent'
        ? '✓ Signature confirmed. Activating monitoring...'
        : '✓ Signature confirmed. Processing payment...';

      addMessage({
        type: 'system',
        content: successMessage,
        timestamp: new Date()
      });

      // Automatically send confirmation message to agent
      const continueMessage = mandateType === 'intent'
        ? `I have signed the Intent mandate (ID: ${signedData.mandate_id}). Please activate the monitoring job.`
        : `I have signed the cart mandate (ID: ${signedData.mandate_id}). Please proceed with payment processing.`;

      // Send directly without setting input field
      const eventSource = new EventSource(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/chat/stream?message=${encodeURIComponent(continueMessage)}&session_id=${sessionId}&user_id=${userId}`
      );

      setIsStreaming(true);
      eventSourceRef.current = eventSource;

      let streamedResponse = '';

      // Handle agent response
      eventSource.addEventListener('agent_chunk', (e) => {
        const data = JSON.parse(e.data);
        streamedResponse += data.text || '';
        setCurrentStreamingMessage(streamedResponse);
      });

      eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);

        if (streamedResponse) {
          addMessage({
            type: 'agent',
            content: streamedResponse,
            timestamp: new Date()
          });
        }

        eventSource.close();
        setIsStreaming(false);
        setCurrentStreamingMessage('');
      });

      eventSource.addEventListener('error', (e) => {
        console.error('Stream error:', e);
        eventSource.close();
        setIsStreaming(false);
        setCurrentStreamingMessage('');
      });

    } catch (error) {
      console.error('Error signing mandate:', error);
      addMessage({
        type: 'error',
        content: `Failed to sign mandate: ${error.message}`,
        timestamp: new Date()
      });
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
   * Render message based on type
   */
  const renderMessage = (msg) => {
    switch (msg.type) {
      case 'user':
        return (
          <div key={msg.id} className="flex justify-end mb-4">
            <div className="bg-blue-500 text-white rounded-lg px-4 py-2 max-w-md">
              {msg.content}
            </div>
          </div>
        );

      case 'agent':
        return (
          <div key={msg.id} className="flex justify-start mb-4">
            <div className="bg-gray-200 text-gray-800 rounded-lg px-4 py-2 max-w-md">
              {msg.content}
            </div>
          </div>
        );

      case 'system':
        return (
          <div key={msg.id} className="flex justify-center mb-4">
            <div className="bg-yellow-100 text-yellow-800 rounded-lg px-4 py-2 text-sm">
              {msg.content}
            </div>
          </div>
        );

      case 'products':
        return (
          <div key={msg.id} className="flex justify-start mb-4">
            <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-2xl">
              <div className="font-semibold mb-2">{msg.content}</div>
              {msg.products && msg.products.map((product, idx) => (
                <div key={idx} className="border-t pt-2 mt-2">
                  <div className="font-medium">{product.name}</div>
                  <div className="text-sm text-gray-600">
                    ${(product.price_cents / 100).toFixed(2)}
                    {product.stock_status === 'in_stock' ? ' • In stock' : ' • Out of stock'}
                    {product.delivery_estimate_days && ` • Ships in ${product.delivery_estimate_days} days`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'success':
        return (
          <div key={msg.id} className="flex justify-center mb-4">
            <div className="bg-green-100 text-green-800 rounded-lg px-4 py-2 text-sm">
              ✓ {msg.content}
            </div>
          </div>
        );

      case 'error':
        return (
          <div key={msg.id} className="flex justify-center mb-4">
            <div className="bg-red-100 text-red-800 rounded-lg px-4 py-2 text-sm">
              ✗ {msg.content}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.map(renderMessage)}

        {/* Streaming message (being typed in real-time) */}
        {isStreaming && currentStreamingMessage && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-200 text-gray-800 rounded-lg px-4 py-2 max-w-md">
              {currentStreamingMessage}
              <span className="animate-pulse">▊</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isSending}
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSending || !inputMessage.trim()}
            className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
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

      {/* Mandate Chain Visualization */}
      {mandateChain && (
        <div className="absolute top-4 right-4 max-w-md">
          <MandateChainViz chain={mandateChain} />
        </div>
      )}
    </div>
  );
}
