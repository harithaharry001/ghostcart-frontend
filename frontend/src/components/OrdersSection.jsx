/**
 * Orders Section Component
 *
 * Displays user's transaction history with mandate chain visualization.
 * Supports both HP (Human-Present) and HNP (Human-Not-Present) flows.
 *
 * Features:
 * - List of all transactions (most recent first)
 * - Status badges (authorized/declined)
 * - Expandable mandate chain for each transaction
 * - AP2 compliance transparency
 * - Automatic refresh on payment completion (SSE events)
 */
import { useState, useEffect, useCallback } from 'react';
import MandateChainFlow from './MandateChainFlow';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function OrdersSection({ userId, onPaymentComplete }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedTransaction, setExpandedTransaction] = useState(null);
  const [mandateChain, setMandateChain] = useState(null);
  const [loadingChain, setLoadingChain] = useState(false);

  /**
   * Fetch user transactions (wrapped in useCallback for external use)
   */
  const fetchTransactions = useCallback(async () => {
    if (!userId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/transactions/user/${userId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }

      const data = await response.json();
      // API returns { transactions: [...] }, extract the array
      setTransactions(data.transactions || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching transactions:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  /**
   * Initial fetch on mount
   */
  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  /**
   * Listen for payment completion events to auto-refresh
   */
  useEffect(() => {
    if (onPaymentComplete) {
      // Parent component will call this when payment completes
      // This allows Home.jsx to trigger refresh via SSE events
      return;
    }
  }, [onPaymentComplete]);

  /**
   * Load mandate chain for a transaction
   */
  const loadMandateChain = async (transactionId) => {
    if (expandedTransaction === transactionId) {
      // Collapse if already expanded
      setExpandedTransaction(null);
      setMandateChain(null);
      return;
    }

    try {
      setLoadingChain(true);
      setExpandedTransaction(transactionId);

      const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}/chain`);

      if (!response.ok) {
        throw new Error('Failed to fetch mandate chain');
      }

      const chain = await response.json();
      setMandateChain(chain);
    } catch (err) {
      console.error('Error fetching mandate chain:', err);
      setMandateChain(null);
    } finally {
      setLoadingChain(false);
    }
  };

  /**
   * Format currency
   */
  const formatCurrency = (cents) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  /**
   * Format date
   */
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  /**
   * Refresh transactions manually (reuses fetchTransactions)
   */
  const refreshTransactions = () => {
    fetchTransactions();
  };

  /**
   * Expose refresh function to parent via callback
   */
  useEffect(() => {
    if (onPaymentComplete) {
      onPaymentComplete.current = fetchTransactions;
    }
  }, [onPaymentComplete, fetchTransactions]);

  return (
    <div className="space-y-4">
      {/* Header - Always visible */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-secondary">Order History</h3>
          <button
            onClick={refreshTransactions}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-neutral-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh orders"
          >
            <svg
              className={`w-5 h-5 text-neutral-600 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
        <span className="badge badge-info">{transactions.length} order{transactions.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Refresh Info Banner */}
      <div className="modern-card p-3 bg-primary/5 border-primary/20">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-secondary">
            <strong>After HP purchase or HNP autonomous purchase:</strong> Click the refresh button above to see your new order
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="modern-card p-6">
          <div className="flex items-center justify-center gap-3">
            <div className="spinner w-5 h-5"></div>
            <p className="text-neutral-600">Loading transactions...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="modern-card p-6 border-error/20">
          <div className="flex items-center gap-3 text-error">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Error loading transactions: {error}</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && transactions.length === 0 && (
        <div className="modern-card p-8 text-center">
          <svg className="w-16 h-16 mx-auto text-neutral-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
          </svg>
          <p className="text-neutral-600 font-medium mb-2">No Orders Yet</p>
          <p className="text-neutral-500 text-sm">
            Complete a purchase using HP (immediate) or HNP (monitored) flow to see your order history here.
          </p>
        </div>
      )}

      {/* Transactions List */}
      {!loading && !error && transactions.length > 0 && (
        <div className="max-h-[600px] overflow-y-auto space-y-4 pr-2">
          {transactions.map((txn) => (
        <div key={txn.transaction_id} className="modern-card">
          {/* Transaction Header */}
          <div
            className="px-4 py-3 cursor-pointer hover:bg-neutral-50 transition-colors"
            onClick={() => loadMandateChain(txn.transaction_id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <p className="font-semibold text-secondary">
                    Order #{txn.transaction_id.slice(-8).toUpperCase()}
                  </p>
                </div>
                <div className="flex items-center gap-4 text-sm text-neutral-600">
                  <span className="font-medium text-success">{formatCurrency(txn.amount_cents)}</span>
                  <span>•</span>
                  <span>{formatDate(txn.created_at)}</span>
                  {txn.authorization_code && (
                    <>
                      <span>•</span>
                      <span className="font-mono text-xs">Auth: {txn.authorization_code}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="flex-shrink-0">
                <svg
                  className={`w-5 h-5 text-neutral-400 transition-transform ${expandedTransaction === txn.transaction_id ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* Expanded Mandate Chain */}
          {expandedTransaction === txn.transaction_id && (
            <div className="border-t border-neutral-200 px-4 py-4 bg-neutral-50">
              {loadingChain ? (
                <div className="flex items-center justify-center gap-3 py-8">
                  <div className="spinner w-5 h-5"></div>
                  <p className="text-neutral-600">Loading mandate chain...</p>
                </div>
              ) : mandateChain ? (
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <h4 className="font-semibold text-secondary">AP2 Mandate Chain</h4>
                    <span className="badge badge-info text-xs">
                      {mandateChain?.flow_type === 'human_not_present' ? 'HNP Flow' : 'HP Flow'}
                    </span>
                  </div>
                  <MandateChainFlow chain={mandateChain} />

                  {/* Raw mandate data (collapsible for debugging) */}
                  <details className="mt-4">
                    <summary className="text-sm text-neutral-600 cursor-pointer hover:text-primary">
                      View raw mandate data
                    </summary>
                    <pre className="mt-2 p-3 bg-white rounded-md border border-neutral-200 text-xs overflow-auto max-h-96">
                      {JSON.stringify(mandateChain, null, 2)}
                    </pre>
                  </details>
                </div>
              ) : (
                <div className="text-center py-8 text-neutral-500">
                  Failed to load mandate chain
                </div>
              )}
            </div>
          )}
        </div>
          ))}
        </div>
      )}
    </div>
  );
}
