/**
 * Signature Modal Component
 * Biometric-style signature authorization for mandates
 */
import React, { useState } from 'react';

export default function SignatureModal({ isOpen, mandate, mandateType, flow, constraints, onSign, onCancel }) {
  const [status, setStatus] = useState('idle'); // idle, signing, verified, error

  if (!isOpen) return null;

  // Determine if this is HNP (Human-Not-Present) flow
  const isHNP = flow === 'hnp' || mandateType === 'intent';

  const handleSign = async () => {
    setStatus('signing');

    // Simulate biometric scan delay
    await new Promise(resolve => setTimeout(resolve, 1500));

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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
        <h2 className="text-2xl font-bold mb-4">
          {isHNP ? 'Pre-Authorization Required' : 'Signature Required'}
        </h2>

        {/* HNP Warning */}
        {isHNP && (
          <div className="bg-orange-50 border-2 border-orange-400 rounded-lg p-4 mb-4">
            <div className="flex items-start gap-2">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-bold text-orange-900 mb-1">
                  Autonomous Purchase Authorization
                </p>
                <p className="text-sm text-orange-800">
                  You are authorizing autonomous purchase. The agent will buy
                  automatically when conditions are met <strong>without asking you again</strong>.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Authorization Details */}
        <div className="mb-6">
          {isHNP ? (
            <div className="space-y-2">
              <p className="text-gray-700 font-medium">
                Monitoring Authorization:
              </p>
              {constraints && (
                <div className="bg-gray-50 rounded p-3 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Maximum Price:</span>
                    <span className="font-semibold text-gray-900">
                      ${(constraints.max_price_cents / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Maximum Delivery:</span>
                    <span className="font-semibold text-gray-900">
                      {constraints.max_delivery_days} days
                    </span>
                  </div>
                  {mandate?.expiration && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Expires:</span>
                      <span className="font-semibold text-gray-900">
                        {new Date(mandate.expiration).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              )}
              <p className="text-sm text-gray-600 mt-2">
                Agent will monitor and purchase when product meets these constraints.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-gray-700 font-medium">
                You are authorizing immediate purchase:
              </p>
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-900">
                  {mandate?.summary || 'Purchase authorization required'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Biometric Fingerprint Icon */}
        <div className="flex justify-center mb-6">
          <div className={`w-32 h-32 rounded-full flex items-center justify-center ${
            status === 'signing' ? 'bg-primary-light animate-pulse' :
            status === 'verified' ? 'bg-success-light' :
            status === 'error' ? 'bg-error-light' :
            'bg-gray-100'
          }`}>
            <span className="text-6xl">
              {status === 'verified' ? '✓' : status === 'error' ? '✗' : '🔐'}
            </span>
          </div>
        </div>

        {/* Status Messages */}
        {status === 'signing' && (
          <p className="text-center text-primary font-medium mb-4">Verifying signature...</p>
        )}
        {status === 'verified' && (
          <p className="text-center text-success font-medium mb-4">Signature verified!</p>
        )}
        {status === 'error' && (
          <p className="text-center text-error font-medium mb-4">Signature failed. Please try again.</p>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={status === 'signing'}
            className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSign}
            disabled={status !== 'idle'}
            className="flex-1 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 font-bold"
          >
            {status === 'idle' ? 'Confirm' : status === 'signing' ? 'Signing...' : 'Done'}
          </button>
        </div>
      </div>
    </div>
  );
}
