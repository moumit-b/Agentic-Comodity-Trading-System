"""Context Agent - analyzes market context using LLM for sentiment and regime classification."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.mcp.news_server import NewsMCPServer
from src.models.learning import ContextAnalysis
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContextAgent:
    """
    Agent for market context analysis using LLM.

    Responsibilities:
    - Fetch and analyze news headlines from multiple sources (Finnhub, Reddit)
    - Generate sentiment scores via LLM
    - Classify market regime tags
    - Cache analysis in database
    - Adjust signal confidence based on sentiment alignment
    """

    def __init__(
        self,
        llm_service: LLMService,
        cache_ttl_minutes: int = 5,
    ):
        """
        Initialize Context Agent.

        Args:
            llm_service: LLM service for sentiment analysis
            cache_ttl_minutes: Cache TTL for context analysis
        """
        self.llm = llm_service
        self.cache_ttl_minutes = cache_ttl_minutes
        self.news_server = NewsMCPServer()

    async def get_context_analysis(
        self,
        symbol: str,
        market_metrics: dict,
        session: AsyncSession | None = None,
    ) -> ContextAnalysis | None:
        """
        Get context analysis for symbol, using cache if available.

        Args:
            symbol: Stock symbol (e.g., "USO")
            market_metrics: Dict with price, rsi, volume, etc.
            session: Optional database session

        Returns:
            ContextAnalysis object or None if LLM disabled
        """
        # Check for cached analysis first
        if session:
            cached = await self._get_cached_analysis(symbol, session)
            if cached:
                logger.info(f"Using cached context analysis for {symbol}")
                return cached

        # Generate new analysis
        if not self.llm.is_enabled:
            logger.warning("LLM disabled, skipping context analysis")
            return None

        try:
            # Fetch aggregated news from MCP server
            news_data = await self._fetch_aggregated_news(symbol)

            # Extract headlines for LLM analysis
            headlines = [h["text"] for h in news_data.get("headlines", [])[:10]]

            if not headlines:
                logger.warning(f"No news headlines available for {symbol}")
                headlines = ["No recent news available"]

            # Analyze sentiment via LLM
            result = await self.llm.analyze_sentiment(
                symbol=symbol,
                headlines=headlines,
                market_metrics=market_metrics,
            )

            # Create ContextAnalysis object
            analysis = ContextAnalysis(
                symbol=symbol,
                analyzed_at=datetime.now(),
                sentiment_score=Decimal(str(result.get("sentiment_score", 0))),
                regime_tag=result.get("regime_tag", "Normal"),
                confidence=Decimal(str(result.get("confidence", 0))),
                reasoning=result.get("reasoning"),
                news_headlines={"headlines": headlines[:10]},
                eia_events={},  # TODO: Integrate EIA calendar
                market_metrics=market_metrics,
                llm_prompt=f"Analyzed {len(headlines)} headlines for {symbol}",
                llm_response=str(result),
                expires_at=datetime.now() + timedelta(minutes=self.cache_ttl_minutes),
            )

            # Save to database
            if session:
                session.add(analysis)
                await session.flush()
                logger.info(
                    f"Saved context analysis for {symbol}: "
                    f"sentiment={analysis.sentiment_score}, "
                    f"regime={analysis.regime_tag}"
                )

            return analysis

        except Exception as e:
            logger.error(f"Failed to generate context analysis: {e}", exc_info=True)
            return None

    async def _fetch_aggregated_news(
        self,
        symbol: str,
    ) -> dict:
        """
        Fetch aggregated news from MCP news server.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with headlines from multiple sources
        """
        try:
            news_data = await self.news_server.aggregate_news(symbol, lookback_days=1)
            logger.info(
                f"Fetched {news_data.get('total_headlines', 0)} headlines for {symbol} "
                f"(Finnhub: {news_data['sources'].get('finnhub', 0)}, "
                f"Reddit: {news_data['sources'].get('reddit', 0)})"
            )
            return news_data
        except Exception as e:
            logger.error(f"Failed to fetch aggregated news: {e}")
            return {"headlines": []}

    async def _get_cached_analysis(
        self,
        symbol: str,
        session: AsyncSession,
    ) -> ContextAnalysis | None:
        """Get non-expired cached analysis from database."""
        query = (
            select(ContextAnalysis)
            .where(ContextAnalysis.symbol == symbol)
            .where(ContextAnalysis.expires_at > datetime.now())
            .order_by(ContextAnalysis.analyzed_at.desc())
            .limit(1)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    def adjust_confidence_for_context(
        self,
        base_confidence: Decimal,
        context: ContextAnalysis | None,
        signal_direction: str,
    ) -> Decimal:
        """
        Adjust signal confidence based on context analysis.

        Args:
            base_confidence: Original signal confidence (0.0-1.0)
            context: Context analysis (may be None)
            signal_direction: "LONG" or "SHORT"

        Returns:
            Adjusted confidence value
        """
        if context is None or context.confidence < Decimal("0.5"):
            return base_confidence

        sentiment = float(context.sentiment_score)

        # Sentiment alignment bonus/penalty
        if signal_direction == "LONG":
            if sentiment > 0.3:
                adjustment = Decimal("0.05")  # Bullish sentiment supports long
            elif sentiment < -0.3:
                adjustment = Decimal("-0.10")  # Bearish sentiment hurts long
            else:
                adjustment = Decimal("0")
        else:  # SHORT
            if sentiment < -0.3:
                adjustment = Decimal("0.05")  # Bearish sentiment supports short
            elif sentiment > 0.3:
                adjustment = Decimal("-0.10")  # Bullish sentiment hurts short
            else:
                adjustment = Decimal("0")

        # High-impact regime tags
        high_impact_tags = ["Geopolitical_Risk", "Supply_Shock", "Demand_Surge"]
        if context.regime_tag in high_impact_tags:
            adjustment -= Decimal("0.05")  # Be more cautious during high-impact events

        adjusted = base_confidence + adjustment
        adjusted = max(Decimal("0.0"), min(Decimal("1.0"), adjusted))

        logger.debug(
            f"Confidence adjustment: {base_confidence:.2f} → {adjusted:.2f} "
            f"(sentiment={sentiment:.2f}, regime={context.regime_tag})"
        )

        return adjusted

    async def refresh_all_symbols(
        self,
        symbols: list[str],
        market_metrics_by_symbol: dict[str, dict],
    ) -> int:
        """
        Refresh context analysis for multiple symbols.

        Used by background task scheduler.

        Args:
            symbols: List of symbols to refresh
            market_metrics_by_symbol: Dict mapping symbol -> market metrics

        Returns:
            Number of symbols successfully refreshed
        """
        refreshed = 0

        async with get_session() as session:
            for symbol in symbols:
                try:
                    metrics = market_metrics_by_symbol.get(symbol, {})
                    analysis = await self.get_context_analysis(
                        symbol=symbol,
                        market_metrics=metrics,
                        session=session,
                    )

                    if analysis:
                        refreshed += 1

                except Exception as e:
                    logger.error(f"Failed to refresh context for {symbol}: {e}")

        logger.info(f"Refreshed context for {refreshed}/{len(symbols)} symbols")
        return refreshed
