"""Settlement Tracker Agent - manages T+1 settlement for cash account compliance."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.core.database import get_session
from src.models.settlement import Settlement

logger = logging.getLogger(__name__)


class SettlementStatus:
    """Settlement status information."""

    def __init__(
        self,
        total_settled: Decimal,
        total_pending: Decimal,
        available_to_trade: Decimal,
        pending_settlements: list[Settlement],
    ):
        """
        Initialize settlement status.

        Args:
            total_settled: Total settled cash available
            total_pending: Total cash pending settlement
            available_to_trade: Cash available for new trades
            pending_settlements: List of pending settlement records
        """
        self.total_settled = total_settled
        self.total_pending = total_pending
        self.available_to_trade = available_to_trade
        self.pending_settlements = pending_settlements


class SettlementTrackerAgent:
    """
    Agent responsible for:
    - Tracking T+1 settlement for cash account (PDT workaround)
    - Preventing trades with unsettled cash
    - Calculating available buying power
    - Recording and updating settlement records
    - Auto-marking settlements as complete on settlement date
    """

    def __init__(self):
        """Initialize Settlement Tracker Agent."""
        self.settlement_delay_days = 1  # T+1 settlement

    async def record_trade_settlement(
        self, trade_id: str, symbol: str, cash_amount: Decimal, trade_date: date | None = None
    ) -> Settlement:
        """
        Record a new trade for T+1 settlement tracking.

        Args:
            trade_id: Unique trade identifier
            symbol: Stock symbol
            cash_amount: Cash amount tied up in trade
            trade_date: Trade date (defaults to today)

        Returns:
            Settlement record
        """
        if trade_date is None:
            trade_date = date.today()

        # Calculate settlement date (T+1)
        settlement_date = trade_date + timedelta(days=self.settlement_delay_days)

        settlement = Settlement(
            trade_id=trade_id,
            symbol=symbol,
            trade_date=trade_date,
            settlement_date=settlement_date,
            cash_amount=cash_amount,
            is_settled=False,
        )

        try:
            async with get_session() as session:
                session.add(settlement)
            logger.info(
                f"Recorded settlement: {trade_id} for ${cash_amount} "
                f"(settles on {settlement_date})"
            )
            return settlement
        except Exception as e:
            logger.error(f"Failed to record settlement for {trade_id}: {e}")
            raise

    async def mark_settlement_complete(self, trade_id: str) -> bool:
        """
        Mark a settlement as complete.

        Args:
            trade_id: Trade identifier

        Returns:
            True if marked complete, False if not found
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select, update

                # Find settlement
                stmt = select(Settlement).where(Settlement.trade_id == trade_id)
                result = await session.execute(stmt)
                settlement = result.scalar_one_or_none()

                if settlement is None:
                    logger.warning(f"Settlement not found: {trade_id}")
                    return False

                # Update settlement
                update_stmt = (
                    update(Settlement)
                    .where(Settlement.trade_id == trade_id)
                    .values(is_settled=True, settled_at=datetime.now())
                )
                await session.execute(update_stmt)

            logger.info(f"Marked settlement complete: {trade_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark settlement complete for {trade_id}: {e}")
            return False

    async def process_due_settlements(self, current_date: date | None = None) -> int:
        """
        Process all settlements that are due (settlement_date <= current_date).

        Args:
            current_date: Date to check (defaults to today)

        Returns:
            Number of settlements marked complete
        """
        if current_date is None:
            current_date = date.today()

        try:
            async with get_session() as session:
                from sqlalchemy import select, update

                # Find all unsettled records where settlement_date <= current_date
                stmt = select(Settlement).where(
                    Settlement.is_settled == False,
                    Settlement.settlement_date <= current_date,
                )
                result = await session.execute(stmt)
                due_settlements = result.scalars().all()

                if not due_settlements:
                    logger.debug("No settlements due for processing")
                    return 0

                # Mark all as settled
                trade_ids = [s.trade_id for s in due_settlements]
                update_stmt = (
                    update(Settlement)
                    .where(Settlement.trade_id.in_(trade_ids))
                    .values(is_settled=True, settled_at=datetime.now())
                )
                await session.execute(update_stmt)

            logger.info(
                f"Processed {len(due_settlements)} settlements on {current_date}: "
                f"{', '.join(trade_ids)}"
            )
            return len(due_settlements)

        except Exception as e:
            logger.error(f"Failed to process due settlements: {e}")
            return 0

    async def get_settlement_status(
        self, total_cash: Decimal, current_date: date | None = None
    ) -> SettlementStatus:
        """
        Get current settlement status and available buying power.

        Args:
            total_cash: Total cash in account
            current_date: Date to check (defaults to today)

        Returns:
            SettlementStatus object
        """
        if current_date is None:
            current_date = date.today()

        try:
            async with get_session() as session:
                from sqlalchemy import select

                # Get all pending settlements
                stmt = select(Settlement).where(Settlement.is_settled == False)
                result = await session.execute(stmt)
                pending_settlements = list(result.scalars().all())

            # Calculate totals
            total_pending = sum(
                (s.cash_amount for s in pending_settlements), Decimal("0.0")
            )
            total_settled = total_cash - total_pending
            available_to_trade = max(total_settled, Decimal("0.0"))

            logger.debug(
                f"Settlement status: Total={total_cash}, "
                f"Settled={total_settled}, Pending={total_pending}, "
                f"Available={available_to_trade}"
            )

            return SettlementStatus(
                total_settled=total_settled,
                total_pending=total_pending,
                available_to_trade=available_to_trade,
                pending_settlements=pending_settlements,
            )

        except Exception as e:
            logger.error(f"Failed to get settlement status: {e}")
            # Return conservative estimate on error
            return SettlementStatus(
                total_settled=Decimal("0.0"),
                total_pending=total_cash,
                available_to_trade=Decimal("0.0"),
                pending_settlements=[],
            )

    async def can_trade_amount(
        self, required_cash: Decimal, total_cash: Decimal
    ) -> tuple[bool, str]:
        """
        Check if sufficient settled cash is available for a trade.

        Args:
            required_cash: Cash needed for trade
            total_cash: Total cash in account

        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        status = await self.get_settlement_status(total_cash)

        if status.available_to_trade >= required_cash:
            return True, ""
        else:
            shortfall = required_cash - status.available_to_trade
            return (
                False,
                f"Insufficient settled cash. Need ${required_cash:.2f}, "
                f"have ${status.available_to_trade:.2f} settled "
                f"(${shortfall:.2f} pending settlement)",
            )

    async def get_pending_settlements_by_symbol(self, symbol: str) -> list[Settlement]:
        """
        Get all pending settlements for a specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            List of pending settlement records
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(Settlement).where(
                    Settlement.symbol == symbol, Settlement.is_settled == False
                )
                result = await session.execute(stmt)
                settlements = list(result.scalars().all())

            logger.debug(f"Found {len(settlements)} pending settlements for {symbol}")
            return settlements

        except Exception as e:
            logger.error(f"Failed to get pending settlements for {symbol}: {e}")
            return []

    async def calculate_max_tradeable_amount(
        self, total_cash: Decimal, symbol: str
    ) -> Decimal:
        """
        Calculate maximum amount that can be traded for a symbol.

        Accounts for T+1 settlement - cannot trade same symbol with unsettled cash.

        Args:
            total_cash: Total cash in account
            symbol: Stock symbol to trade

        Returns:
            Maximum tradeable amount
        """
        # Get overall settlement status
        status = await self.get_settlement_status(total_cash)

        # Get pending settlements for this specific symbol
        symbol_pending = await self.get_pending_settlements_by_symbol(symbol)

        if not symbol_pending:
            # No pending settlements for this symbol, can use all settled cash
            max_amount = status.available_to_trade
        else:
            # Have pending settlements for this symbol
            # Cannot re-trade this symbol until those settle
            # This prevents "good faith violation" on cash accounts
            max_amount = Decimal("0.0")
            logger.warning(
                f"Cannot trade {symbol} - {len(symbol_pending)} pending settlements "
                f"(total ${sum(s.cash_amount for s in symbol_pending):.2f})"
            )

        return max_amount

    async def get_settlement_calendar(
        self, days_ahead: int = 7
    ) -> dict[date, list[Settlement]]:
        """
        Get upcoming settlement calendar.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            Dict mapping settlement_date -> list of Settlement records
        """
        end_date = date.today() + timedelta(days=days_ahead)

        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(Settlement).where(
                    Settlement.is_settled == False,
                    Settlement.settlement_date <= end_date,
                )
                result = await session.execute(stmt)
                settlements = list(result.scalars().all())

            # Group by settlement date
            calendar: dict[date, list[Settlement]] = {}
            for settlement in settlements:
                if settlement.settlement_date not in calendar:
                    calendar[settlement.settlement_date] = []
                calendar[settlement.settlement_date].append(settlement)

            return calendar

        except Exception as e:
            logger.error(f"Failed to get settlement calendar: {e}")
            return {}

    async def cleanup_old_settlements(self, days_to_keep: int = 90) -> int:
        """
        Clean up old settled records to prevent database bloat.

        Args:
            days_to_keep: Keep settlements from last N days

        Returns:
            Number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)

        try:
            async with get_session() as session:
                from sqlalchemy import delete, select

                # Count records to delete
                count_stmt = select(Settlement).where(
                    Settlement.is_settled == True,
                    Settlement.settlement_date < cutoff_date,
                )
                result = await session.execute(count_stmt)
                to_delete = len(list(result.scalars().all()))

                # Delete old records
                delete_stmt = delete(Settlement).where(
                    Settlement.is_settled == True,
                    Settlement.settlement_date < cutoff_date,
                )
                await session.execute(delete_stmt)

            logger.info(
                f"Cleaned up {to_delete} old settlement records "
                f"(older than {cutoff_date})"
            )
            return to_delete

        except Exception as e:
            logger.error(f"Failed to cleanup old settlements: {e}")
            return 0
