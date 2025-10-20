import React, { useState } from 'react';
import MandateChainFlow from './MandateChainFlow';

const AP2InfoSection = () => {
  const [selectedMode, setSelectedMode] = useState('hp');
  return (
    <div className="modern-card p-8 mb-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="icon-container">
            <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold gradient-text">
            About This Demo
          </h2>
        </div>
        <p className="text-lg text-secondary-light max-w-3xl mx-auto">
          This demonstrates the <span className="text-primary font-semibold">Agent Payments Protocol (AP2)</span> implementation using <span className="text-accent font-semibold">AWS Strands SDK</span>. 
          AP2 is an open standard that enables AI agents to make secure payments on your behalf with cryptographic proof of authorization.
        </p>
      </div>

      {/* Key Features Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Security */}
        <div className="stat-card group cursor-pointer">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-success/20 to-success/10 border border-success/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <svg className="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2 text-success">Security</h3>
          <p className="text-neutral-600 text-sm leading-relaxed">
            Clear accountability through cryptographically signed mandates that create a tamper-proof audit trail
          </p>
        </div>

        {/* Interoperability */}
        <div className="stat-card group cursor-pointer">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2 text-primary">Interoperability</h3>
          <p className="text-neutral-600 text-sm leading-relaxed">
            Any compliant agent works with any merchant. Proving AP2 works with AWS Strands SDK
          </p>
        </div>

        {/* Privacy */}
        <div className="stat-card group cursor-pointer">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-secondary/20 to-secondary/10 border border-secondary/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <svg className="w-6 h-6 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2 text-secondary">Privacy</h3>
          <p className="text-neutral-600 text-sm leading-relaxed">
            Shopping agents never see your payment credentials. Role separation ensures data security
          </p>
        </div>
      </div>

      {/* How It Works - Quick Overview */}
      <div className="modern-card p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-secondary">
          <span className="text-primary">⚡</span>
          How It Works
        </h3>
        <div className="space-y-3 text-secondary">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-primary text-xs font-bold">1</span>
            </div>
            <p className="text-sm">
              <span className="font-semibold text-secondary">Verifiable Digital Credentials:</span> Every purchase creates cryptographically signed "mandates"
            </p>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-primary text-xs font-bold">2</span>
            </div>
            <p className="text-sm">
              <span className="font-semibold text-secondary">Mandate Chain:</span> Intent → Cart → Payment → Transaction creates complete audit trail
            </p>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-primary text-xs font-bold">3</span>
            </div>
            <p className="text-sm">
              <span className="font-semibold text-secondary">Two Modes:</span> Human-Present (immediate) and Human-Not-Present (autonomous)
            </p>
          </div>
        </div>
      </div>

      {/* Mode Toggle */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <button
          onClick={() => setSelectedMode('hp')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-300 ${
            selectedMode === 'hp'
              ? 'btn-primary'
              : 'btn-outline'
          }`}
        >
          Human-Present Flow
        </button>
        <button
          onClick={() => setSelectedMode('hnp')}
          className={`px-6 py-3 rounded-xl font-medium transition-all duration-300 ${
            selectedMode === 'hnp'
              ? 'btn-secondary'
              : 'btn-outline'
          }`}
        >
          Human-Not-Present Flow
        </button>
      </div>

      {/* Interactive Mandate Chain Flow */}
      <MandateChainFlow mode={selectedMode} />

      {/* Demo Badge */}
      <div className="mt-6 text-center">
        <div className="badge badge-success">
          <div className="status-dot active mr-2"></div>
          <span className="text-sm">
            Live Demo • Powered by <span className="font-semibold">AP2 Protocol v0.1</span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default AP2InfoSection;
