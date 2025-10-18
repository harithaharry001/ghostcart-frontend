/**
 * Home Page
 * Main interface orchestrating HP flow
 *
 * Note: ChatInterface now manages its own EventSource and displays products/cart inline.
 * The old SSE-based state management has been replaced with the unified streaming approach.
 */
import React, { useState, useEffect } from 'react';
import ChatInterface from '../components/ChatInterface';
import MonitoringStatusCard from '../components/MonitoringStatusCard';
import NotificationBanner from '../components/NotificationBanner';
import { useSession } from '../context/SessionContext';
import { api } from '../services/api';

export default function Home() {
  const { sessionId, userId, updateState } = useSession();

  // HNP Flow State
  const [monitoringJobs, setMonitoringJobs] = useState([]);
  const [notifications, setNotifications] = useState([]);

  /**
   * Fetch monitoring jobs
   */
  const fetchMonitoringJobs = async () => {
    try {
      const response = await api.get(`/monitoring/jobs?user_id=${userId}&active_only=true`);
      setMonitoringJobs(response.jobs || []);
    } catch (error) {
      console.error('Failed to fetch monitoring jobs:', error);
    }
  };

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

  // Note: HP flow (products, cart, signatures) is now handled entirely within ChatInterface
  // which manages its own EventSource connection and displays inline

  /**
   * Load monitoring jobs on mount
   */
  useEffect(() => {
    fetchMonitoringJobs();
  }, [userId]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            GhostCart
            <span className="text-primary ml-2">AP2 Demo</span>
          </h1>
          <p className="text-gray-600">
            Agent Payments Protocol v0.1 - Mandate-based purchase flows
          </p>
        </header>

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
          <div className="lg:col-span-2">
            <div className="h-[600px]">
              <ChatInterface />
            </div>
          </div>

          {/* Right: Monitoring Jobs (HNP flow) */}
          <div className="space-y-6">
            {/* Active Monitoring Jobs */}
            {monitoringJobs.length > 0 && monitoringJobs.map(job => (
              <MonitoringStatusCard
                key={job.job_id}
                job={job}
                onCancel={handleCancelMonitoring}
                onViewChain={async (intentId) => {
                  try {
                    // Fetch mandate by ID (would need mandate endpoint)
                    console.log('View intent mandate:', intentId);
                    // Note: Full implementation requires /api/mandates/{mandate_id} endpoint
                  } catch (error) {
                    console.error('Failed to fetch intent mandate:', error);
                  }
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
