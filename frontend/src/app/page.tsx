'use client';

import { SystemStatus } from '@/components/dashboard/SystemStatus';
import { PriceChart } from '@/components/dashboard/PriceChart';
import { PositionsTable } from '@/components/dashboard/PositionsTable';
import { SignalFeed } from '@/components/dashboard/SignalFeed';
import { RiskGauges } from '@/components/dashboard/RiskGauges';
import { CircuitBreakers } from '@/components/dashboard/CircuitBreakers';
import { OrderConfirmation } from '@/components/dashboard/OrderConfirmation';

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-display font-medium text-accent-cyan tracking-tight mb-2">
          QUANTUM TERMINAL
        </h1>
        <p className="text-terminal-text-secondary text-sm">
          Real-time algorithmic trading dashboard with multi-agent orchestration
        </p>
      </div>

      {/* System Status Bar */}
      <SystemStatus />

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column (2/3) */}
        <div className="col-span-2 space-y-6">
          <div className="glass-card-depth ambient-glow">
            <PriceChart />
          </div>
          <PositionsTable />
        </div>

        {/* Right Column (1/3) */}
        <div className="col-span-1 space-y-6 section-vignette">
          <OrderConfirmation />
          <SignalFeed />
          <RiskGauges />
          <CircuitBreakers />
        </div>
      </div>
    </div>
  );
}
