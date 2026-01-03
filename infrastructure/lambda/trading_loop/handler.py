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
    logger.info(f"Request ID: {context.request_id}")
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
        from src.agents.coordinator import CoordinatorAgent
        from src.core.config import TradingConfig

        # Initialize configuration
        config = TradingConfig()
        logger.info(f"Configuration loaded: automation_mode={config.automation_mode.value}")

        # Run trading cycle
        logger.info("Initializing coordinator agent...")
        coordinator = CoordinatorAgent(config)

        logger.info("Running trading cycle...")
        result = asyncio.run(coordinator.run_trading_cycle())

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
                    "request_id": context.request_id,
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
                    "request_id": context.request_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            ),
        }
