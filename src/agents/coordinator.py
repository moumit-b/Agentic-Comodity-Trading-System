"""Coordinator Agent - orchestrates the entire trading workflow."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from src.agents.execution_agent import ExecutionAgent, ExecutionDecision
from src.agents.risk_manager import RiskManagerAgent
from src.agents.settlement_tracker import SettlementTrackerAgent
from src.agents.strategy_pool import StrategyPoolAgent
from src.agents.strategy_selector import StrategySelectorAgent
from src.core.config import TradingConfig
from src.services.circuit_breakers import CircuitBreakerService
from src.services.discord_notifier import DiscordNotifier
from src.strategies import Signal

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """Complete trade decision with all agent outputs."""

    approved: bool
    signal: Signal | None
    rejection_reason: str
    execution_result: dict | None
    risk_decision: dict | None
    breaker_status: dict | None
    settlement_status: dict | None


class CoordinatorAgent:
    """
    Master coordinator that orchestrates the entire trading workflow.

    Workflow:
    1. Market regime detection → Strategy selection
    2. Strategy execution → Signal generation
    3. Signal filtering and ranking
    4. Risk validation
    5. Settlement check (T+1 compliance)
    6. Circuit breaker check
    7. Execution (if approved)
    8. Notifications
    """

    def __init__(
        self,
        config: TradingConfig,
        strategy_selector: StrategySelectorAgent,
        strategy_pool: StrategyPoolAgent,
        risk_manager: RiskManagerAgent,
        settlement_tracker: SettlementTrackerAgent,
        circuit_breakers: CircuitBreakerService,
        execution_agent: ExecutionAgent,
        notifier: DiscordNotifier | None = None,
    ):
        """
        Initialize Coordinator Agent.

        Args:
            config: Trading configuration
            strategy_selector: Strategy selection agent
            strategy_pool: Strategy pool agent
            risk_manager: Risk management agent
            settlement_tracker: Settlement tracking agent
            circuit_breakers: Circuit breaker service
            execution_agent: Execution agent
            notifier: Discord notifier (optional)
        """
        self.config = config
        self.strategy_selector = strategy_selector
        self.strategy_pool = strategy_pool
        self.risk_manager = risk_manager
        self.settlement_tracker = settlement_tracker
        self.circuit_breakers = circuit_breakers
        self.execution_agent = execution_agent
        self.notifier = notifier

        logger.info("Coordinator Agent initialized")

    async def run_trading_cycle(
        self,
        market_data: dict,
        account_balance: Decimal,
        current_positions: int,
        daily_trades_count: int,
        consecutive_losses: int,
        daily_pnl_pct: Decimal,
    ) -> TradeDecision:
        """
        Run complete trading cycle.

        Args:
            market_data: Market data (bars, indicators, etc.)
            account_balance: Current account balance
            current_positions: Number of open positions
            daily_trades_count: Trades executed today
            consecutive_losses: Consecutive losing trades
            daily_pnl_pct: Daily P&L as percentage

        Returns:
            TradeDecision with approval status and details
        """
        logger.info("=" * 60)
        logger.info("Starting trading cycle")
        logger.info("=" * 60)

        # === STEP 1: Check Circuit Breakers ===
        portfolio_risk = await self.risk_manager.calculate_portfolio_heat(account_balance)

        breaker_status = await self.circuit_breakers.check_all_breakers(
            daily_pnl_pct=daily_pnl_pct,
            consecutive_losses=consecutive_losses,
            portfolio_heat=portfolio_risk.current_heat,
        )

        if breaker_status.is_tripped:
            logger.warning(f"Circuit breakers tripped: {breaker_status.reasons}")
            if self.notifier:
                for breaker_type, reason in zip(
                    breaker_status.active_breakers, breaker_status.reasons
                ):
                    await self.notifier.notify_circuit_breaker(
                        breaker_type=breaker_type.value,
                        reason=reason,
                        active_count=len(breaker_status.active_breakers),
                    )

            return TradeDecision(
                approved=False,
                signal=None,
                rejection_reason=f"Circuit breaker: {', '.join(breaker_status.reasons)}",
                execution_result=None,
                risk_decision=None,
                breaker_status={
                    "is_tripped": breaker_status.is_tripped,
                    "active_breakers": [b.value for b in breaker_status.active_breakers],
                    "reasons": breaker_status.reasons,
                },
                settlement_status=None,
            )

        logger.info("✓ Circuit breakers clear")

        # === STEP 2: Extract Market Data ===
        try:
            import pandas as pd
            import pandas_ta as ta

            from src.strategies import IndicatorSet

            symbol = market_data.get("symbol", "USO")
            bars_dict = market_data.get("bars", {})

            # Convert Alpaca bars to DataFrame
            if not bars_dict or symbol not in bars_dict:
                logger.warning(f"No bar data available for {symbol}")
                return TradeDecision(
                    approved=False,
                    signal=None,
                    rejection_reason="No market data available",
                    execution_result=None,
                    risk_decision=None,
                    breaker_status=None,
                    settlement_status=None,
                )

            bars_list = bars_dict[symbol]
            if not bars_list:
                logger.warning(f"Empty bars list for {symbol}")
                return TradeDecision(
                    approved=False,
                    signal=None,
                    rejection_reason="Empty market data",
                    execution_result=None,
                    risk_decision=None,
                    breaker_status=None,
                    settlement_status=None,
                )

            # Convert to DataFrame
            bars_data = []
            for bar in bars_list:
                bars_data.append(
                    {
                        "timestamp": bar.timestamp,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": int(bar.volume),
                    }
                )

            bars = pd.DataFrame(bars_data)
            bars.set_index("timestamp", inplace=True)

            logger.info(f"Processing {len(bars)} bars for {symbol}")

            # === STEP 3: Calculate Indicators ===
            if len(bars) < 50:
                logger.warning(f"Insufficient bars ({len(bars)}) for analysis, need at least 50")
                return TradeDecision(
                    approved=False,
                    signal=None,
                    rejection_reason="Insufficient market data (need 50+ bars)",
                    execution_result=None,
                    risk_decision=None,
                    breaker_status=None,
                    settlement_status=None,
                )

            # Calculate indicators for multiple timeframes
            indicators = {}
            timeframes = ["5m", "15m", "1h"]

            for tf in timeframes:
                # Resample logic
                rule = tf.replace("m", "min").replace("h", "H")
                
                # Ensure index is datetime
                if not isinstance(bars.index, pd.DatetimeIndex):
                    bars.index = pd.to_datetime(bars.index)

                resampled = bars.resample(rule).agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum"
                }).dropna()

                if len(resampled) < 20:
                    continue

                # Calculate indicators
                df = resampled.copy()
                df["sma_20"] = ta.sma(df["close"], length=20)
                df["ema_20"] = ta.ema(df["close"], length=20)
                df["rsi"] = ta.rsi(df["close"], length=14)
                df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

                macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
                if macd is not None:
                    df["macd"] = macd["MACD_12_26_9"]
                    df["macd_signal"] = macd["MACDs_12_26_9"]
                    df["macd_histogram"] = macd["MACDh_12_26_9"]

                bbands = ta.bbands(df["close"], length=20, std=2)
                if bbands is not None and not bbands.empty:
                    # Dynamically find columns to handle naming variations
                    # e.g., BBU_20_2.0 vs BBU_20_2
                    upper_col = next((c for c in bbands.columns if c.startswith("BBU")), None)
                    mid_col = next((c for c in bbands.columns if c.startswith("BBM")), None)
                    lower_col = next((c for c in bbands.columns if c.startswith("BBL")), None)
                    
                    if upper_col and mid_col and lower_col:
                        df["bb_upper"] = bbands[upper_col]
                        df["bb_middle"] = bbands[mid_col]
                        df["bb_lower"] = bbands[lower_col]

                latest = df.iloc[-1]
                
                indicators[tf] = IndicatorSet(
                    timeframe=tf,
                    sma_20=float(latest["sma_20"]) if pd.notna(latest["sma_20"]) else None,
                    ema_20=float(latest["ema_20"]) if pd.notna(latest["ema_20"]) else None,
                    rsi=float(latest["rsi"]) if pd.notna(latest["rsi"]) else None,
                    atr=float(latest["atr"]) if pd.notna(latest["atr"]) else None,
                    macd=float(latest.get("macd", 0)) if pd.notna(latest.get("macd")) else None,
                    macd_signal=float(latest.get("macd_signal", 0)) if pd.notna(latest.get("macd_signal")) else None,
                    macd_histogram=float(latest.get("macd_histogram", 0)) if pd.notna(latest.get("macd_histogram")) else None,
                    bb_upper=float(latest.get("bb_upper", 0)) if pd.notna(latest.get("bb_upper")) else None,
                    bb_middle=float(latest.get("bb_middle", 0)) if pd.notna(latest.get("bb_middle")) else None,
                    bb_lower=float(latest.get("bb_lower", 0)) if pd.notna(latest.get("bb_lower")) else None,
                )

            if not indicators:
                logger.warning("Failed to calculate indicators for any timeframe")
                # Fallback to single timeframe (1m treated as 1h) if resampling failed, 
                # but better to return empty than wrong data. 
                # Actually, let's keep the old behavior as a fallback if dict is empty but warn.
                pass

            if "1h" in indicators:
                logger.info(
                    f"Indicators (1h): RSI={indicators['1h'].rsi:.1f}, "
                    f"SMA20={indicators['1h'].sma_20:.2f}"
                )
            
            # Log other timeframes for debugging
            for tf, ind in indicators.items():
                if tf != "1h":
                    logger.info(f"Indicators ({tf}): RSI={ind.rsi:.1f}, Close={bars['close'].iloc[-1]:.2f}")

            # === STEP 4: Detect Market Regime ===
            market_regime = self.strategy_selector.detect_market_regime(bars, indicators)
            logger.info(f"Market regime: {market_regime.value}")

            # === STEP 5: Execute Strategies ===
            logger.info("Executing strategies...")
            signals = self.strategy_pool.execute_all_strategies(
                symbol=symbol, bars=bars, indicators=indicators, market_regime=market_regime
            )

            if not signals:
                logger.info("No signals generated by strategies")
                return TradeDecision(
                    approved=False,
                    signal=None,
                    rejection_reason="No signals generated",
                    execution_result=None,
                    risk_decision=None,
                    breaker_status=None,
                    settlement_status=None,
                )

            logger.info(f"Generated {len(signals)} signal(s)")

            # === STEP 6: Rank and Select Best Signal ===
            ranked_signals = self.strategy_pool.rank_signals(signals)
            best_signal = ranked_signals[0]

            logger.info(
                f"Best signal: {best_signal.strategy_name} - {best_signal.direction.value} "
                f"(strength={best_signal.signal_strength}, confidence={best_signal.confidence})"
            )

            # === STEP 7: Evaluate Signal Through Risk Pipeline ===
            trade_decision = await self.evaluate_signal(
                signal=best_signal,
                account_balance=account_balance,
                current_positions=current_positions,
                daily_trades_count=daily_trades_count,
                consecutive_losses=consecutive_losses,
            )

            return trade_decision

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            return TradeDecision(
                approved=False,
                signal=None,
                rejection_reason=f"Trading cycle error: {str(e)}",
                execution_result=None,
                risk_decision=None,
                breaker_status=None,
                settlement_status=None,
            )

    async def evaluate_signal(
        self,
        signal: Signal,
        account_balance: Decimal,
        current_positions: int,
        daily_trades_count: int,
        consecutive_losses: int,
    ) -> TradeDecision:
        """
        Evaluate a trading signal through complete validation pipeline.

        Args:
            signal: Trading signal to evaluate
            account_balance: Current account balance
            current_positions: Number of open positions
            daily_trades_count: Trades executed today
            consecutive_losses: Consecutive losing trades

        Returns:
            TradeDecision with approval status
        """
        logger.info(f"Evaluating signal: {signal.direction.value} {signal.symbol}")

        # === STEP 1: Circuit Breaker Check ===
        portfolio_risk = await self.risk_manager.calculate_portfolio_heat(account_balance)

        breaker_status = await self.circuit_breakers.check_all_breakers(
            daily_pnl_pct=Decimal("0.0"),  # TODO: Get from account
            consecutive_losses=consecutive_losses,
            portfolio_heat=portfolio_risk.current_heat,
        )

        if breaker_status.is_tripped:
            logger.warning(f"Signal rejected by circuit breakers: {breaker_status.reasons}")
            return TradeDecision(
                approved=False,
                signal=signal,
                rejection_reason=f"Circuit breaker: {', '.join(breaker_status.reasons)}",
                execution_result=None,
                risk_decision=None,
                breaker_status={
                    "is_tripped": True,
                    "reasons": breaker_status.reasons,
                },
                settlement_status=None,
            )

        # === STEP 2: Settlement Check ===
        settlement_status = await self.settlement_tracker.get_settlement_status(
            total_cash=account_balance
        )

        logger.info(
            f"Settlement: ${settlement_status.total_settled:.2f} settled, "
            f"${settlement_status.total_pending:.2f} pending"
        )

        # === STEP 3: Risk Validation ===
        risk_decision = await self.risk_manager.evaluate_trade(
            signal=signal,
            account_balance=account_balance,
            settled_cash=settlement_status.available_to_trade,
            current_positions=current_positions,
            portfolio_heat=portfolio_risk.current_heat,
            daily_trades_count=daily_trades_count,
            consecutive_losses=consecutive_losses,
        )

        if not risk_decision.approved:
            logger.warning(f"Signal rejected by risk manager: {risk_decision.reason}")

            # Notify about rejection
            if self.notifier:
                failed_checks = [
                    check for check, passed in risk_decision.passed_checks.items() if not passed
                ]
                await self.notifier.notify_risk_rejection(
                    symbol=signal.symbol,
                    reason=risk_decision.reason,
                    failed_checks=failed_checks,
                )

            return TradeDecision(
                approved=False,
                signal=signal,
                rejection_reason=f"Risk check failed: {risk_decision.reason}",
                execution_result=None,
                risk_decision={
                    "approved": False,
                    "reason": risk_decision.reason,
                    "passed_checks": risk_decision.passed_checks,
                },
                breaker_status=None,
                settlement_status={
                    "total_settled": str(settlement_status.total_settled),
                    "available": str(settlement_status.available_to_trade),
                },
            )

        logger.info(
            f"✓ Risk approved: {risk_decision.position_size} shares, "
            f"${risk_decision.risk_amount:.2f} at risk ({risk_decision.risk_pct:.2%})"
        )

        # === STEP 4: Execute Trade ===
        execution_result = await self.execution_agent.execute_signal(
            signal=signal,
            position_size=risk_decision.position_size,
            account_balance=account_balance,
        )

        logger.info(f"Execution: {execution_result.decision.value} - {execution_result.message}")

        # === STEP 5: Send Notifications ===
        if self.notifier:
            # Notify signal generation
            await self.notifier.notify_signal_generated(
                symbol=signal.symbol,
                direction=signal.direction.value,
                strategy=signal.strategy_name,
                confidence=signal.confidence,
                entry=signal.suggested_entry,
                stop=signal.suggested_stop,
                target=signal.suggested_target,
            )

            # Notify execution if approved
            if execution_result.decision == ExecutionDecision.EXECUTE:
                await self.notifier.notify_trade_execution(
                    symbol=signal.symbol,
                    side=signal.direction.value,
                    qty=risk_decision.position_size,
                    price=signal.suggested_entry,
                    order_id=execution_result.order_id,
                    is_paper=execution_result.metadata.get("is_paper", False),
                )
            elif execution_result.requires_confirmation:
                await self.notifier.notify_confirmation_required(
                    symbol=signal.symbol,
                    direction=signal.direction.value,
                    qty=risk_decision.position_size,
                    entry=signal.suggested_entry,
                    stop=signal.suggested_stop,
                    target=signal.suggested_target,
                    order_id=execution_result.order_id,
                )

        # === Return Decision ===
        return TradeDecision(
            approved=execution_result.decision
            in [
                ExecutionDecision.EXECUTE,
                ExecutionDecision.REQUEST_CONFIRMATION,
            ],
            signal=signal,
            rejection_reason=""
            if execution_result.decision == ExecutionDecision.EXECUTE
            else execution_result.message,
            execution_result={
                "decision": execution_result.decision.value,
                "order_id": execution_result.order_id,
                "message": execution_result.message,
                "requires_confirmation": execution_result.requires_confirmation,
            },
            risk_decision={
                "approved": True,
                "position_size": str(risk_decision.position_size),
                "risk_amount": str(risk_decision.risk_amount),
                "risk_pct": str(risk_decision.risk_pct),
            },
            breaker_status={"is_tripped": False},
            settlement_status={
                "total_settled": str(settlement_status.total_settled),
                "available": str(settlement_status.available_to_trade),
            },
        )

    async def shutdown(self):
        """
        Graceful shutdown.

        Note: In production, this would:
        - Cancel all pending orders via Alpaca API
        - Close end-of-day positions if configured
        - Send shutdown notification with summary
        """
        logger.info("Coordinator shutdown initiated")

        # Send notification if available
        if self.notifier:
            try:
                await self.notifier.send_message(
                    message="🛑 Trading system shutdown initiated",
                    title="System Shutdown"
                )
            except Exception as e:
                logger.error(f"Failed to send shutdown notification: {e}")

        logger.info("Coordinator shutdown complete")
