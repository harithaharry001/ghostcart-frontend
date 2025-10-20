/**
 * Signature Modal Component
 * Futuristic biometric-style signature authorization for mandates
 */
import React, { useState, useEffect } from 'react';

export default function SignatureModal({ isOpen, mandate, mandateType, flow, constraints, onSign, onCancel }) {
  const [status, setStatus] = useState('idle'); // idle, scanning, verified, error

  if (!isOpen) return null;

  // Determine if this is HNP (Human-Not-Present) flow
  const isHNP = flow === 'hnp' || mandateType === 'intent';

  const handleSign = async () => {
    setStatus('scanning');

    // Simulate biometric scan delay with animation
    await new Promise(resolve => setTimeout(resolve, 2000));

    try {
      await onSign();
      setStatus('verified');
      setTimeout(() => {
        setStatus('idle');
      }, 1000);
    } catch (error) {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 2000);
    }
  };

  return (
    <div className="backdrop-overlay">
      <div className="modal">
        <div className="modal-content max-w-lg">
          {/* Header */}
          <div className="text-center mb-6">
            <h2 className="text-3xl font-bold gradient-text mb-2">
              {isHNP ? 'Pre-Authorization Required' : 'Authorize Purchase'}
            </h2>
            <p className="text-sm text-neutral-600">
              {isHNP 
                ? 'Your signature grants the agent authority to act when conditions are met'
                : 'Your signature authorizes this purchase'
            }
          </p>
          </div>

          {/* HNP Warning */}
          {isHNP && (
            <div className="badge badge-warning mb-6 w-full p-4">
              <div className="flex items-start gap-3 text-left">
                <svg className="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="font-bold mb-1">
                    Autonomous Purchase Authorization
                  </p>
                  <p className="text-sm opacity-90">
                    The agent will purchase automatically when conditions are met{' '}
                    <strong>without asking you again</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Authorization Details */}
          <div className="mb-6">
            {isHNP ? (
              <div className="space-y-3">
                <p className="text-secondary font-semibold flex items-center gap-2 text-sm">
                  <span className="text-primary">⚡</span>
                  Monitoring Authorization
                </p>
                {constraints && (
                  <div className="modern-card p-4 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-neutral-600">Maximum Price:</span>
                      <span className="font-bold text-primary text-xl">
                        ${(constraints.max_price_cents / 100).toFixed(2)}
                      </span>
                    </div>
                    <div className="divider"></div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-neutral-600">Maximum Delivery:</span>
                      <span className="font-bold text-success text-xl">
                        {constraints.max_delivery_days} days
                      </span>
                    </div>
                    {mandate?.expiration && (
                      <>
                        <div className="divider"></div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-neutral-600">Expires:</span>
                          <span className="font-semibold text-secondary">
                            {new Date(mandate.expiration).toLocaleDateString()}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                )}
                <p className="text-xs text-neutral-600 italic">
                  Agent will monitor and purchase when product meets these constraints
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-secondary font-semibold flex items-center gap-2 text-sm">
                  <span className="text-success">✓</span>
                  Immediate Purchase Authorization
                </p>
                <div className="modern-card p-4">
                  <p className="text-sm text-secondary">
                    {mandate?.summary || 'Purchase authorization required'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Biometric Fingerprint Icon with Animation */}
          <div className="flex justify-center mb-6">
            <div className={`relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${
              status === 'scanning' ? 'glow-blue scale-110' :
              status === 'verified' ? 'glow-green scale-110' :
              status === 'error' ? 'bg-error/20 border-2 border-error' :
              'bg-white/5 border-2 border-primary/30'
            }`}>
              {/* Scanning animation overlay */}
              {status === 'scanning' && (
                <div className="absolute inset-0 rounded-full overflow-hidden">
                  <div className="absolute inset-0 shimmer"></div>
                </div>
              )}
              
              {/* Icon */}
              <div className="relative z-10">
                {status === 'verified' ? (
                  <svg className="w-16 h-16 text-success animate-scale-in" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : status === 'error' ? (
                  <svg className="w-16 h-16 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  <svg className={`w-16 h-16 ${status === 'scanning' ? 'text-primary animate-pulse-subtle' : 'text-primary/60'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                  </svg>
                )}
              </div>
            </div>
          </div>

          {/* Status Messages */}
          <div className="text-center mb-6 h-6">
            {status === 'scanning' && (
              <p className="text-primary font-medium animate-pulse-subtle">
                Verifying signature...
              </p>
            )}
            {status === 'verified' && (
              <p className="text-success font-medium">
                ✓ Signature Verified
              </p>
            )}
            {status === 'error' && (
              <p className="text-error font-medium">
                ✗ Verification Failed
              </p>
            )}
          </div>

          {/* Footer Note */}
          <div className="modern-card bg-accent/5 border border-accent/20 p-3 mb-6">
            <p className="text-xs text-neutral-600 text-center">
              Creates a tamper-proof cryptographic record of your approval
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              disabled={status === 'scanning'}
              className="flex-1 btn-outline py-3"
            >
              Cancel
            </button>
            <button
              onClick={handleSign}
              disabled={status !== 'idle'}
              className="flex-1 btn-primary py-3"
            >
              {status === 'idle' ? 'Confirm Signature' : 
               status === 'scanning' ? 'Verifying...' : 
               status === 'verified' ? 'Verified!' : 'Try Again'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
