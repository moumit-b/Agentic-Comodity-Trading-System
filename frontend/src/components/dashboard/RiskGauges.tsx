'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatPercent, cn } from '@/lib/utils';
import type { RiskMetrics } from '@/types';

export function RiskGauges() {
  const { on, off } = useWebSocket();
  const { data: riskMetrics, refetch } = useApi<RiskMetrics>(() => apiClient.getRiskMetrics(), 30000);

  useEffect(() => {
    on('risk_update', (data) => {
      refetch();
    });

    return () => {
      off('risk_update');
    };
  }, [on, off, refetch]);

  const getGaugeColor = (value: number, thresholds: { green: number; yellow: number }) => {
    if (value < thresholds.green) return '#00c853';
    if (value < thresholds.yellow) return '#ffc107';
    return '#ff1744';
  };

  return (
    <div className="glass-card p-6">
      <h2 className="text-lg font-display font-medium mb-6">Risk Metrics</h2>

      <div className="space-y-6">
        {/* Portfolio Heat Gauge */}
        {riskMetrics && (
          <div>
            <h3 className="text-sm font-display font-semibold text-text-secondary mb-3">
              Portfolio Heat
            </h3>
            <div className="relative w-48 h-24 mx-auto">
              <svg viewBox="0 0 200 120" className="w-full h-full">
                {/* Background arc */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="#1e1e2e"
                  strokeWidth="12"
                  strokeLinecap="round"
                />
                {/* Value arc */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke={getGaugeColor(riskMetrics.portfolio_heat_pct, { green: 40, yellow: 70 })}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${(riskMetrics.portfolio_heat_pct / 100) * 251.2} 251.2`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex items-end justify-center pb-2">
                <span className="text-2xl font-mono font-light">
                  {riskMetrics.portfolio_heat_pct.toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="flex justify-between text-xs text-text-secondary mt-2">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>
        )}

        {/* RSI Gauge */}
        {riskMetrics && (
          <div>
            <h3 className="text-sm font-display font-semibold text-text-secondary mb-3">
              RSI (USO)
            </h3>
            <div className="relative w-48 h-24 mx-auto">
              <svg viewBox="0 0 200 120" className="w-full h-full">
                {/* Background arc */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="#1e1e2e"
                  strokeWidth="12"
                  strokeLinecap="round"
                />
                {/* Value arc */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke={getGaugeColor(riskMetrics.current_rsi, { green: 30, yellow: 70 })}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${(riskMetrics.current_rsi / 100) * 251.2} 251.2`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex items-end justify-center pb-2">
                <span className="text-2xl font-mono font-light">
                  {riskMetrics.current_rsi.toFixed(1)}
                </span>
              </div>
            </div>
            <div className="flex justify-between text-xs text-text-secondary mt-2">
              <span className="text-loss">Oversold</span>
              <span>Neutral</span>
              <span className="text-profit">Overbought</span>
            </div>
          </div>
        )}

        {/* Daily P&L Progress */}
        {riskMetrics && (
          <div>
            <h3 className="text-sm font-display font-semibold text-text-secondary mb-3">
              Daily P&L Progress
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Target:</span>
                <span className="font-mono font-semibold text-profit">
                  +{riskMetrics.daily_target_pct.toFixed(1)}%
                </span>
              </div>
              <div className="relative h-6 bg-border rounded-full overflow-hidden">
                {/* Limit zone (red) */}
                <div
                  className="absolute left-0 top-0 h-full bg-loss/20"
                  style={{ width: '30%' }}
                />
                {/* Target zone (green) */}
                <div
                  className="absolute right-0 top-0 h-full bg-profit/20"
                  style={{ width: '20%' }}
                />
                {/* Current position */}
                <div
                  className={cn(
                    'absolute top-0 h-full transition-all duration-1000',
                    riskMetrics.daily_pnl_pct >= 0
                      ? 'bg-gradient-to-r from-accent-blue to-profit'
                      : 'bg-gradient-to-r from-loss to-accent-blue'
                  )}
                  style={{
                    left: '50%',
                    width: `${Math.abs(riskMetrics.daily_pnl_pct) * 10}%`,
                    transform: riskMetrics.daily_pnl_pct < 0 ? 'translateX(-100%)' : 'none',
                  }}
                />
                {/* Center marker */}
                <div className="absolute left-1/2 top-0 w-0.5 h-full bg-white/30" />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="font-mono font-semibold text-loss">
                  {riskMetrics.daily_limit_pct.toFixed(1)}%
                </span>
                <span className={cn('font-mono font-medium text-base', riskMetrics.daily_pnl_pct >= 0 ? 'text-profit' : 'text-loss')}>
                  {formatPercent(riskMetrics.daily_pnl_pct)}
                </span>
                <span className="font-mono font-semibold text-profit">
                  +{riskMetrics.daily_target_pct.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Consecutive Losses */}
        {riskMetrics && (
          <div className="glass-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-secondary">Consecutive Losses</p>
                <p className="text-xl font-mono font-light">
                  {riskMetrics.consecutive_losses} / {riskMetrics.max_consecutive_losses}
                </p>
              </div>
              <div className="relative w-16 h-16">
                <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                  <circle
                    cx="18"
                    cy="18"
                    r="16"
                    fill="none"
                    stroke="#1e1e2e"
                    strokeWidth="3"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="16"
                    fill="none"
                    stroke={riskMetrics.consecutive_losses >= riskMetrics.max_consecutive_losses ? '#ff1744' : '#ffc107'}
                    strokeWidth="3"
                    strokeDasharray={`${(riskMetrics.consecutive_losses / riskMetrics.max_consecutive_losses) * 100} 100`}
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-mono font-medium">
                    {((riskMetrics.consecutive_losses / riskMetrics.max_consecutive_losses) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
