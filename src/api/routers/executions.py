"""Executions API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select

from src.api.schemas.responses import ExecutionResponse
from src.core.database import get_session
from src.models.execution import Execution

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfirmationRequest(BaseModel):
    """Request to confirm/reject an execution."""

    action: str  # "approve" or "reject"
    reason: str | None = None


@router.get("/executions", response_model=list[ExecutionResponse])
async def get_executions(
    limit: int = Query(50, ge=1, le=1000, description="Number of executions to return"),
):
    """Get recent executions."""
    try:
        async with get_session() as session:
            stmt = select(Execution).order_by(Execution.timestamp.desc()).limit(limit)
            result = await session.execute(stmt)
            executions = result.scalars().all()

            return [
                ExecutionResponse(
                    id=ex.id,
                    timestamp=ex.timestamp,
                    symbol=ex.symbol,
                    side=ex.side,
                    qty=ex.qty,
                    filled_price=ex.filled_price,
                    status=ex.status,
                    requires_confirmation=ex.requires_confirmation,
                    alpaca_order_id=ex.alpaca_order_id,
                )
                for ex in executions
            ]
    except Exception as e:
        logger.error(f"Failed to get executions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/pending", response_model=list[ExecutionResponse])
async def get_pending_confirmations():
    """Get executions pending confirmation."""
    try:
        async with get_session() as session:
            stmt = select(Execution).where(
                Execution.requires_confirmation == True, Execution.status == "PENDING"
            )
            result = await session.execute(stmt)
            executions = result.scalars().all()

            return [
                ExecutionResponse(
                    id=ex.id,
                    timestamp=ex.timestamp,
                    symbol=ex.symbol,
                    side=ex.side,
                    qty=ex.qty,
                    filled_price=ex.filled_price,
                    status=ex.status,
                    requires_confirmation=ex.requires_confirmation,
                    alpaca_order_id=ex.alpaca_order_id,
                )
                for ex in executions
            ]
    except Exception as e:
        logger.error(f"Failed to get pending confirmations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/confirm")
async def confirm_execution(
    execution_id: int = Path(..., description="Execution ID"),
    request: ConfirmationRequest = None,
):
    """Confirm or reject an execution."""
    try:
        async with get_session() as session:
            stmt = select(Execution).where(Execution.id == execution_id)
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")

            if not execution.requires_confirmation:
                raise HTTPException(
                    status_code=400, detail="Execution does not require confirmation"
                )

            # TODO: Implement confirmation logic
            # Update execution status based on request.action

            return {
                "status": "success",
                "execution_id": execution_id,
                "action": request.action,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
