"""Execution Agent - handles order placement and confirmation based on trading mode."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from src.core.config import AutomationMode, TradingConfig
from src.core.database import get_session
from src.models.execution import Execution
from src.strategies import Signal, SignalDirection

logger = logging.getLogger(__name__)


class ExecutionDecision(str, Enum):
    """Execution decision types."""

    EXECUTE = "EXECUTE"  # Execute immediately
    REQUEST_CONFIRMATION = "REQUEST_CONFIRMATION"  # Wait for human confirmation
    ADVISORY_ONLY = "ADVISORY_ONLY"  # Log only, no execution
    REJECTED = "REJECTED"  # Rejected by pre-flight checks


@dataclass
class ExecutionResult:
    """Result of execution attempt."""

    decision: ExecutionDecision
    order_id: str | None
    message: str
    requires_confirmation: bool
    metadata: dict


class ExecutionAgent:
    """
    Agent responsible for:
    - Order creation and submission
    - Execution mode handling (ADVISORY, PAPER, LIVE_CONFIRM, LIVE_AUTO)
    - Order tracking and status updates
    - Confirmation workflows
    """

    def __init__(self, config: TradingConfig, mode: AutomationMode = AutomationMode.ADVISORY):
        """
        Initialize Execution Agent.

        Args:
            config: Trading configuration
            mode: Automation mode (default: ADVISORY)
        """
        self.config = config
        self.mode = mode

    async def execute_signal(
        self,
        signal: Signal,
        position_size: Decimal,
        account_balance: Decimal,
    ) -> ExecutionResult:
        """
        Execute a trading signal based on current trading mode.

        Args:
            signal: Trading signal
            position_size: Number of shares to trade
            account_balance: Current account balance

        Returns:
            ExecutionResult
        """
        # Determine execution decision based on mode
        if self.mode == AutomationMode.ADVISORY:
            return await self._handle_advisory_mode(signal, position_size)
        elif self.mode == AutomationMode.PAPER_AUTO:
            return await self._handle_paper_mode(signal, position_size)
        elif self.mode == AutomationMode.LIVE_CONFIRM:
            return await self._handle_live_confirm_mode(signal, position_size)
        elif self.mode == AutomationMode.LIVE_AUTO:
            return await self._handle_live_auto_mode(signal, position_size)
        else:
            logger.error(f"Unknown automation mode: {self.mode}")
            return ExecutionResult(
                decision=ExecutionDecision.REJECTED,
                order_id=None,
                message=f"Unknown automation mode: {self.mode}",
                requires_confirmation=False,
                metadata={},
            )

    async def _handle_advisory_mode(
        self, signal: Signal, position_size: Decimal
    ) -> ExecutionResult:
        """Handle ADVISORY mode - log recommendation only."""
        message = (
            f"[ADVISORY] Recommend {signal.direction.value} {position_size} shares of {signal.symbol} "
            f"@ ${signal.suggested_entry:.2f} (stop: ${signal.suggested_stop:.2f}, "
            f"target: ${signal.suggested_target:.2f})"
        )
        logger.info(message)

        return ExecutionResult(
            decision=ExecutionDecision.ADVISORY_ONLY,
            order_id=None,
            message=message,
            requires_confirmation=False,
            metadata={
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "entry": str(signal.suggested_entry),
                "position_size": str(position_size),
            },
        )

    async def _handle_paper_mode(
        self, signal: Signal, position_size: Decimal
    ) -> ExecutionResult:
        """Handle PAPER_AUTO mode - execute in paper account automatically."""
        # Create paper execution
        execution = Execution(
            symbol=signal.symbol,
            side=signal.direction.value,
            qty=position_size,
            filled_price=signal.suggested_entry,
            order_type="LIMIT",
            status="FILLED",
            requires_confirmation=False,
        )

        async with get_session() as session:
            session.add(execution)
            await session.flush()  # Get the ID
            exec_id = execution.id

        message = (
            f"[PAPER] Executed {signal.direction.value} {position_size} shares of {signal.symbol} "
            f"@ ${signal.suggested_entry:.2f}"
        )
        logger.info(message)

        return ExecutionResult(
            decision=ExecutionDecision.EXECUTE,
            order_id=str(exec_id),
            message=message,
            requires_confirmation=False,
            metadata={
                "execution_id": exec_id,
                "is_paper": True,
            },
        )

    async def _handle_live_confirm_mode(
        self, signal: Signal, position_size: Decimal
    ) -> ExecutionResult:
        """Handle LIVE_CONFIRM mode - create execution but wait for confirmation."""
        # Create pending execution
        execution = Execution(
            symbol=signal.symbol,
            side=signal.direction.value,
            qty=position_size,
            filled_price=None,  # Not yet filled
            order_type="LIMIT",
            status="PENDING",
            requires_confirmation=True,
            confirmation_sent_at=datetime.now(),
        )

        async with get_session() as session:
            session.add(execution)
            await session.flush()
            exec_id = execution.id

        message = (
            f"[LIVE-CONFIRM] Awaiting confirmation to {signal.direction.value} "
            f"{position_size} shares of {signal.symbol} @ ${signal.suggested_entry:.2f}"
        )
        logger.info(message)

        return ExecutionResult(
            decision=ExecutionDecision.REQUEST_CONFIRMATION,
            order_id=str(exec_id),
            message=message,
            requires_confirmation=True,
            metadata={
                "execution_id": exec_id,
                "confirmation_required": True,
            },
        )

    async def _handle_live_auto_mode(
        self, signal: Signal, position_size: Decimal
    ) -> ExecutionResult:
        """Handle LIVE_AUTO mode - execute in live account automatically."""
        # Create live execution
        execution = Execution(
            symbol=signal.symbol,
            side=signal.direction.value,
            qty=position_size,
            filled_price=None,  # Will be filled after order execution
            order_type="LIMIT",
            status="PENDING",  # Will update to FILLED after Alpaca confirms
            requires_confirmation=False,
        )

        async with get_session() as session:
            session.add(execution)
            await session.flush()
            exec_id = execution.id

        message = (
            f"[LIVE-AUTO] Submitted {signal.direction.value} {position_size} shares "
            f"of {signal.symbol} @ ${signal.suggested_entry:.2f}"
        )
        logger.warning(message)  # Use warning level for live trades

        return ExecutionResult(
            decision=ExecutionDecision.EXECUTE,
            order_id=str(exec_id),
            message=message,
            requires_confirmation=False,
            metadata={
                "execution_id": exec_id,
                "is_live": True,
            },
        )

    async def confirm_execution(self, execution_id: int, confirmed: bool, confirmed_by: str = "DISCORD") -> bool:
        """
        Confirm or reject a pending execution.

        Args:
            execution_id: Execution ID
            confirmed: Whether to confirm (True) or reject (False)
            confirmed_by: Who confirmed (DISCORD, DASHBOARD, AUTO)

        Returns:
            True if confirmation processed successfully
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                # Find execution
                stmt = select(Execution).where(Execution.id == execution_id)
                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution is None:
                    logger.error(f"Execution not found: {execution_id}")
                    return False

                if not execution.requires_confirmation or execution.status != "PENDING":
                    logger.warning(
                        f"Execution {execution_id} is not pending confirmation (status: {execution.status})"
                    )
                    return False

                if confirmed:
                    # Confirm and submit to broker
                    execution.status = "FILLED"  # Simulate immediate fill for now
                    execution.confirmed_at = datetime.now()
                    execution.confirmed_by = confirmed_by
                    logger.info(f"Execution {execution_id} confirmed by {confirmed_by}")
                else:
                    # Reject execution
                    execution.status = "REJECTED"
                    execution.confirmed_at = datetime.now()
                    execution.confirmed_by = confirmed_by
                    logger.info(f"Execution {execution_id} rejected by {confirmed_by}")

                await session.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to confirm execution {execution_id}: {e}")
            return False

    async def get_pending_confirmations(self) -> list[Execution]:
        """
        Get all executions pending confirmation.

        Returns:
            List of pending executions
        """
        try:
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(Execution).where(
                    Execution.requires_confirmation == True,
                    Execution.status == "PENDING",
                )
                result = await session.execute(stmt)
                executions = list(result.scalars().all())

            return executions
        except Exception as e:
            logger.error(f"Failed to get pending confirmations: {e}")
            return []

    async def update_execution_status(
        self, execution_id: int, new_status: str, **kwargs
    ) -> bool:
        """
        Update execution status.

        Args:
            execution_id: Execution ID
            new_status: New status (PENDING, FILLED, REJECTED)
            **kwargs: Additional fields to update (e.g., filled_price, error_message)

        Returns:
            True if updated successfully
        """
        try:
            async with get_session() as session:
                from sqlalchemy import update

                update_values = {"status": new_status}
                update_values.update(kwargs)

                stmt = (
                    update(Execution)
                    .where(Execution.id == execution_id)
                    .values(**update_values)
                )
                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(f"Updated execution {execution_id} status to {new_status}")
                    return True
                else:
                    logger.warning(f"Execution {execution_id} not found for status update")
                    return False

        except Exception as e:
            logger.error(f"Failed to update execution {execution_id} status: {e}")
            return False
