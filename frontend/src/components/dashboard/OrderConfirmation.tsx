'use client';

import { useState, useEffect, useRef } from 'react';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';
import { Clock, TrendingUp, TrendingDown, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import type { Execution } from '@/types';

export function OrderConfirmation() {
  const { data: pendingExecutions, refetch } = useApi<Execution[]>(
    () => apiClient.getPendingConfirmations(),
    3000
  );
  const [countdown, setCountdown] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Use useRef for timer to prevent recreation on every render
  useEffect(() => {
    if (!pendingExecutions || pendingExecutions.length === 0) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    // Initialize countdown for new executions
    setCountdown((prev) => {
      const updated = { ...prev };
      pendingExecutions.forEach((exec) => {
        if (!(exec.id in updated)) {
          updated[exec.id] = 30;
        }
      });
      return updated;
    });

    // Clear existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    // Start new timer
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        const updated = { ...prev };
        let hasChanges = false;

        pendingExecutions.forEach((exec) => {
          if (updated[exec.id] > 0) {
            updated[exec.id] -= 1;
            hasChanges = true;
          }
        });

        return hasChanges ? updated : prev;
      });
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [pendingExecutions]);

  const handleConfirm = async (executionId: number, action: 'approve' | 'reject') => {
    setLoading((prev) => ({ ...prev, [executionId]: true }));
    setError(null);

    try {
      await apiClient.confirmExecution(executionId, action);
      await refetch();
    } catch (error) {
      console.error('Failed to confirm execution:', error);
      setError(`Failed to ${action} execution. Please try again.`);
    } finally {
      setLoading((prev) => ({ ...prev, [executionId]: false }));
    }
  };

  if (!pendingExecutions || pendingExecutions.length === 0) {
    return null;
  }

  return (
    <div className="glass-card p-6">
      <h2 className="text-base font-medium mb-4 text-accent-purple">Pending Confirmations</h2>
      {error && (
        <div className="mb-4 p-3 bg-loss/10 border border-loss/30 rounded-lg">
          <p className="text-sm text-loss">{error}</p>
        </div>
      )}
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
                    <p className="text-sm text-text-secondary">
                      {execution.side} • {execution.qty} shares
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center space-x-2">
                    <Clock className={cn('w-4 h-4', isExpiring ? 'text-loss animate-pulse' : 'text-text-secondary')} />
                    <span className={cn('font-mono font-medium', isExpiring ? 'text-loss' : 'text-accent-cyan')}>
                      {timeLeft}s
                    </span>
                  </div>
                </div>
              </div>

              {/* Price Info */}
              <div className="glass-card p-3 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-secondary">Entry Price</span>
                  <span className="font-mono font-medium text-base">
                    {execution.filled_price ? formatCurrency(execution.filled_price) : 'Market'}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleConfirm(execution.id, 'reject')}
                  disabled={loading[execution.id]}
                  className="glass-card p-4 border-loss/30 hover:bg-loss/10 hover:border-loss transition-all duration-200 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading[execution.id] ? (
                    <Loader2 className="w-6 h-6 text-loss mx-auto mb-2 animate-spin" />
                  ) : (
                    <XCircle className="w-6 h-6 text-loss mx-auto mb-2 group-hover:scale-110 transition-transform" />
                  )}
                  <p className="text-sm font-display font-medium text-loss">
                    {loading[execution.id] ? 'PROCESSING...' : 'REJECT'}
                  </p>
                </button>
                <button
                  onClick={() => handleConfirm(execution.id, 'approve')}
                  disabled={loading[execution.id]}
                  className="glass-card p-4 border-profit/30 hover:bg-profit/10 hover:border-profit transition-all duration-200 group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading[execution.id] ? (
                    <Loader2 className="w-6 h-6 text-profit mx-auto mb-2 animate-spin" />
                  ) : (
                    <CheckCircle className="w-6 h-6 text-profit mx-auto mb-2 group-hover:scale-110 transition-transform" />
                  )}
                  <p className="text-sm font-display font-medium text-profit">
                    {loading[execution.id] ? 'PROCESSING...' : 'APPROVE'}
                  </p>
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
