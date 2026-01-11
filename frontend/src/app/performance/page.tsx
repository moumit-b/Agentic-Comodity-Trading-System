'use client';

import { useEffect, useRef, useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatPercent, formatDateTime } from '@/lib/utils';
import { TrendingUp, TrendingDown, DollarSign, Target, Activity } from 'lucide-react';
import { createChart, ColorType, UTCTimestamp } from 'lightweight-charts';

export default function PerformancePage() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const { data: executions } = useApi(() => apiClient.getExecutions(), 30000);

  // Calculate performance metrics
  const metrics = executions ? calculateMetrics(executions) : null;

  useEffect(() => {
    if (!chartContainerRef.current || !executions) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#12121a' },
        textColor: '#a0a0b0',
      },
      grid: {
        vertLines: { color: '#1e1e2e' },
        horzLines: { color: '#1e1e2e' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        borderColor: '#1e1e2e',
      },
    });

    const lineSeries = chart.addLineSeries({
      color: '#7c4dff',
      lineWidth: 2,
    });

    // Generate equity curve from executions
    const equityData = generateEquityCurve(executions);
    // Only set data if we have valid equity curve data
    if (equityData.length > 0) {
      lineSeries.setData(equityData);
    }

    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [executions]);

  if (!metrics) {
    return (
      <div className="p-6 flex items-center justify-center h-screen">
        <div className="text-terminal-text-secondary">Loading performance data...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-medium text-accent-purple tracking-tight">Performance Analytics</h1>
        <div className="text-sm text-terminal-text-secondary">Last updated: {new Date().toLocaleTimeString()}</div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Total P&L</span>
            <DollarSign className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className={`text-2xl font-bold font-mono ${metrics.totalPnL >= 0 ? 'profit-glow' : 'loss-glow'}`}>
            {formatCurrency(metrics.totalPnL)}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Win Rate</span>
            <Target className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="text-2xl font-bold font-mono text-accent-purple">
            {formatPercent(metrics.winRate)}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Total Trades</span>
            <Activity className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {metrics.totalTrades}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-terminal-text-secondary">Avg Win/Loss</span>
            <TrendingUp className="w-4 h-4 text-profit" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {metrics.avgWinLossRatio.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold mb-4 text-accent-cyan">Equity Curve</h2>
        <div ref={chartContainerRef} />
      </div>

      {/* Win/Loss Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 text-profit">Winning Trades</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Count:</span>
              <span className="font-mono text-profit">{metrics.winCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Total:</span>
              <span className="font-mono text-profit">{formatCurrency(metrics.winTotal)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Average:</span>
              <span className="font-mono text-profit">{formatCurrency(metrics.avgWin)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Largest:</span>
              <span className="font-mono text-profit">{formatCurrency(metrics.largestWin)}</span>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 text-loss">Losing Trades</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Count:</span>
              <span className="font-mono text-loss">{metrics.lossCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Total:</span>
              <span className="font-mono text-loss">{formatCurrency(metrics.lossTotal)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Average:</span>
              <span className="font-mono text-loss">{formatCurrency(metrics.avgLoss)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-text-secondary">Largest:</span>
              <span className="font-mono text-loss">{formatCurrency(metrics.largestLoss)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Executions */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold mb-4 text-accent-cyan">Recent Executions</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-terminal-border">
                <th className="text-left py-3 text-terminal-text-secondary text-sm">Time</th>
                <th className="text-left py-3 text-terminal-text-secondary text-sm">Symbol</th>
                <th className="text-left py-3 text-terminal-text-secondary text-sm">Side</th>
                <th className="text-right py-3 text-terminal-text-secondary text-sm">Qty</th>
                <th className="text-right py-3 text-terminal-text-secondary text-sm">Price</th>
                <th className="text-right py-3 text-terminal-text-secondary text-sm">P&L</th>
              </tr>
            </thead>
            <tbody>
              {executions?.slice(0, 20).map((exec: any, idx: number) => (
                <tr key={idx} className="border-b border-terminal-border/30 hover:bg-white/5">
                  <td className="py-3 text-sm font-mono">{formatDateTime(exec.executed_at)}</td>
                  <td className="py-3 text-sm font-mono font-bold">{exec.symbol}</td>
                  <td className="py-3">
                    <span className={`text-xs px-2 py-1 rounded ${
                      exec.side === 'BUY' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'
                    }`}>
                      {exec.side}
                    </span>
                  </td>
                  <td className="py-3 text-right font-mono text-sm">{exec.qty}</td>
                  <td className="py-3 text-right font-mono text-sm">{formatCurrency(exec.fill_price)}</td>
                  <td className={`py-3 text-right font-mono text-sm ${
                    (exec.realized_pnl || 0) >= 0 ? 'text-profit' : 'text-loss'
                  }`}>
                    {exec.realized_pnl ? formatCurrency(exec.realized_pnl) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function calculateMetrics(executions: any[]) {
  const closedTrades = executions.filter((e: any) => e.realized_pnl !== null);

  const wins = closedTrades.filter((e: any) => e.realized_pnl > 0);
  const losses = closedTrades.filter((e: any) => e.realized_pnl < 0);

  const totalPnL = closedTrades.reduce((sum: number, e: any) => sum + (e.realized_pnl || 0), 0);
  const winTotal = wins.reduce((sum: number, e: any) => sum + e.realized_pnl, 0);
  const lossTotal = losses.reduce((sum: number, e: any) => sum + e.realized_pnl, 0);

  return {
    totalPnL,
    totalTrades: closedTrades.length,
    winCount: wins.length,
    lossCount: losses.length,
    winRate: closedTrades.length > 0 ? wins.length / closedTrades.length : 0,
    winTotal,
    lossTotal,
    avgWin: wins.length > 0 ? winTotal / wins.length : 0,
    avgLoss: losses.length > 0 ? lossTotal / losses.length : 0,
    avgWinLossRatio: wins.length > 0 && losses.length > 0 ?
      (winTotal / wins.length) / Math.abs(lossTotal / losses.length) : 0,
    largestWin: wins.length > 0 ? Math.max(...wins.map((e: any) => e.realized_pnl)) : 0,
    largestLoss: losses.length > 0 ? Math.min(...losses.map((e: any) => e.realized_pnl)) : 0,
  };
}

function generateEquityCurve(executions: any[]) {
  const sorted = [...executions]
    .filter((e: any) => {
      // Filter out entries with invalid timestamps or null P&L
      if (e.realized_pnl === null || e.realized_pnl === undefined) return false;
      if (!e.executed_at) return false;
      const timestamp = new Date(e.executed_at).getTime();
      return !isNaN(timestamp) && timestamp > 0;
    })
    .sort((a, b) => new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime());

  // Return empty array if no valid data
  if (sorted.length === 0) {
    return [];
  }

  let cumulative = 0;
  return sorted.map((e: any) => {
    cumulative += e.realized_pnl || 0;
    return {
      time: Math.floor(new Date(e.executed_at).getTime() / 1000) as UTCTimestamp,
      value: cumulative,
    };
  });
}
