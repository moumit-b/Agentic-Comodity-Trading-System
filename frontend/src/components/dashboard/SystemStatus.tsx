'use client';

import { useState, useEffect } from 'react';
import { Database, Radio, TrendingUp, AlertTriangle, Power } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatTime, cn } from '@/lib/utils';
import type { AccountStatus } from '@/types';

export function SystemStatus() {
  const { isConnected, on, off } = useWebSocket();
  const { data: account, refetch } = useApi<AccountStatus>(() => apiClient.getAccount(), 5000);
  const [showKillSwitchModal, setShowKillSwitchModal] = useState(false);
  const [mode, setMode] = useState('ADVISORY');

  useEffect(() => {
    on('account_update', (data) => {
      refetch();
    });

    on('market_status', (data) => {
      refetch();
    });

    return () => {
      off('account_update');
      off('market_status');
    };
  }, [on, off, refetch]);

  const handleKillSwitch = async () => {
    try {
      await apiClient.managekillSwitch('activate', 'User requested emergency stop');
      setShowKillSwitchModal(false);
    } catch (error) {
      console.error('Failed to activate kill switch:', error);
    }
  };

  const systemHealth = [
    { name: 'Database', icon: Database, status: true },
    { name: 'WebSocket', icon: Radio, status: isConnected },
    { name: 'Market', icon: TrendingUp, status: account?.market_open || false },
    { name: 'Alpaca', icon: AlertTriangle, status: account ? true : false },
  ];

  const modeColors = {
    ADVISORY: 'text-text-secondary',
    PAPER_AUTO: 'text-accent-purple',
    LIVE_CONFIRM: 'text-accent-purple',
    LIVE_AUTO: 'text-loss',
  };

  return (
    <div className="glass-card p-4">
      <div className="grid grid-cols-4 gap-4">
        {/* System Health */}
        <div>
          <h3 className="text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-2">
            System Health
          </h3>
          <div className="space-y-1.5">
            {systemHealth.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div
                  className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    item.status ? 'bg-profit' : 'bg-loss'
                  )}
                />
                <item.icon className="w-3.5 h-3.5 text-text-secondary" strokeWidth={1.5} />
                <span className="text-xs text-text-secondary">{item.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Automation Mode */}
        <div>
          <h3 className="text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-2">
            Mode
          </h3>
          <div className="border border-border rounded-lg p-2 border-l-2 border-l-accent-purple">
            <p className={cn('text-sm font-mono font-semibold tabular-nums', modeColors[mode as keyof typeof modeColors])}>
              {mode}
            </p>
            <p className="text-[11px] text-text-secondary mt-0.5">Automation Level</p>
          </div>
        </div>

        {/* Account Balance */}
        <div>
          <h3 className="text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-2">
            Account
          </h3>
          <div className="space-y-1">
            <div>
              <p className="text-[11px] text-text-secondary">Balance</p>
              <p className="text-base font-mono font-semibold tabular-nums text-text-primary">
                {account ? formatCurrency(account.balance) : '---'}
              </p>
            </div>
            <div>
              <p className="text-[11px] text-text-secondary">Buying Power</p>
              <p className="text-sm font-mono tabular-nums text-text-secondary">
                {account ? formatCurrency(account.buying_power) : '---'}
              </p>
            </div>
          </div>
        </div>

        {/* Kill Switch */}
        <div>
          <h3 className="text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-2">
            Emergency
          </h3>
          <button
            onClick={() => setShowKillSwitchModal(true)}
            className="w-full border border-loss/30 rounded-lg p-2 hover:border-loss hover:bg-loss/5 transition-all duration-200 group"
          >
            <Power className="w-5 h-5 text-loss mx-auto mb-1 group-hover:scale-110 transition-transform" strokeWidth={1.5} />
            <p className="text-xs font-medium text-loss">KILL SWITCH</p>
          </button>
          {account && (
            <p className="text-[11px] text-text-secondary text-center mt-1.5">
              {formatTime(account.timestamp)}
            </p>
          )}
        </div>
      </div>

      {/* Kill Switch Confirmation Modal */}
      {showKillSwitchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
          <div className="glass-card p-6 max-w-md w-full m-4 border-loss/50">
            <AlertTriangle className="w-10 h-10 text-loss mx-auto mb-3" strokeWidth={1.5} />
            <h3 className="text-lg font-semibold text-center mb-2">
              CONFIRM KILL SWITCH
            </h3>
            <p className="text-sm text-text-secondary text-center mb-6">
              This will immediately halt all trading activity and cancel pending orders.
              This action requires manual clearance to resume.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowKillSwitchModal(false)}
                className="flex-1 border border-border rounded-lg p-2.5 hover:bg-surface-hover transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleKillSwitch}
                className="flex-1 bg-loss hover:bg-loss/80 rounded-lg p-2.5 transition-colors text-sm font-semibold"
              >
                ACTIVATE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
