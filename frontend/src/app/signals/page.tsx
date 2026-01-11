'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatPercent, formatDateTime } from '@/lib/utils';
import { TrendingUp, TrendingDown, Filter, Radio } from 'lucide-react';
import type { Signal } from '@/types';

export default function SignalsPage() {
  const { data: signals } = useApi(() => apiClient.getSignals({ limit: 200 }), 10000);
  const [strategyFilter, setStrategyFilter] = useState<string>('ALL');
  const [directionFilter, setDirectionFilter] = useState<string>('ALL');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');

  const filtered = signals?.filter((signal: Signal) => {
    if (strategyFilter !== 'ALL' && signal.strategy_name !== strategyFilter) return false;
    if (directionFilter !== 'ALL' && signal.direction !== directionFilter) return false;
    if (decisionFilter !== 'ALL' && signal.decision !== decisionFilter) return false;
    return true;
  }) || [];

  const strategies = [...new Set(signals?.map((s: Signal) => s.strategy_name) || [])];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Radio className="w-8 h-8 text-accent-cyan" />
          <h1 className="text-3xl font-medium text-accent-cyan tracking-tight">Signal History</h1>
        </div>
        <div className="text-sm text-terminal-text-secondary">
          Showing {filtered.length} of {signals?.length || 0} signals
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="w-5 h-5 text-accent-purple" />
          <span className="font-medium">Filters</span>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-terminal-text-secondary mb-2">Strategy</label>
            <select
              value={strategyFilter}
              onChange={(e) => setStrategyFilter(e.target.value)}
              className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent-purple"
            >
              <option value="ALL">All Strategies</option>
              {strategies.map((strategy) => (
                <option key={strategy} value={strategy}>{strategy}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-terminal-text-secondary mb-2">Direction</label>
            <select
              value={directionFilter}
              onChange={(e) => setDirectionFilter(e.target.value)}
              className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent-purple"
            >
              <option value="ALL">All Directions</option>
              <option value="LONG">Long</option>
              <option value="SHORT">Short</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-terminal-text-secondary mb-2">Decision</label>
            <select
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
              className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent-purple"
            >
              <option value="ALL">All Decisions</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="PENDING">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Signals Grid */}
      <div className="grid grid-cols-1 gap-4">
        {filtered.map((signal: Signal) => {
          const riskReward = signal.suggested_target && signal.suggested_stop
            ? Math.abs((signal.suggested_target - signal.suggested_entry) /
                      (signal.suggested_entry - signal.suggested_stop))
            : 0;

          return (
            <div key={signal.id} className="glass-card p-6 hover:border-accent-purple/50 transition-all">
              <div className="grid grid-cols-5 gap-6">
                {/* Symbol & Direction */}
                <div>
                  <div className="text-xs text-terminal-text-secondary mb-1">Symbol</div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xl font-bold font-mono">{signal.symbol}</span>
                    <div className={`p-1.5 rounded ${
                      signal.direction === 'LONG'
                        ? 'bg-profit/20 text-profit'
                        : 'bg-loss/20 text-loss'
                    }`}>
                      {signal.direction === 'LONG'
                        ? <TrendingUp className="w-4 h-4" />
                        : <TrendingDown className="w-4 h-4" />
                      }
                    </div>
                  </div>
                  <div className="text-sm text-terminal-text-secondary mt-1">
                    {signal.strategy_name}
                  </div>
                </div>

                {/* Prices */}
                <div>
                  <div className="space-y-2">
                    <div>
                      <div className="text-xs text-terminal-text-secondary">Entry</div>
                      <div className="font-mono font-bold text-accent-cyan">
                        {formatCurrency(signal.suggested_entry)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-terminal-text-secondary">Stop</div>
                      <div className="font-mono text-loss">
                        {formatCurrency(signal.suggested_stop)}
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="space-y-2">
                    <div>
                      <div className="text-xs text-terminal-text-secondary">Target</div>
                      <div className="font-mono text-profit">
                        {formatCurrency(signal.suggested_target)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-terminal-text-secondary">R:R</div>
                      <div className="font-mono text-accent-purple">
                        {riskReward.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Confidence */}
                <div>
                  <div className="text-xs text-terminal-text-secondary mb-1">Confidence</div>
                  <div className="relative h-2 bg-terminal-bg rounded-full overflow-hidden">
                    <div
                      className="absolute h-full bg-gradient-to-r from-accent-purple to-accent-cyan"
                      style={{ width: `${signal.confidence * 100}%` }}
                    />
                  </div>
                  <div className="text-sm font-mono mt-1">{formatPercent(signal.confidence)}</div>
                  <div className="text-xs text-terminal-text-secondary mt-2">
                    {formatDateTime(signal.generated_at)}
                  </div>
                </div>

                {/* Decision */}
                <div className="flex flex-col items-end justify-between">
                  <span className={`px-3 py-1.5 rounded text-sm font-semibold ${
                    signal.decision === 'APPROVED'
                      ? 'bg-profit/20 text-profit border border-profit/30'
                      : signal.decision === 'REJECTED'
                      ? 'bg-loss/20 text-loss border border-loss/30'
                      : 'bg-warning/20 text-warning border border-warning/30'
                  }`}>
                    {signal.decision || 'PENDING'}
                  </span>
                  {signal.decision_reason && (
                    <div className="text-xs text-terminal-text-secondary text-right mt-2">
                      {signal.decision_reason}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
