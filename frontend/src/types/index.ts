export interface AccountStatus {
  balance: number;
  buying_power: number;
  cash: number;
  portfolio_value: number;
  market_open: boolean;
  timestamp: string;
}

export interface Position {
  id: number;
  symbol: string;
  side: 'LONG' | 'SHORT';
  qty: number;
  entry_price: number;
  current_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  opened_at: string;
}

export interface Signal {
  id: number;
  timestamp: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  strategy_name: string;
  timeframe: string;
  confidence: number;
  signal_strength: number;
  suggested_entry: number;
  suggested_stop: number;
  suggested_target: number;
  decision?: 'APPROVED' | 'REJECTED' | 'PENDING';
  decision_reason?: string;
}

export interface Execution {
  id: number;
  timestamp: string;
  symbol: string;
  side: string;
  qty: number;
  filled_price: number | null;
  status: string;
  requires_confirmation: boolean;
  alpaca_order_id: string | null;
}

export interface CircuitBreaker {
  breaker_type: string;
  is_active: boolean;
  triggered_at: string | null;
  cleared_at: string | null;
  reason: string | null;
}

export interface RiskMetrics {
  portfolio_heat_pct: number;
  daily_pnl_pct: number;
  current_rsi: number;
  daily_target_pct: number;
  daily_limit_pct: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
}

export interface Bar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Indicator {
  timestamp: string;
  sma_20?: number;
  ema_20?: number;
  rsi?: number;
  atr?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
}
