"""Market data API endpoints."""

import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.api.auth import verify_api_key
from src.api.schemas.responses import BarResponse, IndicatorResponse
from src.core.database import get_session
from src.models.bars import Bar1m, Indicator

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/bars/{symbol}", response_model=List[BarResponse])
@limiter.limit("60/minute")
async def get_bars(
    request: Request,
    symbol: str,
    limit: int = Query(390, ge=1, le=5000),
    timeframe: str = Query("1Day"),
    _api_key: str = Depends(verify_api_key),
):
    """
    Get historical bars for a symbol.
    Performs on-the-fly aggregation from 1-minute bars.
    """
    try:
        # Map frontend timeframe to pandas offset aliases
        timeframe_map = {
            "1Min": "1min",
            "5Min": "5min",
            "15Min": "15min",
            "1Hour": "1h",
            "4Hour": "4h",
            "1Day": "1D",
            "1Week": "1W",
        }
        resample_rule = timeframe_map.get(timeframe, "1D")
        
        # Determine how many 1m bars to fetch
        # If aggregating, we need more raw data
        fetch_limit = limit
        if resample_rule != "1min":
            # Fetch up to 20,000 bars (~2 months) for aggregation
            # This is a safe upper bound for performance
            fetch_limit = 20000

        async with get_session() as session:
            stmt = (
                select(Bar1m)
                .where(Bar1m.symbol == symbol)
                .order_by(Bar1m.timestamp.desc())
                .limit(fetch_limit)
            )
            result = await session.execute(stmt)
            bars = result.scalars().all()
            
            if not bars:
                return []

            # specific handling for 1m (no aggregation needed)
            if resample_rule == "1min" or timeframe == "1Min":
                 response_data = []
                 for bar in bars:
                    response_data.append(BarResponse(
                        timestamp=bar.timestamp,
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        volume=bar.volume
                    ))
                 return sorted(response_data, key=lambda x: x.timestamp)[:limit]

            # Convert to DataFrame for resampling
            data = []
            for bar in bars:
                data.append({
                    "timestamp": bar.timestamp,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume)
                })
            
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            # Resample
            agg_dict = {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }
            
            df_resampled = df.resample(resample_rule).agg(agg_dict).dropna()
            
            # Slice to requested limit
            if len(df_resampled) > limit:
                df_resampled = df_resampled.iloc[-limit:]
            
            # Convert back to response model
            response_data = []
            for timestamp, row in df_resampled.iterrows():
                response_data.append(BarResponse(
                    timestamp=timestamp,
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=int(row["volume"])
                ))
            
            return response_data

    except Exception as e:
        logger.error(f"Failed to fetch bars for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}", response_model=List[IndicatorResponse])
@limiter.limit("60/minute")
async def get_indicators(
    request: Request,
    symbol: str,
    timeframe: str = Query("5m"),
    limit: int = Query(100, ge=1, le=1000),
    _api_key: str = Depends(verify_api_key),
):
    """Get technical indicators for a symbol."""
    try:
        async with get_session() as session:
            stmt = (
                select(Indicator)
                .where(
                    Indicator.symbol == symbol, 
                    Indicator.timeframe == timeframe
                )
                .order_by(Indicator.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            indicators = result.scalars().all()
            
            response_data = []
            for ind in indicators:
                response_data.append(IndicatorResponse(
                    timestamp=ind.timestamp,
                    sma_20=float(ind.sma_20) if ind.sma_20 is not None else None,
                    ema_20=float(ind.ema_20) if ind.ema_20 is not None else None,
                    rsi=float(ind.rsi) if ind.rsi is not None else None,
                    atr=float(ind.atr) if ind.atr is not None else None,
                    macd=float(ind.macd) if ind.macd is not None else None,
                    macd_signal=float(ind.macd_signal) if ind.macd_signal is not None else None,
                    macd_histogram=float(ind.macd_histogram) if ind.macd_histogram is not None else None,
                    bb_upper=float(ind.bb_upper) if ind.bb_upper is not None else None,
                    bb_middle=float(ind.bb_middle) if ind.bb_middle is not None else None,
                    bb_lower=float(ind.bb_lower) if ind.bb_lower is not None else None,
                ))
                
            return sorted(response_data, key=lambda x: x.timestamp)

    except Exception as e:
        logger.error(f"Failed to fetch indicators for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
