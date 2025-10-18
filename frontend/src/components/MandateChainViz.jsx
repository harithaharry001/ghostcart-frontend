/**
 * Mandate Chain Visualization Component
 * Shows AP2 mandate chain: Intent → Cart → Payment → Transaction
 */
import React, { useState } from 'react';

export default function MandateChainViz({ chain }) {
  const [expandedBox, setExpandedBox] = useState(null);

  if (!chain) return null;

  const { transaction, intent, cart, payment, flow_type } = chain;

  const renderMandateBox = (title, data, color, icon, note, badges = [], references = null) => {
    if (!data) return null;

    const isExpanded = expandedBox === title;
    const mandateId = data.mandate_id || 'N/A';

    return (
      <div className={`border-2 border-${color}-500 rounded-lg p-4 bg-${color}-50`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{icon}</span>
            <div>
              <h4 className="font-bold text-gray-900">{title}</h4>
              {note && (
                <div className={`text-xs text-${color}-700 font-medium mt-1`}>{note}</div>
              )}
            </div>
          </div>
          <button
            onClick={() => setExpandedBox(isExpanded ? null : title)}
            className="text-sm text-gray-600 hover:text-gray-800 underline"
          >
            {isExpanded ? 'Hide' : 'Details'}
          </button>
        </div>

        {/* Badges */}
        {badges.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {badges.map((badge, idx) => (
              <span
                key={idx}
                className={`px-2 py-1 rounded text-xs font-medium ${badge.className}`}
              >
                {badge.text}
              </span>
            ))}
          </div>
        )}

        {/* References */}
        {references && (
          <div className="text-xs text-gray-600 bg-white rounded p-2 mb-2">
            <span className="font-medium">References:</span> {references}
          </div>
        )}

        <div className="text-xs text-gray-500 font-mono">
          ID: {mandateId.substring(0, 24)}...
        </div>

        {isExpanded && (
          <div className="mt-3">
            <pre className="text-xs bg-white p-3 rounded overflow-auto max-h-48 border border-gray-300">
              {JSON.stringify(data, null, 2)}
            </pre>
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(JSON.stringify(data, null, 2))}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                Copy This Mandate
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-xl font-bold mb-4">Mandate Chain</h3>

      <div className="flex items-center justify-center mb-4">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          flow_type === 'human_present' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
        }`}>
          {flow_type === 'human_present' ? 'Human-Present Flow' : 'Human-Not-Present Flow'}
        </span>
      </div>

      <div className="space-y-4">
        {/* Intent */}
        {intent && renderMandateBox(
          'Intent Mandate',
          intent,
          intent?.signature ? 'green' : 'gray',
          intent?.signature ? '✍️' : '💭',
          intent?.signature ? 'User Signed - Pre-Authorization' : 'Context Only (HP)',
          intent?.signature ? [
            { text: '🔐 Pre-Authorization', className: 'bg-green-100 text-green-800' },
            { text: `Max: $${(intent.constraints?.max_price_cents / 100 || 0).toFixed(2)}`, className: 'bg-blue-100 text-blue-800' }
          ] : [],
          null
        )}

        {/* Arrow */}
        {intent && cart && (
          <div className="flex justify-center">
            <span className="text-2xl text-gray-400">↓</span>
          </div>
        )}

        {/* Cart */}
        {cart && renderMandateBox(
          'Cart Mandate',
          cart,
          cart?.signature?.signer_identity?.includes('agent') ? 'blue' : 'green',
          cart?.signature?.signer_identity?.includes('agent') ? '🤖' : '🛒',
          cart?.signature?.signer_identity?.includes('agent') ? 'Agent Signed - Autonomous Action' : 'User Signed - Authorization',
          cart?.signature?.signer_identity?.includes('agent') ? [
            { text: '🤖 Autonomous Purchase', className: 'bg-blue-100 text-blue-800' }
          ] : [
            { text: '✅ User Authorized', className: 'bg-green-100 text-green-800' }
          ],
          cart?.references ? `Intent ID: ${cart.references.substring(0, 16)}...` : null
        )}

        {/* Arrow */}
        {cart && payment && (
          <div className="flex justify-center">
            <span className="text-2xl text-gray-400">↓</span>
          </div>
        )}

        {/* Payment */}
        {payment && renderMandateBox(
          'Payment Mandate',
          payment,
          'purple',
          '💳',
          'Payment Agent Signed',
          [
            { text: '🔒 Payment Agent', className: 'bg-purple-100 text-purple-800' },
            ...(payment.human_not_present ? [
              { text: '🚫👤 Human Not Present', className: 'bg-orange-100 text-orange-800' }
            ] : [])
          ],
          payment?.references ? `Cart ID: ${payment.references.substring(0, 16)}...` : null
        )}

        {/* Arrow */}
        <div className="flex justify-center">
          <span className="text-2xl text-gray-400">↓</span>
        </div>

        {/* Transaction */}
        <div className={`border-2 border-${transaction.status === 'authorized' ? 'success' : 'error'} rounded-lg p-4`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{transaction.status === 'authorized' ? '✅' : '❌'}</span>
            <h4 className="font-bold">Transaction Result</h4>
          </div>
          <div className="text-sm space-y-1">
            <div><span className="font-medium">Status:</span> {transaction.status}</div>
            <div><span className="font-medium">Amount:</span> ${(transaction.amount_cents / 100).toFixed(2)}</div>
            {transaction.authorization_code && (
              <div className="font-mono text-xs text-gray-600">
                Auth: {transaction.authorization_code}
              </div>
            )}
            {transaction.decline_reason && (
              <div className="text-error text-sm">
                Reason: {transaction.decline_reason}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-2">
        <button className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium">
          Copy JSON
        </button>
        <button className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium">
          Download Chain
        </button>
      </div>
    </div>
  );
}
