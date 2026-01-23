import asyncio
import sys
import os
import logging
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

# Add current directory to path
sys.path.append(os.getcwd())

from src.core.config import TradingConfig, AlpacaConfig, DatabaseConfig, RedisConfig
from src.core.database import init_db, get_session
from src.agents.coordinator import CoordinatorAgent
from src.agents.strategy_selector import StrategySelectorAgent
from src.agents.strategy_pool import StrategyPoolAgent
from src.agents.risk_manager import RiskManagerAgent
from src.agents.settlement_tracker import SettlementTrackerAgent
from src.agents.execution_agent import ExecutionAgent
from src.services.circuit_breakers import CircuitBreakerService
from src.services.alpaca_api import AlpacaService
from src.models.bars import Bar1m
from src.models.execution import Decision
from src.models.signal import Signal as SignalModel
from sqlalchemy import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_manual_cycle():
    logger.info("Starting manual trading cycle...")
    
    # Init DB and Configs
    init_db(DatabaseConfig())
    config = TradingConfig()
    
    # Init Agents
    strategy_selector = StrategySelectorAgent(config)
    strategy_pool = StrategyPoolAgent()
    
    risk_manager = RiskManagerAgent(config)
    settlement_tracker = SettlementTrackerAgent()
    execution_agent = ExecutionAgent(config)
    circuit_breakers = CircuitBreakerService()
    
    # Mocking notifier
    coordinator = CoordinatorAgent(
        config=config,
        strategy_selector=strategy_selector,
        strategy_pool=strategy_pool,
        risk_manager=risk_manager,
        settlement_tracker=settlement_tracker,
        circuit_breakers=circuit_breakers,
        execution_agent=execution_agent,
        notifier=None 
    )
    
    symbols = config.symbols
    
    for symbol in symbols:
        logger.info(f"Analyzing {symbol}...")
        
        async with get_session() as session:
            # Get last 2000 bars
            stmt = select(Bar1m).where(Bar1m.symbol == symbol).order_by(Bar1m.timestamp.desc()).limit(2000)
            result = await session.execute(stmt)
            bars_db = result.scalars().all()
            
            if not bars_db:
                logger.warning(f"No bars in DB for {symbol}")
                continue
                
            bars_list = []
            for b in reversed(bars_db): 
                bars_list.append(SimpleNamespace(
                    timestamp=b.timestamp,
                    open=float(b.open),
                    high=float(b.high),
                    low=float(b.low),
                    close=float(b.close),
                    volume=float(b.volume)
                ))
            
            logger.info(f"Fetched {len(bars_list)} bars from DB.")
            
            market_data = {
                "symbol": symbol,
                "bars": {symbol: bars_list}
            }
            
            # Dummy account info
            account_balance = Decimal("100000") 
            
            # Run Coordinator Logic
            decision = await coordinator.run_trading_cycle(
                market_data=market_data,
                account_balance=account_balance,
                current_positions=0,
                daily_trades_count=0,
                consecutive_losses=0,
                daily_pnl_pct=Decimal("0")
            )
            
            # Persist Signal and Decision to DB
            if decision.signal:
                # 1. Save Signal
                sig_orm = SignalModel(
                    timestamp=decision.signal.timestamp,
                    symbol=decision.signal.symbol,
                    direction=decision.signal.direction.value,
                    strategy_name=decision.signal.strategy_name,
                    timeframe=decision.signal.timeframe,
                    confidence=float(decision.signal.confidence),
                    signal_strength=float(decision.signal.signal_strength),
                    suggested_entry=decision.signal.suggested_entry,
                    suggested_stop=decision.signal.suggested_stop,
                    suggested_target=decision.signal.suggested_target,
                    market_regime=decision.signal.market_regime.value if decision.signal.market_regime else "UNKNOWN",
                    reasoning=decision.signal.reasoning
                )
                session.add(sig_orm)
                await session.flush() # Get ID
                
                # 2. Save Decision
                dec_orm = Decision(
                    timestamp=datetime.now(timezone.utc),
                    signal_id=sig_orm.id,
                    decision="APPROVE" if decision.approved else "REJECT",
                    reason=decision.rejection_reason,
                    position_size=int(decision.risk_decision.get("position_size", 0)) if decision.risk_decision else None,
                    risk_amount=Decimal(decision.risk_decision.get("risk_amount", 0)) if decision.risk_decision else None,
                    risk_pct=Decimal(decision.risk_decision.get("risk_pct", 0)) if decision.risk_decision else None
                )
                session.add(dec_orm)
                await session.commit()
                logger.info(f"Persisted Signal {sig_orm.id} and Decision {dec_orm.id}")

            if decision.approved:
                logger.info(f"✅ SIGNAL APPROVED: {decision.signal.direction} {symbol}")
            elif decision.signal:
                logger.info(f"⚠️ SIGNAL FOUND BUT REJECTED: {decision.signal.direction} {symbol} -> {decision.rejection_reason}")
            else:
                logger.info(f"No signal generated for {symbol}")

if __name__ == "__main__":
    asyncio.run(run_manual_cycle())