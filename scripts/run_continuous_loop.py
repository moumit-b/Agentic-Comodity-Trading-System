
import asyncio
import sys
import os
import logging
import time
from datetime import datetime, timezone

# Add current directory to path
sys.path.append(os.getcwd())

from scripts.run_data_ingestion import ingest_data
from scripts.run_trading_cycle import run_manual_cycle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("continuous_loop.log")
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting continuous trading loop...")
    logger.info("Press Ctrl+C to stop.")
    
    cycle_count = 0
    
    while True:
        cycle_count += 1
        start_time = time.time()
        logger.info(f"=== Starting Cycle #{cycle_count} ===")
        
        try:
            # Step 1: Ingest Data (Updates DB with latest RSI)
            logger.info(">>> Running Data Ingestion...")
            await ingest_data()
            
            # Step 2: Run Trading Logic (Checks for signals)
            logger.info(">>> Running Trading Logic...")
            await run_manual_cycle()
            
        except Exception as e:
            logger.error(f"Cycle failed: {e}", exc_info=True)
            
        duration = time.time() - start_time
        logger.info(f"=== Cycle #{cycle_count} Completed in {duration:.2f}s ===")
        
        # Sleep for remainder of minute
        sleep_time = max(10, 60 - duration)
        logger.info(f"Sleeping for {sleep_time:.2f}s...")
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Loop stopped by user.")
