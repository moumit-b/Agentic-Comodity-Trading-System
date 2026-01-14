"""
Lambda handler for trading loop execution.
Triggered by EventBridge every 1 minute during market hours (9 AM - 4 PM ET).

This handler:
1. Initializes services from AWS Secrets Manager
2. Runs the trading coordinator cycle
3. Logs execution results to CloudWatch
4. Returns execution summary
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(secret_name: str, region: str) -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler for trading loop execution.

    Args:
        event: EventBridge event (empty for scheduled invocations)
        context: Lambda context object

    Returns:
        dict: Execution summary with status and statistics
    """
    start_time = datetime.utcnow()
    logger.info("=" * 80)
    logger.info(f"Trading loop started at {start_time.isoformat()}Z")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Get environment variables
        region = os.environ["SECRETS_MANAGER_REGION"]
        alpaca_secret_name = os.environ["ALPACA_SECRET_NAME"]
        database_secret_name = os.environ["DATABASE_SECRET_NAME"]
        redis_secret_name = os.environ["REDIS_SECRET_NAME"]
        discord_secret_name = os.environ["DISCORD_SECRET_NAME"]
        environment = os.environ.get("ENVIRONMENT", "production")

        logger.info(f"Environment: {environment}")

        # Retrieve secrets
        logger.info("Retrieving secrets from Secrets Manager...")
        alpaca_creds = get_secret(alpaca_secret_name, region)
        db_creds = get_secret(database_secret_name, region)
        redis_creds = get_secret(redis_secret_name, region)
        discord_creds = get_secret(discord_secret_name, region)

        # Set environment variables for application
        os.environ["ALPACA_API_KEY"] = alpaca_creds["api_key"]
        os.environ["ALPACA_API_SECRET"] = alpaca_creds["api_secret"]
        os.environ["ALPACA_IS_PAPER"] = str(alpaca_creds.get("paper", True))

        # Set database connection vars for DatabaseConfig (Pydantic)
        # DatabaseConfig reads DB_HOST, DB_USER etc, not DATABASE_URL directly
        os.environ["DB_HOST"] = db_creds["host"]
        os.environ["DB_USER"] = db_creds["username"]
        os.environ["DB_PASSWORD"] = db_creds["password"]
        os.environ["DB_PORT"] = str(db_creds["port"])
        os.environ["DB_NAME"] = db_creds["database"]

        # Set Redis connection
        os.environ["REDIS_HOST"] = redis_creds["host"]
        os.environ["REDIS_PORT"] = str(redis_creds["port"])

        # Set Discord webhook
        os.environ["DISCORD_WEBHOOK_URL"] = discord_creds.get("webhook_url", "")

        logger.info("Secrets loaded successfully")

        # Import application modules (after environment is set)
        from decimal import Decimal

        from src.agents.coordinator import CoordinatorAgent
        from src.agents.execution_agent import ExecutionAgent
        from src.agents.risk_manager import RiskManagerAgent
        from src.agents.settlement_tracker import SettlementTrackerAgent
        from src.agents.strategy_pool import StrategyPoolAgent
        from src.agents.strategy_selector import StrategySelectorAgent
        from src.core.config import AlpacaConfig, DatabaseConfig, TradingConfig
        from src.core.database import init_db
        from src.services.alpaca_api import AlpacaService
        from src.services.circuit_breakers import CircuitBreakerService

        # Initialize configuration
        config = TradingConfig()
        alpaca_config = AlpacaConfig()
        logger.info(f"Configuration loaded: automation_mode={config.automation_mode.value}")

        # Initialize database
        logger.info("Initializing database...")
        db_config = DatabaseConfig()
        init_db(db_config)

        # Initialize services
        logger.info("Initializing services...")
        alpaca_service = AlpacaService(alpaca_config, paper_mode=alpaca_config.is_paper)
        circuit_breakers = CircuitBreakerService()

        # Initialize agents
        logger.info("Initializing agents...")
        strategy_selector = StrategySelectorAgent(config)
        strategy_pool = StrategyPoolAgent()
        risk_manager = RiskManagerAgent(config)
        settlement_tracker = SettlementTrackerAgent()
        execution_agent = ExecutionAgent(config, mode=config.automation_mode)
        
        # Initialize market data agent for fetching bars (Bypass Redis connection)
        from src.agents.market_data import MarketDataAgent
        from src.core.config import RedisConfig
        from alpaca.data.historical import StockHistoricalDataClient
        
        redis_config = RedisConfig()
        market_data_agent = MarketDataAgent(alpaca_config, redis_config)
        # Manually init historical client, skipping Redis connection
        market_data_agent._historical_client = StockHistoricalDataClient(
            api_key=alpaca_config.api_key.get_secret_value(),
            secret_key=alpaca_config.api_secret.get_secret_value(),
        )
        
        # Initialize coordinator
        logger.info("Initializing coordinator agent...")
        coordinator = CoordinatorAgent(
            config=config,
            strategy_selector=strategy_selector,
            strategy_pool=strategy_pool,
            risk_manager=risk_manager,
            settlement_tracker=settlement_tracker,
            circuit_breakers=circuit_breakers,
            execution_agent=execution_agent,
            notifier=None,  # Discord notifications optional in Lambda
        )

        # Define async function for fetching account data and running trading cycle
        async def run_trading_cycle_async():
            # Skip market_data_agent.connect() to avoid Redis/VPC timeout
            
            # Fetch account information
            logger.info("Fetching account information...")
            account = await alpaca_service.get_account()
            account_balance = Decimal(str(account.cash))
            logger.info(f"Account balance: ${account_balance:.2f}")

            # Calculate daily P&L percentage
            account_equity = Decimal(str(account.equity))
            last_equity = Decimal(str(account.last_equity))
            if last_equity > 0:
                daily_pnl_pct = ((account_equity - last_equity) / last_equity) * 100
            else:
                daily_pnl_pct = Decimal("0.0")
            logger.info(f"Daily P&L: {daily_pnl_pct:.2f}%")

            # Fetch current positions
            positions = await alpaca_service.get_all_positions()
            current_positions = len(positions)
            logger.info(f"Current positions: {current_positions}")

            # Check if market is open before proceeding
            logger.info("Checking market status...")
            if not alpaca_service.is_market_open():
                logger.info("Market is closed, skipping trading cycle")
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Market is closed, no trading cycle executed",
                        "request_id": context.aws_request_id,
                        "market_status": "closed",
                    }),
                }
            logger.info("Market is open, proceeding with trading cycle")

            # Get daily trades count and consecutive losses from database
            logger.info("Fetching daily trading statistics...")
            from datetime import date, timedelta
            from sqlalchemy import select, func
            from src.models.execution import Execution
            from src.models.account import DailyLimit
            from src.core.database import get_session

            async with get_session() as session:
                today = date.today()

                # Get daily trades count
                trades_stmt = select(func.count(Execution.id)).where(
                    Execution.timestamp >= datetime.combine(today, datetime.min.time()),
                    Execution.status.in_(["FILLED", "EXECUTED"])
                )
                trades_result = await session.execute(trades_stmt)
                daily_trades_count = int(trades_result.scalar() or 0)

                # Get consecutive losses from DailyLimit table
                limit_stmt = select(DailyLimit).where(DailyLimit.trade_date == today)
                limit_result = await session.execute(limit_stmt)
                daily_limit = limit_result.scalar_one_or_none()
                consecutive_losses = int(daily_limit.consecutive_losses if daily_limit else 0)

            logger.info(f"Daily stats: trades={daily_trades_count}, consecutive_losses={consecutive_losses}")

            # Process each symbol
            results = {}
            symbols = config.symbols # Default: ["USO", "UNG"]
            
            for symbol in symbols:
                logger.info(f"Processing symbol: {symbol}")
                try:
                    # Fetch historical bars (last 200 minutes to ensure enough for indicators)
                    end = datetime.utcnow()
                    start = end - timedelta(minutes=200)
                    
                    # We need the raw objects, not DF, for Coordinator compatibility
                    # Using internal client directly to get Bar objects
                    from alpaca.data.requests import StockBarsRequest
                    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
                    
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                        start=start,
                        end=end,
                    )
                    
                    # Use the client from market_data_agent
                    if not market_data_agent._historical_client:
                        logger.error("Historical client not initialized")
                        continue
                        
                    bars_response = market_data_agent._historical_client.get_stock_bars(request)
                    bars_list = bars_response[symbol] if symbol in bars_response else []
                    
                    if not bars_list:
                        logger.warning(f"No bars found for {symbol}")
                        continue
                        
                    market_data = {
                        "symbol": symbol,
                        "bars": {symbol: bars_list},
                    }

                    logger.info(f"Running trading cycle for {symbol}...")
                    result = await coordinator.run_trading_cycle(
                        market_data=market_data,
                        account_balance=account_balance,
                        current_positions=current_positions,
                        daily_trades_count=daily_trades_count,
                        consecutive_losses=consecutive_losses,
                        daily_pnl_pct=daily_pnl_pct,
                    )
                    results[symbol] = result
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}", exc_info=True)
                    results[symbol] = {"error": str(e)}

            # Disconnect
            # await market_data_agent.disconnect() # Don't disconnect since we didn't connect to Redis

            # Log results
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Serialize results safely
            def json_serial(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return str(obj)
                return str(obj)

            logger.info("-" * 80)
            logger.info(f"Trading cycle completed in {duration:.2f}s")
            # logger.info(f"Result: {json.dumps(results, indent=2, default=json_serial)}")
            logger.info("=" * 80)

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Trading cycle executed successfully",
                        "request_id": context.aws_request_id,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": duration,
                        "environment": environment,
                        "results_count": len(results),
                    }, default=json_serial
                ),
            }

        # Run the async trading cycle
        return asyncio.run(run_trading_cycle_async())

    except Exception as e:
        logger.error(f"Trading cycle failed: {e}", exc_info=True)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": "Trading cycle failed",
                    "request_id": context.aws_request_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            ),
        }
