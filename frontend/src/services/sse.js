/**
 * Server-Sent Events (SSE) Service
 *
 * Manages real-time event streaming from backend for agent transparency.
 * Provides reconnection logic and event handler registration.
 *
 * AP2 Compliance:
 * - Real-time visibility into agent decision-making
 * - Mandate generation transparency
 * - Payment processing status updates
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * SSE connection wrapper with reconnection and event handling
 */
export class SSEConnection {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.eventSource = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.connected = false;
  }

  /**
   * Connect to SSE stream
   */
  connect() {
    if (this.eventSource) {
      console.warn('SSE already connected');
      return;
    }

    const url = `${API_BASE_URL}/stream?session_id=${this.sessionId}`;
    console.log(`Connecting to SSE: ${url}`);

    this.eventSource = new EventSource(url);

    // Connection opened
    this.eventSource.onopen = () => {
      console.log('SSE connection opened');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this._triggerListeners('connection', { status: 'connected' });
    };

    // Connection error
    this.eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      this.connected = false;
      this._triggerListeners('connection', { status: 'error', error });

      // Attempt reconnection with exponential backoff
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        this.disconnect();
        setTimeout(() => this.connect(), delay);
      } else {
        console.error('Max reconnection attempts reached');
        this.disconnect();
      }
    };

    // Generic message handler
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE message:', data);
        this._triggerListeners('message', data);
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
      }
    };

    // Register specific event type handlers
    this._registerEventTypes();
  }

  /**
   * Register handlers for specific SSE event types
   */
  _registerEventTypes() {
    const eventTypes = [
      'connected',
      'chat_message',
      'flow_detected',
      'agent_thinking',
      'product_results',
      'cart_created',
      'mandate_created',
      'signature_requested',
      'signature_complete',
      'payment_processing',
      'payment_authorized',
      'payment_declined',
      'transaction_complete',
      'monitoring_update',
      'error'
    ];

    eventTypes.forEach(eventType => {
      this.eventSource.addEventListener(eventType, (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log(`SSE event [${eventType}]:`, data);
          this._triggerListeners(eventType, data);
        } catch (err) {
          console.error(`Failed to parse SSE event [${eventType}]:`, err);
        }
      });
    });
  }

  /**
   * Disconnect from SSE stream
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.connected = false;
      console.log('SSE connection closed');
      this._triggerListeners('connection', { status: 'disconnected' });
    }
  }

  /**
   * Register event listener
   *
   * @param {string} eventType - Event type to listen for
   * @param {function} callback - Callback function (data) => void
   */
  on(eventType, callback) {
    if (!this.listeners[eventType]) {
      this.listeners[eventType] = [];
    }
    this.listeners[eventType].push(callback);
  }

  /**
   * Unregister event listener
   *
   * @param {string} eventType - Event type
   * @param {function} callback - Callback to remove
   */
  off(eventType, callback) {
    if (!this.listeners[eventType]) return;

    this.listeners[eventType] = this.listeners[eventType].filter(
      cb => cb !== callback
    );
  }

  /**
   * Trigger all listeners for an event type
   */
  _triggerListeners(eventType, data) {
    if (!this.listeners[eventType]) return;

    this.listeners[eventType].forEach(callback => {
      try {
        callback(data);
      } catch (err) {
        console.error(`Error in listener for ${eventType}:`, err);
      }
    });
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.connected;
  }

  /**
   * Get session ID
   */
  getSessionId() {
    return this.sessionId;
  }
}

/**
 * Create new SSE connection
 *
 * @param {string} sessionId - Session identifier
 * @returns {SSEConnection} SSE connection instance
 */
export function createSSEConnection(sessionId) {
  return new SSEConnection(sessionId);
}

/**
 * Generate unique session ID
 */
export function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
