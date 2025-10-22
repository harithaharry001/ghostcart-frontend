/**
 * MonitoringStatusCard Component
 * Futuristic real-time monitoring display for HNP flow
 *
 * AP2 Transparency:
 * - Shows what's being monitored
 * - Displays authorization constraints (max price, max delivery)
 * - Real-time status updates
 * - User can revoke authorization by cancelling
 */
import { useState, useEffect } from 'react';

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
        setTimeRemaining(`${days}d ${hours}h`);
      } else if (hours > 0) {
        setTimeRemaining(`${hours}h ${minutes}m`);
      } else {
        setTimeRemaining(`${minutes}m`);
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
      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(diff / (1000 * 60));

      if (seconds < 10) {
        setLastCheck('just now');
      } else if (seconds < 60) {
        setLastCheck(`${seconds}s ago`);
      } else if (minutes < 60) {
        setLastCheck(`${minutes}m ago`);
      } else {
        const hours = Math.floor(minutes / 60);
        setLastCheck(`${hours}h ago`);
      }
    };

    // Update once when component mounts or job data changes
    updateCountdown();
    updateLastCheck();
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
    <div className="modern-card p-5 animate-slide-up">
      {/* Header with Status Indicator */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="icon-container">
            <svg className="w-5 h-5 text-warning animate-pulse-subtle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-secondary">
              Active Monitoring
            </h3>
            <p className="text-xs text-neutral-600 font-mono">
              {job.job_id.slice(0, 8)}...
            </p>
          </div>
        </div>
        {job.active && (
          <button
            onClick={handleCancel}
            className="btn-ghost p-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Product Query */}
      <div className="mb-4 p-3 bg-primary/5 rounded-xl border border-primary/20">
        <p className="text-xs text-neutral-600 mb-2 uppercase tracking-wide font-medium">Watching for:</p>
        <p className="text-sm font-medium text-secondary">
          {job.product_query}
        </p>
      </div>

      {/* Constraints Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs text-neutral-600">Max Price</p>
          </div>
          <p className="text-2xl font-bold text-primary">
            ${maxPrice}
          </p>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs text-neutral-600">Max Delivery</p>
          </div>
          <p className="text-2xl font-bold text-success">
            {maxDelivery}d
          </p>
        </div>
      </div>

      {/* Status Info */}
      <div className="modern-card p-3 mb-4 space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-neutral-600">Check Interval:</span>
          <span className="text-secondary font-mono text-xs">
            {job.schedule_interval_minutes < 1
              ? `${Math.round(job.schedule_interval_minutes * 60)}s`
              : `${job.schedule_interval_minutes}m`}
          </span>
        </div>

        <div className="divider my-2"></div>

        <div className="flex justify-between items-center text-sm">
          <span className="text-neutral-600">Last Check:</span>
          <span className="text-secondary font-mono text-xs">{lastCheck}</span>
        </div>

        {job.next_run_time && (
          <>
            <div className="divider my-2"></div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-neutral-600">Next Check:</span>
              <span className="text-primary font-mono text-xs">
                {new Date(job.next_run_time).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
            </div>
          </>
        )}

        <div className="divider my-2"></div>

        <div className="flex justify-between items-center text-sm">
          <span className="text-neutral-600">Expires in:</span>
          <span className="text-warning font-mono text-xs">{timeRemaining}</span>
        </div>
      </div>

      {/* Status indicator */}
      <div className="badge badge-info mb-4 w-full justify-start p-3">
        <div className="status-dot active mr-2"></div>
        <div className="text-left">
          <p className="text-xs font-semibold mb-0.5">
            Monitoring Active
          </p>
          <p className="text-xs opacity-80">
            Checking every 10 seconds for price drops. (for demo purpose)
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => onViewChain && onViewChain(job.intent_mandate_id)}
          className="flex-1 btn-outline text-sm py-2"
        >
          View Mandate
        </button>
        <button
          onClick={handleCancel}
          className="btn-ghost text-error text-sm py-2 px-4"
        >
          Cancel
        </button>
      </div>

      {/* Info Footer */}
      <div className="pt-4 border-t border-neutral-200">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-neutral-600">
            <span className="text-secondary font-semibold">Autonomous:</span> Auto-purchase when conditions are met
          </p>
        </div>
      </div>
    </div>
  );
}
