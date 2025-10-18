/**
 * MonitoringStatusCard Component
 *
 * Displays real-time status of active HNP monitoring jobs.
 * Shows product query, constraints, last check time, and allows cancellation.
 *
 * AP2 Transparency:
 * - Shows what's being monitored
 * - Displays authorization constraints (max price, max delivery)
 * - Real-time status updates
 * - User can revoke authorization by cancelling
 */
import { useState, useEffect } from 'react';
import { useSession } from '../context/SessionContext';

export default function MonitoringStatusCard({ job, onCancel, onViewChain }) {
  const [timeRemaining, setTimeRemaining] = useState('');
  const [lastCheck, setLastCheck] = useState('');

  useEffect(() => {
    // Update time remaining countdown
    const updateCountdown = () => {
      if (!job.expires_at) return;

      const now = new Date();
      const expiresAt = new Date(job.expires_at);
      const diff = expiresAt - now;

      if (diff <= 0) {
        setTimeRemaining('Expired');
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 0) {
        setTimeRemaining(`${days}d ${hours}h remaining`);
      } else if (hours > 0) {
        setTimeRemaining(`${hours}h ${minutes}m remaining`);
      } else {
        setTimeRemaining(`${minutes}m remaining`);
      }
    };

    // Update last check time
    const updateLastCheck = () => {
      if (!job.last_check_at) {
        setLastCheck('Not checked yet');
        return;
      }

      const now = new Date();
      const lastCheckTime = new Date(job.last_check_at);
      const diff = now - lastCheckTime;
      const minutes = Math.floor(diff / (1000 * 60));

      if (minutes < 1) {
        setLastCheck('Just now');
      } else if (minutes < 60) {
        setLastCheck(`${minutes}m ago`);
      } else {
        const hours = Math.floor(minutes / 60);
        setLastCheck(`${hours}h ago`);
      }
    };

    updateCountdown();
    updateLastCheck();

    const interval = setInterval(() => {
      updateCountdown();
      updateLastCheck();
    }, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [job.expires_at, job.last_check_at]);

  const handleCancel = async () => {
    if (window.confirm('Cancel monitoring? You can always set it up again later.')) {
      await onCancel(job.job_id);
    }
  };

  const maxPrice = job.constraints?.max_price_cents
    ? (job.constraints.max_price_cents / 100).toFixed(2)
    : 'N/A';

  const maxDelivery = job.constraints?.max_delivery_days || 'N/A';

  return (
    <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-4 shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
          <h3 className="text-lg font-semibold text-blue-900">
            Monitoring Active
          </h3>
        </div>
        {job.active && (
          <button
            onClick={handleCancel}
            className="text-sm text-blue-700 hover:text-blue-900 underline"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Product Query */}
      <div className="mb-3">
        <p className="text-sm text-gray-600 mb-1">Watching for:</p>
        <p className="text-base font-medium text-gray-900">
          {job.product_query}
        </p>
      </div>

      {/* Constraints */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-white rounded p-2">
          <p className="text-xs text-gray-600 mb-1">Max Price</p>
          <p className="text-base font-semibold text-green-700">
            ${maxPrice}
          </p>
        </div>
        <div className="bg-white rounded p-2">
          <p className="text-xs text-gray-600 mb-1">Max Delivery</p>
          <p className="text-base font-semibold text-green-700">
            {maxDelivery} days
          </p>
        </div>
      </div>

      {/* Status Info */}
      <div className="space-y-2 mb-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Check Interval:</span>
          <span className="text-gray-900 font-medium">
            {job.schedule_interval_minutes < 1
              ? `${Math.round(job.schedule_interval_minutes * 60)}s`
              : `${job.schedule_interval_minutes}m`}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Last Check:</span>
          <span className="text-gray-900 font-medium">{lastCheck}</span>
        </div>

        {job.next_run_time && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Next Check:</span>
            <span className="text-gray-900 font-medium">
              {new Date(job.next_run_time).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </span>
          </div>
        )}

        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Expires:</span>
          <span className="text-gray-900 font-medium">{timeRemaining}</span>
        </div>
      </div>

      {/* Current Status Reason */}
      <div className="bg-yellow-50 border border-yellow-200 rounded p-2 mb-3">
        <p className="text-xs text-yellow-800">
          <span className="font-semibold">Status:</span> Conditions not met - checking periodically
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewChain && onViewChain(job.intent_mandate_id)}
          className="flex-1 px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          View Intent Mandate
        </button>
      </div>

      {/* Info Footer */}
      <div className="mt-3 pt-3 border-t border-blue-200">
        <p className="text-xs text-gray-600">
          🤖 I'll purchase automatically when conditions are met.
          You'll be notified immediately.
        </p>
      </div>
    </div>
  );
}
