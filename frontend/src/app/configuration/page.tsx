'use client';

import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { Settings, Shield, DollarSign, TrendingUp, Activity, AlertTriangle } from 'lucide-react';

export default function ConfigurationPage() {
  const { data: config } = useApi(() => apiClient.getConfiguration(), 60000);

  if (!config) {
    return (
      <div className="p-6 flex items-center justify-center h-screen">
        <div className="text-terminal-text-secondary">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center space-x-3">
        <Settings className="w-8 h-8 text-accent-purple" />
        <h1 className="text-3xl font-medium text-accent-purple tracking-tight">System Configuration</h1>
      </div>

      {/* Trading Parameters */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-6">
          <Activity className="w-5 h-5 text-accent-cyan" />
          <h2 className="text-lg font-medium text-accent-cyan">Trading Parameters</h2>
        </div>
        <div className="grid grid-cols-3 gap-6">
          <ConfigItem
            label="Automation Mode"
            value={config.automation_mode || 'ADVISORY'}
            description="Current trading automation level"
          />
          <ConfigItem
            label="Max Positions"
            value={config.max_positions || 5}
            description="Maximum concurrent positions"
          />
          <ConfigItem
            label="Max Daily Trades"
            value={config.max_daily_trades || 10}
            description="Trade limit per day"
          />
          <ConfigItem
            label="Default Position Size"
            value={formatPercent((config.default_position_size || 0.1))}
            description="% of portfolio per position"
          />
          <ConfigItem
            label="Min Confidence"
            value={formatPercent((config.min_signal_confidence || 0.7))}
            description="Minimum signal confidence threshold"
          />
          <ConfigItem
            label="Trading Hours"
            value={`${config.trading_start || '09:30'} - ${config.trading_end || '16:00'}`}
            description="Active trading window"
          />
        </div>
      </div>

      {/* Risk Management */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-6">
          <Shield className="w-5 h-5 text-profit" />
          <h2 className="text-lg font-medium text-profit">Risk Management</h2>
        </div>
        <div className="grid grid-cols-3 gap-6">
          <ConfigItem
            label="Max Daily Loss"
            value={formatCurrency(config.max_daily_loss || -500)}
            description="Daily loss limit (circuit breaker)"
            valueClass="text-loss"
          />
          <ConfigItem
            label="Max Portfolio Heat"
            value={formatPercent((config.max_portfolio_heat || 0.5))}
            description="Maximum risk exposure"
            valueClass="text-warning"
          />
          <ConfigItem
            label="Max Position Heat"
            value={formatPercent((config.max_position_heat || 0.15))}
            description="Risk per position"
            valueClass="text-warning"
          />
          <ConfigItem
            label="Stop Loss %"
            value={formatPercent((config.default_stop_loss_pct || 0.02))}
            description="Default stop loss distance"
            valueClass="text-loss"
          />
          <ConfigItem
            label="Take Profit %"
            value={formatPercent((config.default_take_profit_pct || 0.04))}
            description="Default take profit distance"
            valueClass="text-profit"
          />
          <ConfigItem
            label="Consecutive Loss Limit"
            value={config.max_consecutive_losses || 3}
            description="Max losses before pause"
            valueClass="text-loss"
          />
        </div>
      </div>

      {/* Strategy Configuration */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-6">
          <TrendingUp className="w-5 h-5 text-accent-purple" />
          <h2 className="text-xl font-bold text-accent-purple">Strategy Settings</h2>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-sm text-terminal-text-secondary">Enabled Strategies</h3>
            {(config.enabled_strategies || ['MeanReversion', 'TrendFollowing', 'Breakout']).map((strategy: string) => (
              <div key={strategy} className="flex items-center justify-between p-3 bg-terminal-bg rounded border border-terminal-border">
                <span className="font-mono">{strategy}</span>
                <span className="text-xs text-profit">ACTIVE</span>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold text-sm text-terminal-text-secondary">Indicators</h3>
            {(config.indicators || ['RSI', 'MACD', 'Bollinger Bands', 'SMA', 'EMA']).map((indicator: string) => (
              <div key={indicator} className="flex items-center justify-between p-3 bg-terminal-bg rounded border border-terminal-border">
                <span className="font-mono">{indicator}</span>
                <span className="text-xs text-accent-cyan">ENABLED</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Circuit Breakers */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-6">
          <AlertTriangle className="w-5 h-5 text-warning" />
          <h2 className="text-xl font-bold text-warning">Circuit Breakers</h2>
        </div>
        <div className="space-y-3">
          <CircuitBreakerItem
            name="DAILY_LOSS_LIMIT"
            threshold={formatCurrency(config.max_daily_loss || -500)}
            enabled={true}
          />
          <CircuitBreakerItem
            name="CONSECUTIVE_LOSSES"
            threshold={`${config.max_consecutive_losses || 3} losses`}
            enabled={true}
          />
          <CircuitBreakerItem
            name="MAX_POSITIONS"
            threshold={`${config.max_positions || 5} positions`}
            enabled={true}
          />
          <CircuitBreakerItem
            name="MAX_DAILY_TRADES"
            threshold={`${config.max_daily_trades || 10} trades`}
            enabled={true}
          />
          <CircuitBreakerItem
            name="PORTFOLIO_HEAT"
            threshold={formatPercent(config.max_portfolio_heat || 0.5)}
            enabled={true}
          />
          <CircuitBreakerItem
            name="VOLATILITY_SPIKE"
            threshold="2x avg volatility"
            enabled={config.volatility_protection !== false}
          />
          <CircuitBreakerItem
            name="MANUAL_KILL_SWITCH"
            threshold="User activated"
            enabled={true}
          />
        </div>
      </div>

      {/* API Configuration */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-6">
          <DollarSign className="w-5 h-5 text-accent-cyan" />
          <h2 className="text-xl font-bold text-accent-cyan">API Configuration</h2>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <ConfigItem
            label="Broker"
            value="Alpaca"
            description="Trading API provider"
          />
          <ConfigItem
            label="Market Data"
            value="Alpaca + IEX"
            description="Market data sources"
          />
          <ConfigItem
            label="Database"
            value="PostgreSQL"
            description="Primary data store"
          />
          <ConfigItem
            label="Cache"
            value="Redis"
            description="In-memory cache"
          />
        </div>
      </div>
    </div>
  );
}

function ConfigItem({
  label,
  value,
  description,
  valueClass = 'text-white'
}: {
  label: string;
  value: string | number;
  description: string;
  valueClass?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="text-xs text-terminal-text-secondary">{label}</div>
      <div className={`text-xl font-bold font-mono ${valueClass}`}>{value}</div>
      <div className="text-xs text-terminal-text-secondary">{description}</div>
    </div>
  );
}

function CircuitBreakerItem({
  name,
  threshold,
  enabled
}: {
  name: string;
  threshold: string;
  enabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-terminal-bg rounded border border-terminal-border">
      <div>
        <div className="font-mono font-semibold">{name}</div>
        <div className="text-sm text-terminal-text-secondary mt-1">Threshold: {threshold}</div>
      </div>
      <div className={`px-3 py-1 rounded text-xs font-semibold ${
        enabled ? 'bg-profit/20 text-profit' : 'bg-terminal-border text-terminal-text-secondary'
      }`}>
        {enabled ? 'ENABLED' : 'DISABLED'}
      </div>
    </div>
  );
}
