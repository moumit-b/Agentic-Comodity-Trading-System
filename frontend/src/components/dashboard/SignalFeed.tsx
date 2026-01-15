'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatDateTime, cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, ChevronDown, Filter } from 'lucide-react';
import type { Signal } from '@/types';

export function SignalFeed() {
  const { on, off } = useWebSocket();
  const { data: signals, refetch } = useApi<Signal[]>(() => apiClient.getSignals({ limit: 50 }), 30000);
  const [filteredSignals, setFilteredSignals] = useState<Signal[]>([]);
  const [strategyFilter, setStrategyFilter] = useState('All');
  const [directionFilter, setDirectionFilter] = useState('All');

  useEffect(() => {
    const handler = () => refetch();
    on('signal_new', handler);
    return () => off('signal_new', handler);
  }, [on, off, refetch]);

  useEffect(() => {
    if (!signals) return;

    let filtered = [...signals];

    if (strategyFilter !== 'All') {
      filtered = filtered.filter((s) => s.strategy_name === strategyFilter);
    }

    if (directionFilter !== 'All') {
      filtered = filtered.filter((s) => s.direction === directionFilter);
    }

    setFilteredSignals(filtered);
  }, [signals, strategyFilter, directionFilter]);

  const strategies = signals ? ['All', ...new Set(signals.map((s) => s.strategy_name))] : ['All'];

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-display font-medium">Signal Feed</h2>
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-text-secondary" />
          <select
            value={strategyFilter}
            onChange={(e) => setStrategyFilter(e.target.value)}
            className="glass-card px-3 py-1 text-sm font-mono cursor-pointer hover:bg-white/5 transition-colors"
          >
            {strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
          <select
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value)}
            className="glass-card px-3 py-1 text-sm font-mono cursor-pointer hover:bg-white/5 transition-colors"
          >
            <option value="All">All</option>
            <option value="LONG">Long</option>
            <option value="SHORT">Short</option>
          </select>
        </div>
      </div>

      {signals && (
        <div className="mb-4 grid grid-cols-3 gap-4">
          <div className="glass-card p-3">
            <p className="text-xs text-text-secondary">Long Signals</p>
            <p className="text-base font-mono font-medium text-profit">
              {signals.filter((s) => s.direction === 'LONG').length}
            </p>
          </div>
          <div className="glass-card p-3">
            <p className="text-xs text-text-secondary">Short Signals</p>
            <p className="text-base font-mono font-medium text-loss">
              {signals.filter((s) => s.direction === 'SHORT').length}
            </p>
          </div>
          <div className="glass-card p-3">
            <p className="text-xs text-text-secondary">Avg Confidence</p>
            <p className="text-base font-mono font-medium">
              {((signals.reduce((sum, s) => sum + s.confidence, 0) / signals.length) * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
        {filteredSignals.map((signal) => {
          const riskReward =
            Math.abs(signal.suggested_target - signal.suggested_entry) /
            Math.abs(signal.suggested_entry - signal.suggested_stop);

          return (
            <div
              key={signal.id}
              className={cn(
                'glass-card p-4 border-l-2 hover:bg-white/5 transition-all duration-200',
                signal.direction === 'LONG' ? 'border-profit' : 'border-loss'
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  {signal.direction === 'LONG' ? (
                    <TrendingUp className="w-5 h-5 text-profit" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-loss" />
                  )}
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-medium text-base">{signal.symbol}</span>
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded text-xs font-mono font-semibold',
                          signal.direction === 'LONG' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'
                        )}
                      >
                        {signal.direction}
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary mt-1">
                      {signal.strategy_name} • {signal.timeframe}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {signal.decision === 'APPROVED' && (
                    <span className="px-2 py-1 rounded text-xs font-mono font-semibold bg-profit/20 text-profit">
                      APPROVED
                    </span>
                  )}
                  {signal.decision === 'REJECTED' && (
                    <span className="px-2 py-1 rounded text-xs font-mono font-semibold bg-loss/20 text-loss">
                      REJECTED
                    </span>
                  )}
                  {signal.decision === 'PENDING' && (
                    <span className="px-2 py-1 rounded text-xs font-mono font-semibold bg-border text-text-secondary">
                      PENDING
                    </span>
                  )}
                </div>
              </div>

              {/* Price Levels */}
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <p className="text-xs text-text-secondary">Entry</p>
                  <p className="font-mono font-semibold">{formatCurrency(signal.suggested_entry)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Stop</p>
                  <p className="font-mono font-semibold text-loss">{formatCurrency(signal.suggested_stop)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Target</p>
                  <p className="font-mono font-semibold text-profit">{formatCurrency(signal.suggested_target)}</p>
                </div>
              </div>

              {/* Confidence & R:R */}
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-text-secondary">Confidence</span>
                    <span className="font-mono font-semibold">{(signal.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-accent-blue to-accent-purple transition-all duration-500"
                      style={{ width: `${signal.confidence * 100}%` }}
                    />
                  </div>
                </div>
                <div className="ml-4 text-right">
                  <p className="text-xs text-text-secondary">R:R</p>
                  <p className="font-mono font-semibold">1:{riskReward.toFixed(2)}</p>
                </div>
              </div>

              {/* Timestamp */}
              <p className="text-xs text-text-secondary mt-3">{formatDateTime(signal.timestamp)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
