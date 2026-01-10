'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatDateTime, cn } from '@/lib/utils';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import type { CircuitBreaker } from '@/types';

export function CircuitBreakers() {
  const { on, off } = useWebSocket();
  const { data: breakers, refetch } = useApi<CircuitBreaker[]>(() => apiClient.getCircuitBreakers(), 5000);

  useEffect(() => {
    on('circuit_breaker', (data) => {
      refetch();
    });

    return () => {
      off('circuit_breaker');
    };
  }, [on, off, refetch]);

  const breakerLabels: Record<string, string> = {
    DAILY_LOSS_LIMIT: 'Daily Loss Limit',
    CONSECUTIVE_LOSSES: 'Consecutive Losses',
    MAX_POSITIONS: 'Max Positions',
    MAX_DAILY_TRADES: 'Max Daily Trades',
    PORTFOLIO_HEAT: 'Portfolio Heat',
    VOLATILITY_SPIKE: 'Volatility Spike',
    MANUAL_KILL_SWITCH: 'Kill Switch',
  };

  const activeCount = breakers?.filter((b) => b.is_active).length || 0;
  const totalBreakers = 7;
  const healthPct = ((totalBreakers - activeCount) / totalBreakers) * 100;

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-display font-medium">Circuit Breakers</h2>
        <div className="text-right">
          <p className="text-xs text-text-secondary">System Health</p>
          <p className={cn('text-xl font-mono font-light', healthPct === 100 ? 'text-profit' : healthPct > 50 ? 'text-warning' : 'text-loss')}>
            {healthPct.toFixed(0)}%
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {breakers?.map((breaker) => (
          <div
            key={breaker.breaker_type}
            className={cn(
              'glass-card p-4 transition-all duration-300',
              breaker.is_active
                ? 'border-loss/50 bg-loss/5 animate-pulse-glow'
                : 'border/50'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {breaker.is_active ? (
                  <XCircle className="w-6 h-6 text-loss animate-pulse" />
                ) : (
                  <CheckCircle className="w-6 h-6 text-profit" />
                )}
                <div>
                  <p className="font-display font-semibold">
                    {breakerLabels[breaker.breaker_type] || breaker.breaker_type}
                  </p>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {breaker.is_active ? (
                      <span className="text-loss font-mono">ACTIVE</span>
                    ) : (
                      <span className="text-profit font-mono">OK</span>
                    )}
                  </p>
                </div>
              </div>
              {breaker.is_active && breaker.triggered_at && (
                <div className="text-right text-xs">
                  <p className="text-text-secondary">Triggered</p>
                  <p className="font-mono">{formatDateTime(breaker.triggered_at)}</p>
                </div>
              )}
            </div>
            {breaker.is_active && breaker.reason && (
              <div className="mt-3 pt-3 border-t border/30">
                <p className="text-xs text-text-secondary">Reason:</p>
                <p className="text-sm mt-1">{breaker.reason}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {activeCount > 0 && (
        <div className="mt-6 glass-card p-4 border-loss/50 bg-loss/5">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-loss flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-display font-semibold text-loss">Trading Halted</p>
              <p className="text-sm text-text-secondary mt-1">
                {activeCount} circuit breaker{activeCount > 1 ? 's' : ''} active. Trading is suspended.
                Clear breakers to resume.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
