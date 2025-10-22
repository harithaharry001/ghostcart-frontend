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
import ReactMarkdown from 'react-markdown';
import { useSession } from '../context/SessionContext';
import SignatureModal from './SignatureModal';
import MandateChainViz from './MandateChainViz';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function ChatInterface({ onPaymentComplete, onAutonomousPurchaseComplete }) {
  const { sessionId, setSessionId, userId, flowType, setFlowType } = useSession();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const messagesEndRef = useRef(null);
  const welcomeShown = useRef(null);
  const eventSourceRef = useRef(null);
  const shownToolNotifications = useRef(new Set());
  const messageIdCounter = useRef(0);

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

  // Monitoring Status State (for real-time status card updates)
  const [monitoringStatus, setMonitoringStatus] = useState(null);

  // Track if payment was initiated in current conversation (for HP flow refresh)
  const paymentInitiatedRef = useRef(false);

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
    messageIdCounter.current += 1;
    // Use counter + timestamp to ensure absolute uniqueness even across remounts
    const uniqueId = `${Date.now()}-${messageIdCounter.current}`;
    setMessages(prev => [...prev, { id: uniqueId, ...message }]);
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

    // Reset tool notifications tracker for new message
    shownToolNotifications.current = new Set();

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

        // Show tool execution message (only once per tool per message)
        if (!shownToolNotifications.current.has(data.tool_name)) {
          shownToolNotifications.current.add(data.tool_name);
          
          if (data.tool_name === 'search_products') {
            addMessage({
              type: 'system',
              content: '🔍 Searching products...',
              timestamp: new Date()
            });
          } else if (data.tool_name === 'shopping_assistant' || data.tool_name === 'monitoring_assistant') {
            addMessage({
              type: 'system',
              content: '🔄 Routing to specialized agent...',
              timestamp: new Date()
            });
          }
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

        // Extract total breakdown from total object
        const totalObj = data.total || {};
        const subtotalCents = totalObj.subtotal_cents || 0;
        const taxCents = totalObj.tax_cents || 0;
        const shippingCents = totalObj.shipping_cents || 0;
        const grandTotalCents = totalObj.grand_total_cents || 0;

        addMessage({
          type: 'system',
          content: `✓ Cart created: ${data.items && data.items.length} item(s) | Subtotal: $${(subtotalCents / 100).toFixed(2)} + Tax: $${(taxCents / 100).toFixed(2)} + Shipping: $${(shippingCents / 100).toFixed(2)} = Total: $${(grandTotalCents / 100).toFixed(2)}`,
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
          // Mark that payment is being initiated (HP flow)
          paymentInitiatedRef.current = true;
        }

        setMandateConstraints(data.constraints || null);
        setShowSignatureModal(true);

        addMessage({
          type: 'system',
          content: '🔐 Signature required - please review and approve',
          timestamp: new Date()
        });
      });

      // Handle monitoring check started (FR-043)
      eventSource.addEventListener('monitoring_check_started', (e) => {
        const data = JSON.parse(e.data);
        console.log('Monitoring check started:', data);

        // Update monitoring status with "checking" indicator
        setMonitoringStatus(prev => ({
          ...prev,
          checking: true,
          last_check_time: data.timestamp
        }));

        addMessage({
          type: 'system',
          content: `🔍 ${data.message}`,
          timestamp: new Date()
        });
      });

      // Handle monitoring check complete (FR-018)
      eventSource.addEventListener('monitoring_check_complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Monitoring check complete:', data);

        // Update monitoring status with check results
        setMonitoringStatus({
          checking: false,
          current_price_cents: data.current_price_cents,
          current_delivery_days: data.current_delivery_days,
          current_stock_status: data.current_stock_status,
          target_price_cents: data.target_price_cents,
          target_delivery_days: data.target_delivery_days,
          reason: data.reason,
          last_check_at: data.last_check_at
        });

        if (data.status === 'conditions_not_met') {
          addMessage({
            type: 'monitoring_status',
            content: data.message,
            data: data,  // Pass full data for status card
            timestamp: new Date()
          });
        }
      });

      // Handle monitoring expired (FR-049)
      eventSource.addEventListener('monitoring_expired', (e) => {
        const data = JSON.parse(e.data);
        console.log('Monitoring expired:', data);

        addMessage({
          type: 'warning',
          content: data.message,
          data: data,  // Include action_available for "Set Up New Monitoring" button
          timestamp: new Date()
        });
      });

      // Handle autonomous purchase starting
      eventSource.addEventListener('autonomous_purchase_starting', (e) => {
        const data = JSON.parse(e.data);
        console.log('Autonomous purchase starting:', data);

        addMessage({
          type: 'success',
          content: `🎉 ${data.message} Product: ${data.product.name} at $${(data.product.price_cents / 100).toFixed(2)}`,
          timestamp: new Date()
        });
      });

      // Handle autonomous cart created
      eventSource.addEventListener('autonomous_cart_created', (e) => {
        const data = JSON.parse(e.data);
        console.log('Autonomous cart created:', data);

        addMessage({
          type: 'system',
          content: `✓ Cart created autonomously (agent-signed) - Total: $${(data.total_cents / 100).toFixed(2)}`,
          timestamp: new Date()
        });
      });

      // Handle autonomous purchase complete
      eventSource.addEventListener('autonomous_purchase_complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Autonomous purchase complete:', data);

        addMessage({
          type: 'success',
          content: `✅ Autonomous Purchase Complete!\n\n${data.product_name} purchased for $${(data.amount_cents / 100).toFixed(2)}\nTransaction ID: ${data.transaction_id}\nAuthorization: ${data.authorization_code}`,
          data: data,  // Pass for "View Chain" button
          timestamp: new Date()
        });

        // Trigger order refresh AND monitoring jobs refresh for HNP payment completion
        if (onAutonomousPurchaseComplete) {
          console.log('Autonomous purchase complete - triggering orders and monitoring refresh');
          onAutonomousPurchaseComplete();
        }
      });

      // Handle autonomous purchase failed
      eventSource.addEventListener('autonomous_purchase_failed', (e) => {
        const data = JSON.parse(e.data);
        console.log('Autonomous purchase failed:', data);

        addMessage({
          type: 'error',
          content: `❌ Autonomous purchase failed: ${data.error || data.message}`,
          timestamp: new Date()
        });
      });

      // Handle HP purchase complete
      eventSource.addEventListener('hp_purchase_complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('HP purchase complete:', data);

        addMessage({
          type: 'success',
          content: `✅ Purchase Complete!\n\n${data.product_name} purchased for $${(data.amount_cents / 100).toFixed(2)}\nTransaction ID: ${data.transaction_id}\nAuthorization: ${data.authorization_code}`,
          data: data,  // Pass for "View Chain" button
          timestamp: new Date()
        });

        // Trigger order refresh for HP payment completion
        if (onPaymentComplete) {
          console.log('HP purchase complete - triggering order refresh via SSE event');
          onPaymentComplete();
        }

        // Reset payment initiated flag since we got explicit completion event
        paymentInitiatedRef.current = false;
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

        // Fallback: Trigger order refresh if HP payment was initiated but no SSE event received
        // (This shouldn't happen now that we emit hp_purchase_complete event, but kept as safety net)
        if (paymentInitiatedRef.current && onPaymentComplete) {
          console.log('HP payment completed (fallback) - triggering order refresh');
          onPaymentComplete();
          paymentInitiatedRef.current = false; // Reset for next conversation
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

        // Reset payment flag on error
        paymentInitiatedRef.current = false;

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

        // Reset payment flag on connection error
        paymentInitiatedRef.current = false;

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
      // Reset payment flag on error
      paymentInitiatedRef.current = false;
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
          <div key={msg.id} className="flex justify-end mb-4 animate-slide-up">
            <div className="message-bubble user">
              {msg.content}
            </div>
          </div>
        );

      case 'agent':
        return (
          <div key={msg.id} className="flex justify-start mb-4 animate-slide-up">
            <div className="message-bubble agent">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="flex-1 prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-2 my-3" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-2 my-3" {...props} />,
                      li: ({node, ...props}) => <li className="ml-2" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-secondary" {...props} />,
                      em: ({node, ...props}) => <em className="italic" {...props} />,
                      code: ({node, inline, ...props}) => 
                        inline ? 
                          <code className="bg-neutral-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props} /> :
                          <code className="block bg-neutral-100 p-3 rounded-lg text-sm font-mono my-2" {...props} />
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        );

      case 'system':
        return (
          <div key={msg.id} className="flex justify-center mb-4 animate-fade-in">
            <div className="badge badge-warning">
              {msg.content}
            </div>
          </div>
        );

      case 'products':
        return (
          <div key={msg.id} className="flex justify-start mb-4 animate-slide-up">
            <div className="modern-card px-4 py-3 max-w-2xl">
              <div className="font-semibold mb-3 text-primary flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                {msg.content}
              </div>
              <div className="space-y-2">
                {msg.products && msg.products.map((product, idx) => (
                  <div key={idx} className="product-card">
                    <div className="font-medium text-secondary mb-2">{product.name}</div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-success font-semibold text-lg">
                        ${(product.price_cents / 100).toFixed(2)}
                      </span>
                      {product.stock_status === 'in_stock' ? (
                        <span className="badge badge-success">In Stock</span>
                      ) : (
                        <span className="badge badge-error">Out of Stock</span>
                      )}
                      {product.delivery_estimate_days && (
                        <span className="text-neutral-600 text-xs">Ships in {product.delivery_estimate_days}d</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 'success':
        return (
          <div key={msg.id} className="flex justify-center mb-4 animate-fade-in">
            <div className="badge badge-success">
              ✓ {msg.content}
            </div>
          </div>
        );

      case 'error':
        return (
          <div key={msg.id} className="flex justify-center mb-4 animate-fade-in">
            <div className="badge badge-error">
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
      <div className="flex-1 scrollable-container p-4 space-y-2">
        {messages.map(renderMessage)}

        {/* Streaming message (being typed in real-time) */}
        {isStreaming && currentStreamingMessage && (
          <div className="flex justify-start mb-4 animate-slide-up">
            <div className="message-bubble agent">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-primary animate-pulse-subtle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="flex-1 prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-2 my-3" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-2 my-3" {...props} />,
                      li: ({node, ...props}) => <li className="ml-2" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-secondary" {...props} />,
                      em: ({node, ...props}) => <em className="italic" {...props} />,
                      code: ({node, inline, ...props}) => 
                        inline ? 
                          <code className="bg-neutral-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props} /> :
                          <code className="block bg-neutral-100 p-3 rounded-lg text-sm font-mono my-2" {...props} />
                    }}
                  >
                    {currentStreamingMessage}
                  </ReactMarkdown>
                  <span className="inline-block w-1.5 h-4 bg-primary ml-1 animate-pulse"></span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-neutral-200 p-4 flex-shrink-0">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me to find products or set up monitoring..."
            disabled={isSending}
            className="input-modern disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSending || !inputMessage.trim()}
            className="btn-primary"
          >
            {isSending ? (
              <span className="flex items-center gap-2">
                <div className="spinner w-5 h-5"></div>
                Sending
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Send
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </span>
            )}
          </button>
        </div>
        <div className="mt-3 space-y-2">
          <p className="text-xs text-neutral-600 text-center font-semibold">
            Try these sample queries:
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setInputMessage("Find AirPods under $200")}
              disabled={isSending || isStreaming}
              className="text-xs px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary/10"
            >
              🎧 HP: AirPods under $200
            </button>
            <button
              onClick={() => setInputMessage("Find coffee maker under $70")}
              disabled={isSending || isStreaming}
              className="text-xs px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary/10"
            >
              ☕ HP: Coffee maker
            </button>
            <button
              onClick={() => setInputMessage("Monitor for Sony headphones under $350")}
              disabled={isSending || isStreaming}
              className="text-xs px-3 py-2 bg-accent/10 hover:bg-accent/20 text-accent rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-accent/10"
            >
              🎵 HNP: Sony headphones
            </button>
            <button
              onClick={() => setInputMessage("Monitor for Dyson vacuum under $550")}
              disabled={isSending || isStreaming}
              className="text-xs px-3 py-2 bg-accent/10 hover:bg-accent/20 text-accent rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-accent/10"
            >
              🧹 HNP: Dyson vacuum
            </button>
          </div>
          <p className="text-xs text-neutral-500 text-center italic">
            HP = Immediate purchase • HNP = Autonomous monitoring
          </p>
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
