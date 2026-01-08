'use client';

import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { Shield, AlertTriangle, TrendingDown, Activity } from 'lucide-react';

export default function RiskPage() {
  const { isConnected, on, off } = useWebSocket();
  const { data: riskMetrics, refetch } = useApi(() => apiClient.getRiskMetrics(), 5000);
  const { data: positions } = useApi(() => apiClient.getPositions(), 5000);

  useEffect(() => {
    on('risk_update', () => refetch());
    return () => off('risk_update');
  }, [on, off, refetch]);

  if (!riskMetrics) {
    return (
      <div className="p-6 flex items-center justify-center h-screen">
        <div className="text-terminal-text-secondary">Loading risk metrics...</div>
      </div>
    );
  }

  const portfolioHeat = riskMetrics.portfolio_heat || 0;
  const dailyPnL = riskMetrics.daily_pnl || 0;
  const dailyPnLPct = riskMetrics.daily_pnl_pct || 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Shield className="w-8 h-8 text-profit" />
          <h1 className="text-3xl font-medium text-profit tracking-tight">Risk Analytics</h1>
        </div>
        <div className={`flex items-center space-x-2 ${isConnected ? 'text-profit' : 'text-loss'}`}>
          <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
          <span className="text-sm">{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Key Risk Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Portfolio Heat</span>
            <Activity className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="relative mb-3">
            <div className="h-3 bg-terminal-bg rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  portfolioHeat < 0.4 ? 'bg-profit' :
                  portfolioHeat < 0.7 ? 'bg-warning' : 'bg-loss'
                }`}
                style={{ width: `${Math.min(portfolioHeat * 100, 100)}%` }}
              />
            </div>
          </div>
          <div className={`text-2xl font-light font-mono ${
            portfolioHeat < 0.4 ? 'text-profit' :
            portfolioHeat < 0.7 ? 'text-warning' : 'text-loss'
          }`}>
            {formatPercent(portfolioHeat)}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Daily P&L</span>
            <TrendingDown className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className={`text-2xl font-light font-mono ${dailyPnL >= 0 ? 'profit-glow' : 'loss-glow'}`}>
            {formatCurrency(dailyPnL)}
          </div>
          <div className={`text-sm font-mono mt-1 ${dailyPnLPct >= 0 ? 'text-profit' : 'text-loss'}`}>
            {formatPercent(dailyPnLPct)}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Open Positions</span>
            <Activity className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {positions?.length || 0}
          </div>
          <div className="text-sm text-terminal-text-secondary mt-1">
            of {riskMetrics.max_positions || 5} max
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Buying Power</span>
            <AlertTriangle className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="text-2xl font-bold font-mono text-accent-purple">
            {formatCurrency(riskMetrics.buying_power || 0)}
          </div>
        </div>
      </div>

      {/* Position Risk Breakdown */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold mb-4 text-accent-cyan">Position Risk Exposure</h2>
        <div className="space-y-3">
          {positions?.map((position: any) => {
            const risk = Math.abs(position.unrealized_pnl || 0);
            const riskPct = position.unrealized_pnl_pct || 0;
            const positionHeat = Math.abs(riskPct) / 100;

            return (
              <div key={position.id} className="p-4 bg-terminal-bg rounded border border-terminal-border">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-xl font-bold font-mono">{position.symbol}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      position.side === 'LONG' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'
                    }`}>
                      {position.side}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className={`text-lg font-bold font-mono ${
                      position.unrealized_pnl >= 0 ? 'text-profit' : 'text-loss'
                    }`}>
                      {formatCurrency(position.unrealized_pnl)}
                    </div>
                    <div className={`text-sm font-mono ${
                      riskPct >= 0 ? 'text-profit' : 'text-loss'
                    }`}>
                      {formatPercent(riskPct / 100)}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 text-sm mb-3">
                  <div>
                    <div className="text-xs text-terminal-text-secondary">Entry</div>
                    <div className="font-mono">{formatCurrency(position.entry_price)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-terminal-text-secondary">Current</div>
                    <div className="font-mono">{formatCurrency(position.current_price)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-terminal-text-secondary">Stop</div>
                    <div className="font-mono text-loss">
                      {position.stop_loss ? formatCurrency(position.stop_loss) : '-'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-terminal-text-secondary">Target</div>
                    <div className="font-mono text-profit">
                      {position.take_profit ? formatCurrency(position.take_profit) : '-'}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-terminal-text-secondary">Position Heat</span>
                    <span className="text-xs font-mono">{formatPercent(positionHeat)}</span>
                  </div>
                  <div className="h-2 bg-terminal-surface rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        positionHeat < 0.1 ? 'bg-profit' :
                        positionHeat < 0.15 ? 'bg-warning' : 'bg-loss'
                      }`}
                      style={{ width: `${Math.min(positionHeat * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Risk Limits */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 text-warning">Daily Limits</h2>
          <div className="space-y-4">
            <LimitItem
              label="Daily P&L"
              current={dailyPnL}
              limit={riskMetrics.daily_loss_limit || -500}
              formatFn={formatCurrency}
            />
            <LimitItem
              label="Daily Trades"
              current={riskMetrics.daily_trade_count || 0}
              limit={riskMetrics.max_daily_trades || 10}
              formatFn={(v) => v.toString()}
            />
            <LimitItem
              label="Consecutive Losses"
              current={riskMetrics.consecutive_losses || 0}
              limit={riskMetrics.max_consecutive_losses || 3}
              formatFn={(v) => v.toString()}
            />
          </div>
        </div>

        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 text-profit">Portfolio Metrics</h2>
          <div className="space-y-3">
            <MetricRow label="Total Equity" value={formatCurrency(riskMetrics.total_equity || 0)} />
            <MetricRow label="Cash" value={formatCurrency(riskMetrics.cash || 0)} />
            <MetricRow label="Margin Used" value={formatCurrency(riskMetrics.margin_used || 0)} />
            <MetricRow
              label="Leverage"
              value={`${(riskMetrics.leverage || 1).toFixed(2)}x`}
              valueClass={riskMetrics.leverage > 2 ? 'text-warning' : 'text-white'}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function LimitItem({
  label,
  current,
  limit,
  formatFn
}: {
  label: string;
  current: number;
  limit: number;
  formatFn: (v: number) => string;
}) {
  const pct = Math.abs(current / limit) * 100;
  const isNearLimit = pct > 80;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-terminal-text-secondary">{label}</span>
        <span className={`text-sm font-mono ${isNearLimit ? 'text-loss' : 'text-white'}`}>
          {formatFn(current)} / {formatFn(limit)}
        </span>
      </div>
      <div className="h-2 bg-terminal-bg rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${
            pct < 50 ? 'bg-profit' :
            pct < 80 ? 'bg-warning' : 'bg-loss'
          }`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function MetricRow({
  label,
  value,
  valueClass = 'text-white'
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-terminal-bg rounded">
      <span className="text-sm text-terminal-text-secondary">{label}</span>
      <span className={`font-mono font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}
