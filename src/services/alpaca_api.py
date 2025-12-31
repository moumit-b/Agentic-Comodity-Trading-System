"""Alpaca API service for order execution and account management."""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.models import Order as AlpacaOrder

from src.core.config import AlpacaConfig

logger = logging.getLogger(__name__)


class AlpacaService:
    """
    Service for interacting with Alpaca API.

    Handles:
    - Order submission (market, limit, bracket)
    - Order status tracking
    - Position management
    - Account information
    """

    def __init__(self, config: AlpacaConfig, paper_mode: bool = True):
        """
        Initialize Alpaca service.

        Args:
            config: Alpaca configuration
            paper_mode: Whether to use paper trading account
        """
        self.config = config
        self.paper_mode = paper_mode

        # Initialize Alpaca client
        self.client = TradingClient(
            api_key=config.api_key.get_secret_value(),
            secret_key=config.api_secret.get_secret_value(),
            paper=paper_mode,
        )

        logger.info(f"Alpaca client initialized (paper={paper_mode})")

    async def submit_limit_order(
        self,
        symbol: str,
        qty: Decimal,
        side: str,  # "BUY" or "SELL"
        limit_price: Decimal,
        time_in_force: str = "day",
    ) -> AlpacaOrder:
        """
        Submit a limit order to Alpaca.

        Args:
            symbol: Stock symbol
            qty: Quantity
            side: Order side (BUY/SELL)
            limit_price: Limit price
            time_in_force: Time in force (day, gtc, ioc, fok)

        Returns:
            Alpaca Order object

        Raises:
            Exception if order submission fails
        """
        try:
            # Map our side to Alpaca enum
            alpaca_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            # Map time in force
            tif_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            alpaca_tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

            # Create order request
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=float(qty),
                side=alpaca_side,
                limit_price=float(limit_price),
                time_in_force=alpaca_tif,
            )

            # Submit order
            order = self.client.submit_order(order_data)

            logger.info(
                f"Submitted limit order: {order.id} - {side} {qty} {symbol} @ ${limit_price}"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to submit limit order: {e}")
            raise

    async def submit_market_order(
        self,
        symbol: str,
        qty: Decimal,
        side: str,
        time_in_force: str = "day",
    ) -> AlpacaOrder:
        """
        Submit a market order to Alpaca.

        Args:
            symbol: Stock symbol
            qty: Quantity
            side: Order side (BUY/SELL)
            time_in_force: Time in force

        Returns:
            Alpaca Order object

        Raises:
            Exception if order submission fails
        """
        try:
            # Map our side to Alpaca enum
            alpaca_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            # Map time in force
            tif_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            alpaca_tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

            # Create order request
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=float(qty),
                side=alpaca_side,
                time_in_force=alpaca_tif,
            )

            # Submit order
            order = self.client.submit_order(order_data)

            logger.info(f"Submitted market order: {order.id} - {side} {qty} {symbol}")

            return order

        except Exception as e:
            logger.error(f"Failed to submit market order: {e}")
            raise

    async def get_order(self, order_id: str) -> AlpacaOrder:
        """
        Get order details from Alpaca.

        Args:
            order_id: Alpaca order ID

        Returns:
            Alpaca Order object

        Raises:
            Exception if order not found
        """
        try:
            order = self.client.get_order_by_id(order_id)
            return order
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Alpaca order ID

        Returns:
            True if cancelled successfully

        Raises:
            Exception if cancellation fails
        """
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    async def get_all_positions(self) -> list:
        """
        Get all open positions.

        Returns:
            List of Alpaca Position objects
        """
        try:
            positions = self.client.get_all_positions()
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise

    async def get_position(self, symbol: str):
        """
        Get position for a specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Alpaca Position object or None if no position
        """
        try:
            position = self.client.get_open_position(symbol)
            return position
        except Exception as e:
            # Position not found is expected, don't log error
            if "position does not exist" in str(e).lower():
                return None
            logger.error(f"Failed to get position for {symbol}: {e}")
            raise

    async def close_position(self, symbol: str) -> bool:
        """
        Close a position.

        Args:
            symbol: Stock symbol

        Returns:
            True if closed successfully
        """
        try:
            self.client.close_position(symbol)
            logger.info(f"Closed position: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close position {symbol}: {e}")
            raise

    async def get_account(self):
        """
        Get account information.

        Returns:
            Alpaca Account object
        """
        try:
            account = self.client.get_account()
            return account
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise

    async def get_buying_power(self) -> Decimal:
        """
        Get current buying power.

        Returns:
            Buying power as Decimal
        """
        try:
            account = await self.get_account()
            return Decimal(str(account.buying_power))
        except Exception as e:
            logger.error(f"Failed to get buying power: {e}")
            raise

    async def get_portfolio_value(self) -> Decimal:
        """
        Get current portfolio value.

        Returns:
            Portfolio value as Decimal
        """
        try:
            account = await self.get_account()
            return Decimal(str(account.portfolio_value))
        except Exception as e:
            logger.error(f"Failed to get portfolio value: {e}")
            raise

    async def get_cash(self) -> Decimal:
        """
        Get current cash balance.

        Returns:
            Cash balance as Decimal
        """
        try:
            account = await self.get_account()
            return Decimal(str(account.cash))
        except Exception as e:
            logger.error(f"Failed to get cash balance: {e}")
            raise

    def is_market_open(self) -> bool:
        """
        Check if market is currently open.

        Returns:
            True if market is open
        """
        try:
            clock = self.client.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return False

    async def wait_for_order_fill(
        self, order_id: str, timeout_seconds: int = 60, poll_interval: int = 2
    ) -> AlpacaOrder:
        """
        Wait for an order to fill.

        Args:
            order_id: Alpaca order ID
            timeout_seconds: Max time to wait
            poll_interval: Seconds between status checks

        Returns:
            Filled Alpaca Order object

        Raises:
            TimeoutError if order doesn't fill in time
        """
        import asyncio

        elapsed = 0
        while elapsed < timeout_seconds:
            order = await self.get_order(order_id)

            if order.status == "filled":
                logger.info(f"Order {order_id} filled")
                return order
            elif order.status in ["canceled", "expired", "rejected"]:
                raise Exception(f"Order {order_id} ended with status: {order.status}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Order {order_id} did not fill within {timeout_seconds}s")
