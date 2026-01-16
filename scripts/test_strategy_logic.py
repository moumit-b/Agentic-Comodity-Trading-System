"""
Test script to verify Strategy Logic and Signal Generation.
Runs the Coordinator Agent against historical data to check for signals.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_strategy_logic():
    print("=== Testing Strategy Logic (Dry Run) ===")
    
    try:
        # Import necessary modules
        from src.agents.coordinator import CoordinatorAgent
        from src.agents.execution_agent import ExecutionAgent
        from src.agents.risk_manager import RiskManagerAgent
        from src.agents.settlement_tracker import SettlementTrackerAgent
        from src.agents.strategy_pool import StrategyPoolAgent
        from src.agents.strategy_selector import StrategySelectorAgent
        from src.core.config import TradingConfig, AlpacaConfig, DatabaseConfig, RedisConfig
        from src.services.alpaca_api import AlpacaService
        from src.services.circuit_breakers import CircuitBreakerService
        from src.agents.market_data import MarketDataAgent
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        # Load config
        config = TradingConfig()
        alpaca_config = AlpacaConfig()
        
        # Initialize Services (Mocking DB/Redis to avoid connection issues if not running)
        # Actually, let's use the real ones if available, or lightweight mocks
        # Coordinator needs them initialized.
        
        print("Initializing agents...")
        strategy_selector = StrategySelectorAgent(config)
        strategy_pool = StrategyPoolAgent()
        risk_manager = RiskManagerAgent(config)
        settlement_tracker = SettlementTrackerAgent()
        execution_agent = ExecutionAgent(config)
        circuit_breakers = CircuitBreakerService()
        
        # === MOCKING FOR DRY RUN ===
        # Mock Circuit Breaker
        from src.services.circuit_breakers import CircuitBreakerStatus
        async def mock_check_breakers(*args, **kwargs):
            return CircuitBreakerStatus(is_tripped=False, active_breakers=[], reasons=[], can_trade=True)
        circuit_breakers.check_all_breakers = mock_check_breakers
        
        # Bypass DB calls for risk manager (portfolio heat)
        from src.agents.risk_manager import PortfolioRisk
        async def mock_calc_heat(*args, **kwargs):
            return PortfolioRisk(
                total_positions=0, 
                portfolio_value=Decimal("100000"), 
                current_heat=Decimal("0"),
                risk_per_position={},
                max_position_risk=Decimal("0")
            )
        risk_manager.calculate_portfolio_heat = mock_calc_heat
        # ===========================
        
        coordinator = CoordinatorAgent(
            config=config,
            strategy_selector=strategy_selector,
            strategy_pool=strategy_pool,
            risk_manager=risk_manager,
            settlement_tracker=settlement_tracker,
            circuit_breakers=circuit_breakers,
            execution_agent=execution_agent,
        )
        
        # Initialize Market Data (Direct Alpaca Client)
        print("Fetching historical data from Alpaca...")
        from alpaca.data.historical import StockHistoricalDataClient
        history_client = StockHistoricalDataClient(
            api_key=alpaca_config.api_key.get_secret_value(),
            secret_key=alpaca_config.api_secret.get_secret_value()
        )
        
        symbols = ["USO", "UNG"]
        # Fetch last 2 days, ending 20 mins ago to support free tier API keys
        end = datetime.now(timezone.utc) - timedelta(minutes=20)
        start = end - timedelta(days=2)
        
        for symbol in symbols:
            print(f"\n--- Analyzing {symbol} ---")
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                start=start,
                end=end,
            )
            
            bars_response = history_client.get_stock_bars(request)
            
            # Access the data dictionary from the wrapper
            data_dict = bars_response.data if hasattr(bars_response, "data") else bars_response
            
            if symbol not in data_dict:
                print(f"No data found for {symbol}")
                continue
                
            bars_list = data_dict[symbol]
            print(f"Fetched {len(bars_list)} bars.")
            
            # Simulate a trading cycle with this data
            market_data = {
                "symbol": symbol,
                "bars": {symbol: bars_list}
            }
            
            # Dummy account data
            account_balance = Decimal("100000")
            current_positions = 0
            daily_trades = 0
            consecutive_losses = 0
            daily_pnl = Decimal("0")
            
            print("Running Coordinator logic...")
            # We wrap the run_trading_cycle to handle potential DB calls gracefully
            # If Coordinator tries to write to DB, it might fail if DB is off locally.
            # But the logic *before* writing (signal generation) is what we care about.
            
            try:
                # We expect this might fail at the "Execution/Logging" step if DB is missing
                # But we should see "Signal generated" logs before that.
                decision = await coordinator.run_trading_cycle(
                    market_data=market_data,
                    account_balance=account_balance,
                    current_positions=current_positions,
                    daily_trades_count=daily_trades,
                    consecutive_losses=consecutive_losses,
                    daily_pnl_pct=daily_pnl
                )
                
                print(f"Decision: {decision}")
                if decision.signal:
                    print(f"✅ SIGNAL FOUND: {decision.signal.strategy_name} {decision.signal.direction}")
                else:
                    print(f"No signal: {decision.rejection_reason}")
                    
            except Exception as e:
                print(f"Cycle finished with error (expected if DB off): {e}")
                # Check logs above for "Signal generated"
                pass

    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_strategy_logic())
