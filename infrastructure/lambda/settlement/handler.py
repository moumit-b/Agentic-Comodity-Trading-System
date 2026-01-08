"""
Lambda handler for daily settlement processing.
Triggered by EventBridge at market close (4:00 PM ET).

This handler:
1. Processes T+1 settlement for all pending trades
2. Marks settled transactions
3. Updates available cash balances
4. Sends daily summary notification
5. Performs end-of-day cleanup
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
    Lambda handler for daily settlement processing.

    Args:
        event: EventBridge event (empty for scheduled invocations)
        context: Lambda context object

    Returns:
        dict: Settlement summary with statistics
    """
    start_time = datetime.utcnow()
    logger.info("=" * 80)
    logger.info(f"Settlement processing started at {start_time.isoformat()}Z")
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
        from src.agents.settlement_tracker import SettlementTrackerAgent
        from src.core.config import DatabaseConfig, TradingConfig
        from src.core.database import init_db

        # Initialize configuration
        config = TradingConfig()
        logger.info("Configuration loaded")

        # Initialize database
        logger.info("Initializing database...")
        db_config = DatabaseConfig()
        init_db(db_config)

        # Initialize settlement tracker
        logger.info("Initializing settlement tracker agent...")
        settlement_tracker = SettlementTrackerAgent()  # Takes no arguments

        # Process settlement
        logger.info("Processing settlement for today...")
        settlement_result = asyncio.run(settlement_tracker.process_due_settlements())

        # Get pending settlements
        logger.info("Retrieving pending settlements...")
        # get_settlement_status requires total_cash, so we need to fetch it from Alpaca
        from src.services.alpaca_api import AlpacaService

        alpaca_service = AlpacaService(config.alpaca, paper_mode=config.alpaca.paper_trading)
        account_info = alpaca_service.get_account()
        from decimal import Decimal

        total_cash = Decimal(str(account_info.cash))
        settlement_status = asyncio.run(settlement_tracker.get_settlement_status(total_cash))
        pending = settlement_status.pending_settlements

        # Available cash is already calculated in settlement_status
        logger.info("Calculating available cash...")
        available_cash = settlement_status.available_to_trade

        # Cleanup old records (older than 90 days)
        logger.info("Cleaning up old settlement records...")
        cleanup_result = asyncio.run(settlement_tracker.cleanup_old_settlements(90))

        # Log summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        summary = {
            "settled_today": settlement_result,
            "pending_settlements": len(pending),
            "available_cash": float(available_cash),
            "account_cash": float(account_info.cash),
            "cleanup_deleted": cleanup_result,
        }

        logger.info("-" * 80)
        logger.info(f"Settlement processing completed in {duration:.2f}s")
        logger.info(f"Summary: {json.dumps(summary, indent=2)}")
        logger.info("=" * 80)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Settlement processing completed successfully",
                    "request_id": context.aws_request_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "environment": environment,
                    "summary": summary,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Settlement processing failed: {e}", exc_info=True)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": "Settlement processing failed",
                    "request_id": context.aws_request_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            ),
        }
