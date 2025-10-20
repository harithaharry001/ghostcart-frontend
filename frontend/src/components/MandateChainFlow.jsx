/**
 * MandateChainFlow Component
 * Interactive visual representation of the AP2 mandate chain
 * Shows the flow: Intent → Cart → Payment → Transaction
 */
import React, { useState } from 'react';

export default function MandateChainFlow({ mode = 'hp', chain = null }) {
  const [hoveredStep, setHoveredStep] = useState(null);

  // Determine mode from chain data if provided
  const flowType = chain?.flow_type || mode;
  // Handle both 'hnp' and 'human_not_present' values
  const currentMode = (flowType === 'human_not_present' || flowType === 'hnp') ? 'hnp' : 'hp';

  // Define the mandate chain steps
  const steps = [
    {
      id: 'intent',
      name: 'Intent Mandate',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
      hp: {
        color: 'gray',
        status: 'Audit Context',
        signed: 'Not Signed',
        description: 'Captures user\'s search query for audit trail - signature NOT required per AP2 human-present specification',
        tooltip: 'Per AP2 Protocol: Intent Mandate is created to record the user\'s original request for audit trail and dispute resolution. In human-present flow, user signature is NOT required on Intent because the Cart Mandate signature serves as the authorization mechanism. Intent provides context only.'
      },
      hnp: {
        color: 'success',
        status: 'Pre-Authorization',
        signed: 'User Signed ✓',
        description: 'You granted the agent authority to act when conditions met per AP2 human-not-present flow',
        tooltip: 'Intent Mandate with user signature serves as pre-authorization for future autonomous action. Contains constraints (maximum price, maximum delivery time, expiration timestamp) that the agent must respect when executing the purchase.'
      }
    },
    {
      id: 'cart',
      name: 'Cart Mandate',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
      hp: {
        color: 'success',
        status: 'User Authorization',
        signed: 'User Signed ✓',
        description: 'User signature on exact items and prices IS the authorization per AP2 human-present specification',
        tooltip: 'Per AP2 Protocol: Cart Mandate with user signature is THE authorization mechanism in human-present flow. Contains exact SKUs, quantities, prices, delivery details, and totals. User signature on Cart authorizes the payment - this is what makes the purchase valid, not the Intent signature.'
      },
      hnp: {
        color: 'primary',
        status: 'Autonomous Action',
        signed: 'Agent Signed 🤖',
        description: 'Agent acted on your behalf based on Intent authority per AP2 specification',
        tooltip: 'Agent acted on your behalf based on Intent authority per AP2 specification. Cart Mandate created by agent (NOT user signature) when monitoring conditions satisfied. References Intent Mandate ID showing required mandate chain link.'
      }
    },
    {
      id: 'payment',
      name: 'Payment Mandate',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
      hp: {
        color: 'secondary',
        status: 'Payment Processing',
        signed: 'Payment Agent',
        description: 'Payment Agent processes authorization referencing Cart Mandate - uses tokenized credentials only',
        tooltip: 'Per AP2 Protocol: Payment Mandate created by Payment Agent references Cart Mandate. Contains tokenized payment credentials only - raw PCI data never exposed to shopping agents due to AP2 role separation. Sent to payment networks with AI agent presence signals for appropriate risk assessment.'
      },
      hnp: {
        color: 'secondary',
        status: 'Payment Processing',
        signed: 'Payment Agent',
        description: 'Payment Agent Signed with Human Not Present Flag Set',
        tooltip: 'Payment Mandate created with human-not-present flag set per AP2 specification, signaling to payment network this is an autonomous transaction. Enables appropriate risk assessment for agent-driven commerce.'
      }
    },
  ];

  const modeLabel = currentMode === 'hnp' ? 'Human-Not-Present' : 'Human-Present';

  // Extract mandate details from chain if provided
  const getMandateDetails = (stepId) => {
    if (!chain) return null;

    switch (stepId) {
      case 'intent':
        // For HP flow, intent might exist but not be signed (context-only)
        if (chain.intent) {
          return {
            id: chain.intent.mandate_id,
            signer: chain.intent.signature?.signer_identity || 'Context Only',
            timestamp: chain.intent.signature?.timestamp || chain.intent.created_at,
            data: chain.intent
          };
        }
        return null;
      case 'cart':
        return chain.cart ? {
          id: chain.cart.mandate_id,
          signer: chain.cart.signature?.signer_identity || 'Unsigned',
          timestamp: chain.cart.signature?.timestamp,
          data: chain.cart
        } : null;
      case 'payment':
        return chain.payment ? {
          id: chain.payment.mandate_id,
          signer: chain.payment.signature?.signer_identity || 'Payment Agent',
          timestamp: chain.payment.signature?.timestamp || chain.payment.processed_at,
          data: chain.payment
        } : null;
      case 'transaction':
        return chain.transaction ? {
          id: chain.transaction.transaction_id,
          status: chain.transaction.status,
          authCode: chain.transaction.authorization_code,
          timestamp: chain.transaction.created_at,
          data: chain.transaction
        } : null;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {/* If chain data available, show detailed mandate list */}
      {chain ? (
        <div className="space-y-3">
          {steps.map((step, index) => {
            const details = getMandateDetails(step.id);
            const config = step[currentMode];

            return (
              <div key={step.id} className="modern-card p-4 border-l-4" style={{
                borderLeftColor:
                  step.id === 'cart' ? '#10b981' :
                  step.id === 'payment' ? '#6366f1' :
                  step.id === 'transaction' ? '#10b981' :
                  '#9ca3af'
              }}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Icon */}
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      step.id === 'cart' ? 'bg-success/20 text-success' :
                      step.id === 'payment' ? 'bg-secondary/20 text-secondary' :
                      step.id === 'transaction' ? 'bg-success/20 text-success' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {step.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-secondary">{step.name}</h4>
                        <span className="text-xs text-neutral-500">Step {index + 1}</span>
                      </div>

                      {/* Show details if available, otherwise show generic info */}
                      {details && details.signer ? (
                        <>
                          {/* Signer */}
                          <div className="text-sm text-neutral-700 mb-2">
                            <span className="text-neutral-600">Signed by:</span>{' '}
                            <span className="font-medium">{details.signer}</span>
                          </div>

                          {/* Mandate ID */}
                          {details.id && (
                            <div className="text-xs font-mono bg-neutral-100 text-neutral-700 px-2 py-1 rounded inline-block mb-2">
                              {details.id}
                            </div>
                          )}

                          {/* Timestamp */}
                          {details.timestamp && (
                            <div className="text-xs text-neutral-500">
                              {new Date(details.timestamp).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true
                              })}
                            </div>
                          )}

                          {/* Additional info for transaction */}
                          {step.id === 'transaction' && details.authCode && (
                            <div className="mt-2 pt-2 border-t border-neutral-200">
                              <div className="text-xs text-neutral-600">
                                Auth Code: <span className="font-mono text-success">{details.authCode}</span>
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-sm text-neutral-500 italic">
                          {config ? config.description : 'No data available'}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status badge */}
                  {step.id === 'transaction' && (
                    <div className="badge badge-success">Completed</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        // Fallback to educational flow if no chain data
        <div className="modern-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-display font-semibold flex items-center gap-2 text-secondary">
              <span className="text-primary">⚡</span>
              Mandate Chain Flow
            </h3>
            <div className="badge badge-info">
              <div className={`w-2 h-2 rounded-full ${currentMode === 'hnp' ? 'bg-warning' : 'bg-success'} animate-pulse`}></div>
              <span className="text-xs">{modeLabel} Mode</span>
            </div>
          </div>

      {/* Flow Visualization */}
      <div className="relative">
        {/* Steps */}
        <div className="grid grid-cols-3 gap-4">
          {steps.map((step, index) => {
            const config = step[currentMode];
            const isHovered = hoveredStep === step.id;
            
            return (
              <div key={step.id} className="relative">
                {/* Connecting Arrow */}
                {index < steps.length - 1 && (
                  <div className="absolute top-1/2 -right-2 transform translate-x-1/2 -translate-y-1/2 z-10">
                    <svg className="w-4 h-4 text-primary animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}

                {/* Step Card */}
                <div
                  className={`modern-card p-4 rounded-xl transition-all duration-300 cursor-pointer ${
                    isHovered ? 'scale-105 shadow-large' : ''
                  } ${
                    config.color === 'success' ? 'border-success/50' :
                    config.color === 'primary' ? 'border-primary/50' :
                    config.color === 'secondary' ? 'border-secondary/50' :
                    'border-neutral-400/50'
                  } border-2`}
                  onMouseEnter={() => setHoveredStep(step.id)}
                  onMouseLeave={() => setHoveredStep(null)}
                >
                  {/* Icon */}
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-3 ${
                    config.color === 'success' ? 'bg-success/20 text-success' :
                    config.color === 'primary' ? 'bg-primary/20 text-primary' :
                    config.color === 'secondary' ? 'bg-secondary/20 text-secondary' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {step.icon}
                  </div>

                  {/* Step Number */}
                  <div className="text-xs text-neutral-600 mb-1">Step {index + 1}</div>

                  {/* Name */}
                  <h4 className="text-sm font-display font-semibold text-secondary mb-2">
                    {step.name}
                  </h4>

                  {/* Status Badge */}
                  <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium mb-2 ${
                    config.color === 'success' ? 'bg-success/20 text-success' :
                    config.color === 'primary' ? 'bg-primary/20 text-primary' :
                    config.color === 'secondary' ? 'bg-secondary/20 text-secondary' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {config.status}
                  </div>

                  {/* Signed By */}
                  <div className="text-xs text-neutral-600 mb-2">
                    {chain && getMandateDetails(step.id) ? (
                      <div>
                        <div className="font-semibold text-secondary">{getMandateDetails(step.id).signer}</div>
                        {getMandateDetails(step.id).timestamp && (
                          <div className="text-xs text-neutral-500 mt-1">
                            {new Date(getMandateDetails(step.id).timestamp).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit',
                              hour12: true
                            })}
                          </div>
                        )}
                      </div>
                    ) : (
                      config.signed
                    )}
                  </div>

                  {/* Mandate ID (if chain data available) */}
                  {chain && getMandateDetails(step.id) && (
                    <div className="text-xs font-mono text-primary bg-primary/5 px-2 py-1 rounded mt-2 truncate" title={getMandateDetails(step.id).id}>
                      {getMandateDetails(step.id).id.substring(0, 20)}...
                    </div>
                  )}

                  {/* Description (shown on hover) */}
                  {isHovered && (
                    <div className="mt-3 pt-3 border-t border-neutral-200">
                      <p className="text-xs text-secondary leading-relaxed">
                        {config.description}
                      </p>
                    </div>
                  )}
                </div>

                {/* Tooltip (shown on hover) */}
                {isHovered && (
                  <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 translate-y-full z-20 w-64">
                    <div className="modern-card p-3 rounded-lg border border-primary/50 mt-2 shadow-xl">
                      <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                        <div className="w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-primary/50"></div>
                      </div>
                      <p className="text-xs text-secondary leading-relaxed">
                        {config.tooltip}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 pt-6 border-t border-neutral-200">
        <div className="flex items-center justify-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-success"></div>
            <span className="text-neutral-600">User Authorization</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary"></div>
            <span className="text-neutral-600">Agent Action</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-secondary"></div>
            <span className="text-neutral-600">Payment Network</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-neutral-500"></div>
            <span className="text-neutral-600">Context Only</span>
          </div>
        </div>
      </div>

      {/* Info Footer */}
      <div className="mt-4 modern-card bg-primary/5 border border-primary/20 rounded-lg p-3">
        <p className="text-xs text-secondary text-center">
          <span className="text-primary font-semibold">Hover over each step</span> for detailed explanations •
          <a href="https://ap2-protocol.org/specification/" target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary-dark ml-1 font-medium">
            Read AP2 Specification →
          </a>
        </p>
      </div>
        </div>
      )}
    </div>
  );
}
