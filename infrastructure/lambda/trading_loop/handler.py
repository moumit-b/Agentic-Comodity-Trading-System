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
        os.environ["ALPACA_PAPER_TRADING"] = str(alpaca_creds.get("paper", True))

        # Construct database URL
        db_url = (
            f"postgresql+asyncpg://{db_creds['username']}:{db_creds['password']}"
            f"@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        )
        os.environ["DATABASE_URL"] = db_url

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
        from src.core.config import DatabaseConfig, TradingConfig
        from src.core.database import init_db
        from src.services.alpaca_api import AlpacaService
        from src.services.circuit_breakers import CircuitBreakerService

        # Initialize configuration
        config = TradingConfig()
        logger.info(f"Configuration loaded: automation_mode={config.automation_mode.value}")

        # Initialize database
        logger.info("Initializing database...")
        db_config = DatabaseConfig()
        init_db(db_config)

        # Initialize services
        logger.info("Initializing services...")
        alpaca_service = AlpacaService(config.alpaca, paper_mode=config.alpaca.paper_trading)
        circuit_breakers = CircuitBreakerService()

        # Initialize agents
        logger.info("Initializing agents...")
        strategy_selector = StrategySelectorAgent(config)
        strategy_pool = StrategyPoolAgent()
        risk_manager = RiskManagerAgent(config)
        settlement_tracker = SettlementTrackerAgent()
        execution_agent = ExecutionAgent(config, mode=config.automation_mode)

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

        # Fetch account information
        logger.info("Fetching account information...")
        account = alpaca_service.get_account()
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
        positions = alpaca_service.get_all_positions()
        current_positions = len(positions)
        logger.info(f"Current positions: {current_positions}")

        # Fetch market data for USO (primary symbol)
        # TODO: Make symbol configurable
        symbol = "USO"
        logger.info(f"Fetching market data for {symbol}...")
        bars = alpaca_service.get_latest_bars([symbol])
        market_data = {
            "symbol": symbol,
            "bars": bars,
            # Additional data would be fetched here (indicators, etc.)
        }

        # Get daily trades count and consecutive losses from circuit breakers
        # For now, use placeholder values (would be fetched from database in production)
        daily_trades_count = 0  # TODO: Query from database
        consecutive_losses = 0  # TODO: Query from database or circuit breaker state

        logger.info("Running trading cycle...")
        result = asyncio.run(
            coordinator.run_trading_cycle(
                market_data=market_data,
                account_balance=account_balance,
                current_positions=current_positions,
                daily_trades_count=daily_trades_count,
                consecutive_losses=consecutive_losses,
                daily_pnl_pct=daily_pnl_pct,
            )
        )

        # Log results
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info("-" * 80)
        logger.info(f"Trading cycle completed in {duration:.2f}s")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
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
                    "result": result,
                }
            ),
        }

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
