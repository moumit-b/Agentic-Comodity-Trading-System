import asyncio
import sys

sys.path.append(".")

from sqlalchemy import text

from src.core.config import DatabaseConfig
from src.core.database import get_session, init_db


async def main():
    init_db(DatabaseConfig())

    async with get_session() as session:
        # Check indicators
        result = await session.execute(
            text("""
                SELECT symbol, timeframe, COUNT(*) as count,
                       MAX(timestamp) as latest,
                       AVG(rsi) as avg_rsi,
                       MAX(rsi) as max_rsi,
                       MIN(rsi) as min_rsi
                FROM indicators
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)
        )
        rows = result.fetchall()

        print("=" * 80)
        print("INDICATORS IN DATABASE")
        print("=" * 80)

        if not rows:
            print("⚠️  NO INDICATORS FOUND")
        else:
            for r in rows:
                print(f"{r.symbol} {r.timeframe}:")
                print(f"  Records: {r.count}")
                print(f"  Latest: {r.latest}")
                avg_rsi = f"{r.avg_rsi:.2f}" if r.avg_rsi else "N/A"
                min_rsi = f"{r.min_rsi:.2f}" if r.min_rsi else "N/A"
                max_rsi = f"{r.max_rsi:.2f}" if r.max_rsi else "N/A"
                print(f"  RSI - Avg: {avg_rsi}, Min: {min_rsi}, Max: {max_rsi}")
                print()

        # Check for potential signals (RSI < 30 or > 70)
        result = await session.execute(
            text("""
                SELECT symbol, timeframe, timestamp, rsi, sma_20, macd
                FROM indicators
                WHERE rsi IS NOT NULL
                  AND (rsi < 30 OR rsi > 70)
                  AND timestamp >= NOW() - INTERVAL '7 days'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
        )
        rows = result.fetchall()

        print("=" * 80)
        print("POTENTIAL SIGNALS (RSI < 30 or > 70)")
        print("=" * 80)

        if not rows:
            print("No extreme RSI signals in past 7 days")
        else:
            for r in rows:
                signal = "🔴 OVERBOUGHT" if r.rsi > 70 else "🟢 OVERSOLD"
                sma = f"{r.sma_20:.2f}" if r.sma_20 else "N/A"
                macd = f"{r.macd:.2f}" if r.macd else "N/A"
                print(f"{signal} - {r.symbol} {r.timeframe} @ {r.timestamp}")
                print(f"  RSI: {r.rsi:.2f}, SMA20: {sma}, MACD: {macd}")

if __name__ == "__main__":
    asyncio.run(main())
