/**
 * Home Page - AWS-Inspired Professional Theme
 * Main interface orchestrating HP flow
 */
import React, { useState, useEffect } from 'react';
import ChatInterface from '../components/ChatInterface';
import MonitoringStatusCard from '../components/MonitoringStatusCard';
import NotificationBanner from '../components/NotificationBanner';
import AP2InfoSection from '../components/AP2InfoSection';
import OrdersSection from '../components/OrdersSection';
import { useSession } from '../context/SessionContext';
import { api } from '../services/api';

export default function Home() {
  const { sessionId, userId, updateState } = useSession();

  // HNP Flow State
  const [monitoringJobs, setMonitoringJobs] = useState([]);
  const [notifications, setNotifications] = useState([]);

  // Mandate viewing state
  const [viewingMandate, setViewingMandate] = useState(null);

  /**
   * Fetch monitoring jobs (wrapped in useCallback to avoid dependency issues)
   */
  const fetchMonitoringJobs = React.useCallback(async () => {
    try {
      const response = await api.get(`/monitoring/jobs?user_id=${userId}&active_only=true`);
      setMonitoringJobs(response.jobs || []);
    } catch (error) {
      console.error('Failed to fetch monitoring jobs:', error);
    }
  }, [userId]);

  /**
   * Handle monitoring job cancellation
   */
  const handleCancelMonitoring = async (jobId) => {
    try {
      await api.delete(`/monitoring/jobs/${jobId}?user_id=${userId}`);
      await fetchMonitoringJobs();
    } catch (error) {
      console.error('Failed to cancel monitoring:', error);
    }
  };

  /**
   * Load monitoring jobs on mount and poll for updates
   */
  useEffect(() => {
    if (!userId) return;

    // Initial fetch
    fetchMonitoringJobs();

    // Poll every 5 seconds for updates
    const pollInterval = setInterval(() => {
      fetchMonitoringJobs();
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [userId, fetchMonitoringJobs]);

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* AWS-style accent bar */}
      <div className="accent-bar"></div>
      
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Professional Header */}
        <header className="mb-8 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              {/* AWS-style logo */}
              <div className="w-14 h-14 rounded-lg bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-aws">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              
              <div>
                <h1 className="text-4xl font-bold text-secondary mb-1">
                  AWS Strands Agent Payments
                </h1>
                <p className="text-sm text-secondary-light">
                  Implementing AP2 Protocol with AWS Strands SDK • <span className="text-primary font-semibold">v0.1-beta</span>
                </p>
              </div>
            </div>
            
            <div className="hidden md:flex items-center gap-3">
              <span className="badge badge-info">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                AWS Bedrock
              </span>
            </div>
          </div>
          
          <p className="text-secondary-light max-w-3xl">
            Demonstrating cryptographically verifiable payment authorization for AI agents using <span className="font-semibold text-primary">AWS Strands SDK</span>
          </p>
        </header>

        {/* AP2 Info Section */}
        <div className="mb-8 animate-slide-up">
          <AP2InfoSection />
        </div>

        {/* Notification Banners */}
        {notifications.map((notification, idx) => (
          <NotificationBanner
            key={idx}
            notification={notification}
            onDismiss={() => setNotifications(prev => prev.filter((_, i) => i !== idx))}
            onViewChain={async (txnId) => {
              try {
                const chainResponse = await api.get(`/transactions/${txnId}/chain`);
                setTransactionChain(chainResponse);
              } catch (error) {
                console.error('Failed to fetch transaction chain:', error);
              }
            }}
          />
        ))}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Chat Interface (handles HP flow inline) */}
          <div className="lg:col-span-2 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <div className="modern-card p-6 h-[700px] flex flex-col">
              <div className="card-header flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="status-dot active"></div>
                  <h2 className="text-lg font-semibold text-secondary">
                    AI Shopping Assistant
                  </h2>
                  <span className="ml-auto badge badge-info font-mono text-xs">
                    {sessionId?.slice(0, 8)}...
                  </span>
                </div>
              </div>
              <div className="flex-1 min-h-0">
                <ChatInterface />
              </div>
            </div>
          </div>

          {/* Right: Monitoring Jobs (HNP flow) */}
          <div className="space-y-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
            {/* Monitoring Header */}
            {monitoringJobs.length > 0 && (
              <div className="modern-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="status-dot pending"></div>
                  <h3 className="text-sm font-semibold text-secondary">
                    Active Monitoring
                  </h3>
                </div>
                <p className="text-xs text-neutral-600">
                  Autonomous purchase monitoring
                </p>
              </div>
            )}
            
            {/* Active Monitoring Jobs */}
            {monitoringJobs.length > 0 && monitoringJobs.map(job => (
              <MonitoringStatusCard
                key={job.job_id}
                job={job}
                onCancel={handleCancelMonitoring}
                onViewChain={async (intentId) => {
                  try {
                    console.log('Fetching intent mandate:', intentId);
                    const response = await api.get(`/mandates/${intentId}`);
                    setViewingMandate(response);
                  } catch (error) {
                    console.error('Failed to fetch intent mandate:', error);
                    alert('Failed to load mandate details');
                  }
                }}
              />
            ))}

            {/* Empty State */}
            {monitoringJobs.length === 0 && (
              <div className="modern-card p-8 text-center">
                <div className="icon-container mx-auto mb-4 opacity-50">
                  <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm text-secondary mb-2 font-medium">
                  No active monitoring
                </p>
                <p className="text-xs text-neutral-600">
                  Set up price alerts and autonomous purchases
                </p>
              </div>
            )}

            {/* Orders Section */}
            <OrdersSection userId={userId} />
          </div>
        </div>

        {/* Professional Footer */}
        <footer className="mt-12 pt-8 border-t border-neutral-200 animate-fade-in">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm text-secondary">
              <svg className="w-4 h-4 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>
                Implementing <span className="font-bold text-primary">AP2 Protocol</span> using <span className="font-bold text-accent">AWS Strands SDK</span> +  <span className="font-bold text-accent">AWS Bedrock</span>
              </span>
            </div>
            
            <div className="flex items-center gap-4 text-sm text-neutral-600">
              <span>Team: <span className="font-bold text-secondary">Agent Strands</span></span>
              <span className="text-neutral-300">|</span>
              <span>Demonstrating AP2 Interoperability</span>
            </div>
          </div>
        </footer>
      </div>

      {/* Intent Mandate Modal */}
      {viewingMandate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="modern-card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="sticky top-0 bg-white border-b border-neutral-200 p-6 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-display font-semibold text-secondary mb-1">
                  Intent Mandate Details
                </h3>
                <p className="text-xs text-neutral-600 font-mono">
                  {viewingMandate.mandate_id}
                </p>
              </div>
              <button
                onClick={() => setViewingMandate(null)}
                className="w-8 h-8 rounded-lg hover:bg-neutral-100 flex items-center justify-center transition-colors"
              >
                <svg className="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Status Badge */}
              <div className="flex items-center gap-2">
                <span className={`badge ${
                  viewingMandate.validation_status === 'valid' ? 'badge-success' :
                  viewingMandate.validation_status === 'unsigned' ? 'badge-warning' :
                  'badge-error'
                }`}>
                  {viewingMandate.validation_status === 'valid' ? '✓ Signed' :
                   viewingMandate.validation_status === 'unsigned' ? '⏳ Unsigned' :
                   '✗ Invalid'}
                </span>
                <span className="text-xs text-neutral-600">
                  Created {new Date(viewingMandate.created_at).toLocaleString()}
                </span>
              </div>

              {/* Product Query */}
              <div className="modern-card bg-primary/5 border border-primary/20 p-4">
                <div className="text-xs text-neutral-600 mb-1 font-semibold">Product Query</div>
                <div className="text-base font-medium text-secondary">
                  {viewingMandate.mandate_data.product_query}
                </div>
              </div>

              {/* Constraints */}
              {viewingMandate.mandate_data.constraints && (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-secondary">Constraints</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="modern-card p-3">
                      <div className="text-xs text-neutral-600 mb-1">Max Price</div>
                      <div className="text-lg font-bold text-success">
                        ${(viewingMandate.mandate_data.constraints.max_price_cents / 100).toFixed(2)}
                      </div>
                    </div>
                    <div className="modern-card p-3">
                      <div className="text-xs text-neutral-600 mb-1">Max Delivery</div>
                      <div className="text-lg font-bold text-primary">
                        {viewingMandate.mandate_data.constraints.max_delivery_days} days
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Expiration */}
              {viewingMandate.mandate_data.expiration && (
                <div className="modern-card p-3">
                  <div className="text-xs text-neutral-600 mb-1">Expiration</div>
                  <div className="text-sm text-secondary">
                    {new Date(viewingMandate.mandate_data.expiration).toLocaleString()}
                  </div>
                </div>
              )}

              {/* Signature */}
              {viewingMandate.mandate_data.signature && (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-secondary">Signature</h4>
                  <div className="modern-card bg-success/5 border border-success/20 p-4 space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Algorithm</span>
                      <span className="text-secondary font-mono">
                        {viewingMandate.mandate_data.signature.algorithm}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Signer</span>
                      <span className="text-secondary font-mono">
                        {viewingMandate.mandate_data.signature.signer_identity}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Timestamp</span>
                      <span className="text-secondary">
                        {new Date(viewingMandate.mandate_data.signature.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-success/20">
                      <div className="text-xs text-neutral-600 mb-1">Signature Value</div>
                      <div className="text-xs font-mono text-success break-all bg-white p-2 rounded">
                        {viewingMandate.mandate_data.signature.signature_value}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Scenario */}
              <div className="modern-card p-3">
                <div className="text-xs text-neutral-600 mb-1">Scenario</div>
                <div className="text-sm text-secondary">
                  {viewingMandate.mandate_data.scenario === 'human_not_present' ?
                    '🤖 Human-Not-Present (Autonomous)' :
                    '👤 Human-Present (Immediate)'}
                </div>
              </div>

              {/* AP2 Compliance Note */}
              <div className="modern-card bg-primary/5 border border-primary/20 p-3">
                <p className="text-xs text-secondary">
                  <span className="font-semibold text-primary">AP2 Compliance:</span> This Intent mandate
                  serves as pre-authorization for autonomous purchases. The agent must verify that any Cart
                  created references this Intent and stays within these constraints.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-white border-t border-neutral-200 p-4 flex justify-end">
              <button
                onClick={() => setViewingMandate(null)}
                className="btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
