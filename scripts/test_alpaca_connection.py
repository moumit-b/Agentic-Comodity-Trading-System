#!/usr/bin/env python3
"""Test Alpaca API connection with the keys from .env file."""

import os

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test Alpaca API connection."""
    print("=" * 60)
    print("Testing Alpaca API Connection")
    print("=" * 60)

    # Get credentials
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    is_paper = os.getenv("ALPACA_IS_PAPER", "true").lower() == "true"

    if not api_key or not api_secret:
        print("[ERROR] Missing API keys in .env file")
        return False

    print("\n[CONFIG] Configuration:")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Mode: {'Paper Trading' if is_paper else 'Live Trading'}")

    try:
        # Test trading client
        print("\n[TEST] Testing Trading Client...")
        trading_client = TradingClient(api_key, api_secret, paper=is_paper)
        account = trading_client.get_account()

        print("[SUCCESS] Trading Client Connected!")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")

    except Exception as e:
        print(f"[ERROR] Trading Client Error: {e}")
        return False

    try:
        # Test market data client
        print("\n[TEST] Testing Market Data Client...")
        data_client = StockHistoricalDataClient(api_key, api_secret)

        # Get latest quote for USO
        request = StockLatestQuoteRequest(symbol_or_symbols=["USO"])
        quotes = data_client.get_stock_latest_quote(request)
        uso_quote = quotes["USO"]

        print("[SUCCESS] Market Data Client Connected!")
        print(f"   USO Bid: ${uso_quote.bid_price}")
        print(f"   USO Ask: ${uso_quote.ask_price}")
        print(f"   Timestamp: {uso_quote.timestamp}")

    except Exception as e:
        print(f"[ERROR] Market Data Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All Tests Passed! Alpaca API is working correctly.")
    print("=" * 60)
    print("\n[NEXT STEPS]")
    print("   1. Run: uv run python scripts/seed_sample_data.py")
    print("   2. Run: uv run streamlit run dashboard/app.py")
    print("   3. Open: http://localhost:8501")

    return True

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
