'use client';

import { useState, useEffect } from 'react';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';
import { Clock, TrendingUp, TrendingDown, CheckCircle, XCircle } from 'lucide-react';
import type { Execution } from '@/types';

export function OrderConfirmation() {
  const { data: pendingExecutions, refetch } = useApi<Execution[]>(
    () => apiClient.getPendingConfirmations(),
    3000
  );
  const [countdown, setCountdown] = useState<Record<number, number>>({});

  useEffect(() => {
    if (!pendingExecutions) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        const updated = { ...prev };
        pendingExecutions.forEach((exec) => {
          if (!(exec.id in updated)) {
            updated[exec.id] = 30;
          } else if (updated[exec.id] > 0) {
            updated[exec.id] -= 1;
          }
        });
        return updated;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [pendingExecutions]);

  const handleConfirm = async (executionId: number, action: 'approve' | 'reject') => {
    try {
      await apiClient.confirmExecution(executionId, action);
      refetch();
    } catch (error) {
      console.error('Failed to confirm execution:', error);
    }
  };

  if (!pendingExecutions || pendingExecutions.length === 0) {
    return null;
  }

  return (
    <div className="glass-card p-6">
      <h2 className="text-base font-medium mb-4 text-accent-purple">Pending Confirmations</h2>
      <div className="space-y-4">
        {pendingExecutions.map((execution) => {
          const timeLeft = countdown[execution.id] || 30;
          const isExpiring = timeLeft <= 10;

          return (
            <div
              key={execution.id}
              className={cn(
                'p-4 border rounded-lg bg-terminal-bg',
                isExpiring ? 'border-loss animate-pulse' : 'border-accent-purple/30'
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  {execution.side === 'LONG' ? (
                    <div className="p-2 rounded-lg bg-profit/20">
                      <TrendingUp className="w-6 h-6 text-profit" />
                    </div>
                  ) : (
                    <div className="p-2 rounded-lg bg-loss/20">
                      <TrendingDown className="w-6 h-6 text-loss" />
                    </div>
                  )}
                  <div>
                    <p className="font-mono font-medium text-lg">{execution.symbol}</p>
                    <p className="text-sm text-terminal-text-secondary">
                      {execution.side} • {execution.qty} shares
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center space-x-2">
                    <Clock className={cn('w-4 h-4', isExpiring ? 'text-loss animate-pulse' : 'text-terminal-text-secondary')} />
                    <span className={cn('font-mono font-medium', isExpiring ? 'text-loss' : 'text-accent-cyan')}>
                      {timeLeft}s
                    </span>
                  </div>
                </div>
              </div>

              {/* Price Info */}
              <div className="glass-card p-3 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-terminal-text-secondary">Entry Price</span>
                  <span className="font-mono font-medium text-base">
                    {execution.filled_price ? formatCurrency(execution.filled_price) : 'Market'}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleConfirm(execution.id, 'reject')}
                  className="glass-card p-4 border-loss/30 hover:bg-loss/10 hover:border-loss transition-all duration-200 group"
                >
                  <XCircle className="w-6 h-6 text-loss mx-auto mb-2 group-hover:scale-110 transition-transform" />
                  <p className="text-sm font-display font-medium text-loss">REJECT</p>
                </button>
                <button
                  onClick={() => handleConfirm(execution.id, 'approve')}
                  className="glass-card p-4 border-profit/30 hover:bg-profit/10 hover:border-profit transition-all duration-200 group"
                >
                  <CheckCircle className="w-6 h-6 text-profit mx-auto mb-2 group-hover:scale-110 transition-transform" />
                  <p className="text-sm font-display font-medium text-profit">APPROVE</p>
                </button>
              </div>

              {/* Warning */}
              {isExpiring && (
                <p className="text-xs text-loss text-center mt-3 animate-pulse">
                  Expiring soon! Take action now.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
