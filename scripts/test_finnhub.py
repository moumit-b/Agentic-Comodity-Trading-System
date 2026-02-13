"""Test Finnhub WebSocket connection and bar aggregation."""

import asyncio
import logging
import sys

sys.path.append(".")

from src.agents.finnhub_data import FinnhubDataAgent
from src.core.config import FinnhubConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Test Finnhub connection."""
    logger.info("=" * 80)
    logger.info("FINNHUB WEBSOCKET CONNECTION TEST")
    logger.info("=" * 80)

    config = FinnhubConfig()

    if not config.api_key.get_secret_value():
        logger.error("❌ FINNHUB_API_KEY not set in .env")
        return

    logger.info(f"API Key: {config.api_key.get_secret_value()[:10]}...")
    logger.info(f"WebSocket URL: {config.ws_url}")
    logger.info(f"Use as primary: {config.use_as_primary}")

    # Callback to receive bars
    received_bars = []

    async def on_bar(symbol: str, bar_data: dict):
        logger.info(f"✅ Received 1m bar: {symbol} @ {bar_data['timestamp']}")
        logger.info(f"   O:{bar_data['open']:.2f} H:{bar_data['high']:.2f} "
                    f"L:{bar_data['low']:.2f} C:{bar_data['close']:.2f} V:{bar_data['volume']}")
        received_bars.append(bar_data)

    agent = FinnhubDataAgent(config, on_bar)

    try:
        # Connect
        logger.info("\nConnecting to Finnhub...")
        await agent.connect()

        # Subscribe to test symbols
        symbols = ["USO", "UNG"]
        logger.info(f"\nSubscribing to {symbols}...")
        await agent.subscribe(symbols)

        # Check health
        health = agent.get_health_status()
        logger.info("\nHealth Status:")
        logger.info(f"  Connected: {health['connected']}")
        logger.info(f"  Running: {health['running']}")
        logger.info(f"  Subscribed symbols: {health['subscribed_symbols']}")

        # Listen for 60 seconds
        logger.info("\n📡 Listening for trades (60 seconds)...")
        logger.info("   (Market needs to be open to receive data)")

        async def listen_task():
            try:
                await agent.run()
            except Exception as e:
                logger.error(f"Listen error: {e}")

        listen = asyncio.create_task(listen_task())

        # Wait 60 seconds
        await asyncio.sleep(60)

        # Cancel listening
        listen.cancel()

        logger.info(f"\n✅ Test complete. Received {len(received_bars)} bars")

        if received_bars:
            logger.info("\nSample bar:")
            bar = received_bars[0]
            logger.info(f"  Symbol: {bar.get('symbol', 'N/A')}")
            logger.info(f"  Timestamp: {bar['timestamp']}")
            logger.info(f"  OHLCV: O:{bar['open']} H:{bar['high']} L:{bar['low']} "
                        f"C:{bar['close']} V:{bar['volume']}")
        else:
            logger.warning("⚠️  No bars received (market may be closed)")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

    finally:
        await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
