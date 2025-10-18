/**
 * NotificationBanner Component
 *
 * Large, prominent notification for autonomous purchase completion.
 * Displays product details, authorization info, and mandate chain access.
 *
 * AP2 Transparency:
 * - Shows what was purchased autonomously
 * - Displays original authorization constraints
 * - Links to complete mandate chain for audit
 * - User can dismiss after reviewing
 */
import { useState } from 'react';

export default function NotificationBanner({
  notification,
  onDismiss,
  onViewDetails,
  onViewChain
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!notification) return null;

  const {
    type, // 'success', 'error', 'info'
    title,
    message,
    product_name,
    amount_cents,
    authorization_date,
    constraints,
    transaction_id,
    intent_id,
    cart_id,
    authorization_code
  } = notification;

  // Determine banner styling based on type
  const getStyles = () => {
    switch (type) {
      case 'success':
        return {
          bg: 'bg-green-50',
          border: 'border-green-400',
          icon: '✅',
          iconBg: 'bg-green-500',
          text: 'text-green-900',
          button: 'bg-green-600 hover:bg-green-700'
        };
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-400',
          icon: '❌',
          iconBg: 'bg-red-500',
          text: 'text-red-900',
          button: 'bg-red-600 hover:bg-red-700'
        };
      case 'info':
      default:
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-400',
          icon: 'ℹ️',
          iconBg: 'bg-blue-500',
          text: 'text-blue-900',
          button: 'bg-blue-600 hover:bg-blue-700'
        };
    }
  };

  const styles = getStyles();

  const formatCurrency = (cents) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div
      className={`${styles.bg} border-2 ${styles.border} rounded-lg shadow-lg mb-4 overflow-hidden transition-all duration-300`}
    >
      {/* Header */}
      <div className="p-4 flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1">
          {/* Icon */}
          <div className={`${styles.iconBg} rounded-full w-10 h-10 flex items-center justify-center text-white text-xl flex-shrink-0`}>
            {styles.icon}
          </div>

          {/* Content */}
          <div className="flex-1">
            <h3 className={`text-xl font-bold ${styles.text} mb-1`}>
              {title || 'Autonomous Purchase Complete!'}
            </h3>
            <p className={`text-sm ${styles.text} opacity-80`}>
              {message || 'Your monitoring conditions were met and the purchase was completed automatically.'}
            </p>
          </div>
        </div>

        {/* Dismiss Button */}
        <button
          onClick={onDismiss}
          className={`${styles.text} opacity-50 hover:opacity-100 ml-2`}
          aria-label="Dismiss notification"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Product Info */}
          {product_name && (
            <div className="bg-white rounded-lg p-3">
              <p className="text-sm text-gray-600 mb-1">Product Purchased</p>
              <p className="text-lg font-semibold text-gray-900">
                {product_name}
              </p>
              {amount_cents && (
                <p className="text-2xl font-bold text-green-600 mt-1">
                  {formatCurrency(amount_cents)}
                </p>
              )}
            </div>
          )}

          {/* Authorization Details */}
          <div className="grid grid-cols-2 gap-3">
            {authorization_date && (
              <div className="bg-white rounded p-2">
                <p className="text-xs text-gray-600 mb-1">Authorized On</p>
                <p className="text-sm font-medium text-gray-900">
                  {formatDate(authorization_date)}
                </p>
              </div>
            )}

            {authorization_code && (
              <div className="bg-white rounded p-2">
                <p className="text-xs text-gray-600 mb-1">Auth Code</p>
                <p className="text-sm font-medium font-mono text-gray-900">
                  {authorization_code}
                </p>
              </div>
            )}
          </div>

          {/* Original Constraints */}
          {constraints && (
            <div className="bg-white rounded-lg p-3">
              <p className="text-sm text-gray-600 mb-2">
                Your Original Constraints:
              </p>
              <div className="flex gap-4 text-sm">
                {constraints.max_price_cents && (
                  <div>
                    <span className="text-gray-600">Max Price: </span>
                    <span className="font-semibold text-gray-900">
                      {formatCurrency(constraints.max_price_cents)}
                    </span>
                  </div>
                )}
                {constraints.max_delivery_days && (
                  <div>
                    <span className="text-gray-600">Max Delivery: </span>
                    <span className="font-semibold text-gray-900">
                      {constraints.max_delivery_days} days
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Transaction ID */}
          {transaction_id && (
            <div className="bg-white rounded p-2">
              <p className="text-xs text-gray-600 mb-1">Transaction ID</p>
              <p className="text-sm font-mono text-gray-900">
                {transaction_id}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            {transaction_id && onViewDetails && (
              <button
                onClick={() => onViewDetails(transaction_id)}
                className={`flex-1 px-4 py-2 text-white rounded font-medium transition-colors ${styles.button}`}
              >
                View Details
              </button>
            )}

            {(intent_id || cart_id || transaction_id) && onViewChain && (
              <button
                onClick={() => onViewChain(transaction_id)}
                className={`flex-1 px-4 py-2 text-white rounded font-medium transition-colors ${styles.button}`}
              >
                View Mandate Chain
              </button>
            )}
          </div>

          {/* AP2 Transparency Note */}
          <div className="bg-white bg-opacity-50 rounded p-2 mt-3">
            <p className="text-xs text-gray-700">
              🔗 <span className="font-semibold">AP2 Transparency:</span> Complete
              mandate chain available for audit. Intent (pre-authorization) →
              Cart (agent-signed) → Payment (HNP flag) → Transaction.
            </p>
          </div>
        </div>
      )}

      {/* Toggle Expand/Collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full py-2 text-center text-sm font-medium ${styles.text} hover:bg-black hover:bg-opacity-5 transition-colors`}
      >
        {isExpanded ? 'Show Less ▲' : 'Show More ▼'}
      </button>
    </div>
  );
}
