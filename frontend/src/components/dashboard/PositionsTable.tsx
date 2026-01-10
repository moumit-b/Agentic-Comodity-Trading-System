'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatPercent, formatDateTime, cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react';
import type { Position } from '@/types';

export function PositionsTable() {
  const { on, off } = useWebSocket();
  const { data: positions, refetch } = useApi<Position[]>(() => apiClient.getPositions(), 5000);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    on('position_update', (data) => {
      refetch();
    });

    return () => {
      off('position_update');
    };
  }, [on, off, refetch]);

  if (!positions || positions.length === 0) {
    return (
      <div className="glass-card p-6">
        <h2 className="text-lg font-display font-medium mb-4">Open Positions</h2>
        <div className="text-center py-12 text-text-secondary">
          <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No open positions</p>
        </div>
      </div>
    );
  }

  const totalPnL = positions.reduce((sum, pos) => sum + Number(pos.unrealized_pnl), 0);
  const avgPnLPct = positions.reduce((sum, pos) => sum + Number(pos.unrealized_pnl_pct), 0) / positions.length;

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-display font-medium">Open Positions</h2>
        <div className="flex items-center space-x-6">
          <div>
            <p className="text-xs text-text-secondary">Positions</p>
            <p className="text-base font-mono font-medium">{positions.length}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Total P&L</p>
            <p className={cn('text-base font-mono font-medium', totalPnL >= 0 ? 'text-profit' : 'text-loss')}>
              {formatCurrency(totalPnL)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Avg P&L %</p>
            <p className={cn('text-base font-mono font-medium', avgPnLPct >= 0 ? 'text-profit' : 'text-loss')}>
              {formatPercent(avgPnLPct)}
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border">
              <th className="text-left text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Symbol
              </th>
              <th className="text-left text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Side
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Qty
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Entry
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Current
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                P&L ($)
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                P&L (%)
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Stop
              </th>
              <th className="text-right text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">
                Target
              </th>
              <th className="text-center text-xs font-display font-semibold text-text-secondary uppercase tracking-wider py-3 px-4">

              </th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position, index) => {
              const isExpanded = expandedRow === position.id;
              const pnl = Number(position.unrealized_pnl);
              const pnlPct = Number(position.unrealized_pnl_pct);

              return (
                <>
                  <tr
                    key={position.id}
                    className={cn(
                      'border-b border/30 hover:bg-white/5 transition-colors cursor-pointer',
                      index % 2 === 0 ? 'bg-white/[0.02]' : ''
                    )}
                    onClick={() => setExpandedRow(isExpanded ? null : position.id)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        {position.side === 'LONG' ? (
                          <TrendingUp className="w-4 h-4 text-profit" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-loss" />
                        )}
                        <span className="font-mono font-medium">{position.symbol}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          'px-2 py-1 rounded text-xs font-mono font-semibold',
                          position.side === 'LONG' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'
                        )}
                      >
                        {position.side}
                      </span>
                    </td>
                    <td className="text-right font-mono py-3 px-4">{position.qty}</td>
                    <td className="text-right font-mono py-3 px-4">{formatCurrency(position.entry_price)}</td>
                    <td className="text-right font-mono py-3 px-4">{formatCurrency(position.current_price)}</td>
                    <td className={cn('text-right font-mono font-medium py-3 px-4', pnl >= 0 ? 'text-profit' : 'text-loss')}>
                      {formatCurrency(pnl)}
                    </td>
                    <td className={cn('text-right font-mono font-medium py-3 px-4', pnlPct >= 0 ? 'text-profit' : 'text-loss')}>
                      {formatPercent(pnlPct)}
                    </td>
                    <td className="text-right font-mono py-3 px-4">
                      {position.stop_loss ? formatCurrency(position.stop_loss) : '---'}
                    </td>
                    <td className="text-right font-mono py-3 px-4">
                      {position.take_profit ? formatCurrency(position.take_profit) : '---'}
                    </td>
                    <td className="text-center py-3 px-4">
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-text-secondary mx-auto" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-text-secondary mx-auto" />
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={10} className="bg-white/[0.02] border-b border/30">
                        <div className="p-4 grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-xs text-text-secondary mb-1">Position Value</p>
                            <p className="font-mono font-medium">
                              {formatCurrency(position.qty * position.current_price)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-text-secondary mb-1">Opened At</p>
                            <p className="font-mono">{formatDateTime(position.opened_at)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-text-secondary mb-1">Risk:Reward</p>
                            <p className="font-mono">
                              {position.stop_loss && position.take_profit
                                ? `1:${((position.take_profit - position.entry_price) / (position.entry_price - position.stop_loss)).toFixed(2)}`
                                : '---'}
                            </p>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
