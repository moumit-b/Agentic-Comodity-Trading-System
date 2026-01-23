
import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta, timezone

# Add current directory to path
sys.path.append(os.getcwd())

from src.core.config import AlpacaConfig, RedisConfig, DatabaseConfig
from src.core.database import init_db
from src.agents.market_data import MarketDataAgent
from src.services.redis_cache import RedisCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Redis to avoid connection issues if missing
class MockRedisCache(RedisCache):
    def connect(self):
        logger.info("Mock Redis connected")
    def disconnect(self):
        pass
    def cache_bars_1m(self, *args): pass
    def cache_bars_aggregated(self, *args): pass
    def cache_indicators(self, *args): pass
    def cache_regime(self, *args): pass
    def get_bars_1m(self, *args): return None
    def get_bars_aggregated(self, *args): return None
    def get_indicators(self, *args): return None
    def get_regime(self, *args): return None

async def ingest_data():
    logger.info("Starting manual data ingestion...")
    
    # Init DB
    db_config = DatabaseConfig()
    init_db(db_config)
    
    # Init Configs
    alpaca_config = AlpacaConfig()
    redis_config = RedisConfig()
    
    # Init Market Data Agent with Mock Redis
    agent = MarketDataAgent(alpaca_config, redis_config)
    agent.redis_cache = MockRedisCache(redis_config)
    
    # Connect (initializes Alpaca client)
    await agent.connect()
    
    symbols = ["USO", "UNG"]
    
    # Fetch last 24 hours of data, ending 20 mins ago (Free Tier restriction)
    end = datetime.now(timezone.utc) - timedelta(minutes=20)
    start = end - timedelta(days=1)
    
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}...")
        
        try:
            # Fetch 1m bars
            df = await agent.fetch_historical_bars(symbol, start, end)
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                continue
                
            logger.info(f"Fetched {len(df)} bars. Processing...")
            
            # Manually trigger processing for each bar (or batch it)
            # MarketDataAgent._on_bar_received expects a Bar object.
            # But we can just use the internal methods if we are careful.
            
            # Better approach: Use the internal buffer and trigger aggregation directly
            # converting the historical DF to the internal buffer format
            
            # The df from fetch_historical_bars is indexed by timestamp if using bars.df?
            # actually fetch_historical_bars returns df with multi-index (symbol, timestamp) or just timestamp?
            # Let's check alpaca sdk... usually it returns a df with timestamp index if single symbol?
            # The agent implementation returns: bars.df
            
            # Reset index to get timestamp as column
            df = df.reset_index()
            
            # Rename columns to match what _on_bar_received expects in the buffer
            # Alpaca historical DF columns: [open, high, low, close, volume, trade_count, vwap]
            # timestamp is in the index usually.
            
            # Let's populate the buffer directly
            agent._bars_1m[symbol] = df
            
            # Trigger aggregation which calculates indicators and saves to DB
            await agent._aggregate_timeframes(symbol)
            
            logger.info(f"Successfully processed {symbol}")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            
    await agent.disconnect()
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(ingest_data())
