"""Tests for Phase 2: Agentic Decision Making components."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.context_agent import ContextAgent
from src.agents.learning_observer import LearningObserver
from src.models.learning import ContextAnalysis, LearningLog
from src.services.llm_service import LLMService, RateLimiter
from src.strategies import Signal, SignalDirection
from src.strategies.mean_reversion import (
    BollingerBandsMeanReversion,
    RSIOversoldOverbought,
)

# ===== RateLimiter Tests =====


class TestRateLimiter:
    """Test RateLimiter enforces API rate limits correctly."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with correct parameters."""
        limiter = RateLimiter(rpm=15, tpm=1_000_000, rpd=1500)

        assert limiter.rpm == 15
        assert limiter.tpm == 1_000_000
        assert limiter.rpd == 1500
        assert len(limiter._minute_requests) == 0
        assert len(limiter._minute_tokens) == 0
        assert len(limiter._day_requests) == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limits(self):
        """Test rate limiter allows requests within limits."""
        limiter = RateLimiter(rpm=10, tpm=100_000, rpd=100)

        # Should allow first request without raising
        await limiter.acquire(estimated_tokens=50)
        limiter.record_request(50)
        assert len(limiter._minute_requests) == 1
        assert len(limiter._minute_tokens) == 1

    @pytest.mark.asyncio
    async def test_rate_limiter_raises_when_rpd_exceeded(self):
        """Test rate limiter raises exception when daily limit exceeded."""
        limiter = RateLimiter(rpm=1000, tpm=100_000, rpd=2)

        # Make 2 requests (hit RPD limit)
        await limiter.acquire(estimated_tokens=10)
        limiter.record_request(10)
        await limiter.acquire(estimated_tokens=10)
        limiter.record_request(10)

        # Third request should raise
        with pytest.raises(Exception, match="Daily rate limit exceeded"):
            await limiter.acquire(estimated_tokens=10)

    def test_rate_limiter_daily_remaining(self):
        """Test daily remaining counter."""
        limiter = RateLimiter(rpm=15, tpm=100_000, rpd=100)

        assert limiter.daily_remaining == 100

        limiter.record_request(50)
        assert limiter.daily_remaining == 99

        limiter.record_request(50)
        assert limiter.daily_remaining == 98


# ===== LLMService Tests =====


class TestLLMService:
    """Test multi-provider LLMService."""

    @pytest.fixture
    def mock_gemini_config(self):
        """Mock Gemini configuration."""
        config = MagicMock()
        config.api_key.get_secret_value.return_value = ""
        config.model_name = "gemini-2.5-flash-lite"
        config.max_requests_per_minute = 15
        config.max_tokens_per_minute = 250_000
        config.max_requests_per_day = 1000
        config.cache_ttl_seconds = 300
        config.temperature = 0.3
        config.max_output_tokens = 1024
        config.enable_llm = False
        return config

    @pytest.fixture
    def mock_groq_config(self):
        """Mock Groq configuration."""
        config = MagicMock()
        config.api_key.get_secret_value.return_value = ""
        config.model_name = "llama-3.3-70b-versatile"
        config.max_requests_per_minute = 30
        config.max_tokens_per_minute = 6000
        config.max_requests_per_day = 1000
        config.temperature = 0.3
        config.max_tokens = 1024
        config.enable_groq = False
        return config

    def test_llm_service_disabled_when_no_keys(self, mock_gemini_config, mock_groq_config):
        """Test LLM service disabled when no provider configured."""
        service = LLMService(mock_gemini_config, mock_groq_config)
        assert not service.is_enabled

    @pytest.mark.asyncio
    async def test_llm_service_returns_disabled_response(self, mock_gemini_config, mock_groq_config):
        """Test LLM service returns placeholder when disabled."""
        service = LLMService(mock_gemini_config, mock_groq_config)
        response = await service.generate("test prompt")

        assert response.content == "[LLM disabled]"
        assert response.provider == "none"
        assert response.cached is False

    def test_llm_service_json_parsing(self, mock_gemini_config, mock_groq_config):
        """Test JSON parsing from LLM responses."""
        service = LLMService(mock_gemini_config, mock_groq_config)

        # Clean JSON
        result = service._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

        # JSON in markdown code blocks
        result = service._parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_llm_service_json_parsing_invalid(self, mock_gemini_config, mock_groq_config):
        """Test JSON parsing handles invalid JSON."""
        service = LLMService(mock_gemini_config, mock_groq_config)

        with pytest.raises((ValueError, KeyError)):
            service._parse_json_response("not valid json")

    @pytest.mark.asyncio
    async def test_llm_service_uses_cache(self, mock_gemini_config, mock_groq_config):
        """Test LLM service uses cached responses."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = '{"result": "cached"}'

        service = LLMService(mock_gemini_config, mock_groq_config, cache=mock_cache)

        response = await service.generate("test prompt", cache_key="test_key")

        assert response.content == '{"result": "cached"}'
        assert response.cached is True
        assert response.provider == "cache"

    def test_provider_status(self, mock_gemini_config, mock_groq_config):
        """Test provider status reporting."""
        service = LLMService(mock_gemini_config, mock_groq_config)
        status = service.get_provider_status()

        assert status["enabled"] is False
        assert len(status["providers"]) == 0

    @pytest.mark.asyncio
    async def test_groq_primary_fallback_gemini(self, mock_gemini_config, mock_groq_config):
        """Test Groq is tried first, then falls back to Gemini."""
        service = LLMService(mock_gemini_config, mock_groq_config)

        # Mock Groq client and limiter
        service._groq_client = MagicMock()
        service._groq_limiter = RateLimiter(rpm=30, tpm=6000, rpd=1000)
        service.groq_config = mock_groq_config

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "groq response"
        mock_response.usage.total_tokens = 100

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            response = await service.generate("test prompt")

        assert response.provider == "groq"
        assert response.content == "groq response"


# ===== ContextAgent Tests =====


class TestContextAgent:
    """Test ContextAgent for sentiment analysis and confidence adjustment."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        llm = AsyncMock(spec=LLMService)
        llm.is_enabled = True
        llm.analyze_sentiment = AsyncMock(
            return_value={
                "sentiment_score": 0.5,
                "regime_tag": "Normal",
                "confidence": 0.8,
                "reasoning": "Test reasoning",
            }
        )
        return llm

    @pytest.fixture
    def context_agent(self, mock_llm_service):
        """Create ContextAgent with mock LLM."""
        return ContextAgent(llm_service=mock_llm_service, cache_ttl_minutes=5)

    def test_context_agent_initialization(self, context_agent):
        """Test ContextAgent initializes correctly."""
        assert context_agent.cache_ttl_minutes == 5
        assert context_agent.news_server is not None

    def test_adjust_confidence_bullish_sentiment_long(self, context_agent):
        """Test confidence adjustment for bullish sentiment + LONG signal."""
        context = MagicMock(spec=ContextAnalysis)
        context.sentiment_score = Decimal("0.5")  # Bullish
        context.confidence = Decimal("0.8")
        context.regime_tag = "Normal"

        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=context,
            signal_direction="LONG",
        )

        # Should increase confidence (bullish supports long)
        assert adjusted > Decimal("0.7")
        assert adjusted == Decimal("0.75")

    def test_adjust_confidence_bearish_sentiment_long(self, context_agent):
        """Test confidence adjustment for bearish sentiment + LONG signal."""
        context = MagicMock(spec=ContextAnalysis)
        context.sentiment_score = Decimal("-0.5")  # Bearish
        context.confidence = Decimal("0.8")
        context.regime_tag = "Normal"

        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=context,
            signal_direction="LONG",
        )

        # Should decrease confidence (bearish hurts long)
        assert adjusted < Decimal("0.7")
        assert adjusted == Decimal("0.60")

    def test_adjust_confidence_bearish_sentiment_short(self, context_agent):
        """Test confidence adjustment for bearish sentiment + SHORT signal."""
        context = MagicMock(spec=ContextAnalysis)
        context.sentiment_score = Decimal("-0.5")  # Bearish
        context.confidence = Decimal("0.8")
        context.regime_tag = "Normal"

        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=context,
            signal_direction="SHORT",
        )

        # Should increase confidence (bearish supports short)
        assert adjusted > Decimal("0.7")
        assert adjusted == Decimal("0.75")

    def test_adjust_confidence_high_impact_regime(self, context_agent):
        """Test confidence adjustment for high-impact regime tags."""
        context = MagicMock(spec=ContextAnalysis)
        context.sentiment_score = Decimal("0.0")  # Neutral
        context.confidence = Decimal("0.8")
        context.regime_tag = "Geopolitical_Risk"  # High impact

        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=context,
            signal_direction="LONG",
        )

        # Should decrease confidence (high-impact event = caution)
        assert adjusted < Decimal("0.7")

    def test_adjust_confidence_low_confidence_context_ignored(self, context_agent):
        """Test that low-confidence context analysis is ignored."""
        context = MagicMock(spec=ContextAnalysis)
        context.sentiment_score = Decimal("0.9")  # Very bullish
        context.confidence = Decimal("0.3")  # Low confidence
        context.regime_tag = "Normal"

        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=context,
            signal_direction="LONG",
        )

        # Should not change (low confidence context ignored)
        assert adjusted == Decimal("0.7")

    def test_adjust_confidence_none_context(self, context_agent):
        """Test that None context is handled gracefully."""
        adjusted = context_agent.adjust_confidence_for_context(
            base_confidence=Decimal("0.7"),
            context=None,
            signal_direction="LONG",
        )

        assert adjusted == Decimal("0.7")


# ===== LearningObserver Tests =====


class TestLearningObserver:
    """Test LearningObserver for RLM cycle."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        llm = AsyncMock(spec=LLMService)
        llm.is_enabled = True
        llm.generate_reflection = AsyncMock(
            return_value={
                "reflection": "Test reflection",
                "suggested_adjustment": {
                    "parameter": "rsi_oversold",
                    "direction": "relaxed",
                    "magnitude": "small",
                    "reason": "Test reason",
                },
            }
        )
        return llm

    @pytest.fixture
    def learning_observer(self, mock_llm_service):
        """Create LearningObserver with mock LLM."""
        return LearningObserver(
            llm_service=mock_llm_service,
            prediction_horizon_minutes=60,
            reflection_batch_size=5,
        )

    @pytest.mark.asyncio
    async def test_log_prediction(self, learning_observer):
        """Test logging a prediction."""
        signal = MagicMock(spec=Signal)
        signal.symbol = "USO"
        signal.direction = SignalDirection.LONG
        signal.strategy_name = "Test_Strategy"
        signal.suggested_entry = Decimal("75.50")
        signal.suggested_target = Decimal("77.00")
        signal.market_regime = None

        session = AsyncMock()

        log = await learning_observer.log_prediction(
            signal=signal,
            session=session,
            rsi=32.5,
            atr=1.25,
            sentiment_score=Decimal("0.3"),
            context_tag="Bullish_Momentum",
        )

        assert log.symbol == "USO"
        assert log.direction == "LONG"
        assert log.strategy_name == "Test_Strategy"
        assert log.entry_price == Decimal("75.50")
        assert log.predicted_target == Decimal("77.00")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_pending_observations_correct_prediction(
        self, learning_observer
    ):
        """Test observing a correct prediction."""
        log = MagicMock(spec=LearningLog)
        log.symbol = "USO"
        log.direction = "LONG"
        log.predicted_target = Decimal("77.00")
        log.entry_price = Decimal("75.00")
        log.observed_at = None
        log.predicted_at = datetime.now() - timedelta(hours=2)

        # Build mock chain: await session.execute() -> result -> .scalars() -> .all()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [log]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        session = AsyncMock()
        session.execute.return_value = execute_result

        current_prices = {"USO": Decimal("78.00")}  # Above target = correct

        updated = await learning_observer.check_pending_observations(
            session=session,
            current_prices=current_prices,
        )

        assert len(updated) == 1
        assert log.prediction_correct is True
        assert log.actual_price == Decimal("78.00")


# ===== Dynamic Thresholds Tests =====


class TestDynamicThresholds:
    """Test dynamic threshold calculation based on volatility."""

    def test_bollinger_bands_high_volatility_thresholds(self):
        """Test BB strategy uses stricter thresholds in high volatility."""
        strategy = BollingerBandsMeanReversion()

        atr = Decimal("3.50")
        current_price = Decimal("100.00")

        thresholds = strategy._get_dynamic_thresholds(atr, current_price)

        # High volatility (3.5%) -> stricter thresholds
        assert thresholds["rsi_oversold"] == 30.0
        assert thresholds["rsi_overbought"] == 70.0
        assert thresholds["volatility_pct"] == pytest.approx(3.5)

    def test_bollinger_bands_low_volatility_thresholds(self):
        """Test BB strategy uses relaxed thresholds in low volatility."""
        strategy = BollingerBandsMeanReversion()

        atr = Decimal("0.50")
        current_price = Decimal("100.00")

        thresholds = strategy._get_dynamic_thresholds(atr, current_price)

        # Low volatility (0.5%) -> relaxed thresholds
        assert thresholds["rsi_oversold"] == 40.0
        assert thresholds["rsi_overbought"] == 60.0
        assert thresholds["volatility_pct"] == 0.5

    def test_bollinger_bands_normal_volatility_thresholds(self):
        """Test BB strategy uses default thresholds in normal volatility."""
        strategy = BollingerBandsMeanReversion()

        atr = Decimal("2.00")
        current_price = Decimal("100.00")

        thresholds = strategy._get_dynamic_thresholds(atr, current_price)

        # Normal volatility (2.0%) -> default thresholds
        assert thresholds["rsi_oversold"] == 35.0
        assert thresholds["rsi_overbought"] == 65.0
        assert thresholds["volatility_pct"] == 2.0

    def test_rsi_strategy_dynamic_thresholds(self):
        """Test RSI strategy uses dynamic thresholds."""
        strategy = RSIOversoldOverbought()

        # High volatility
        thresholds_high = strategy._get_dynamic_thresholds(
            Decimal("3.50"), Decimal("100.00")
        )
        assert thresholds_high["rsi_oversold"] == 20.0
        assert thresholds_high["rsi_overbought"] == 80.0

        # Low volatility
        thresholds_low = strategy._get_dynamic_thresholds(
            Decimal("0.50"), Decimal("100.00")
        )
        assert thresholds_low["rsi_oversold"] == 30.0
        assert thresholds_low["rsi_overbought"] == 70.0

    def test_dynamic_thresholds_with_rlm_overrides(self):
        """Test thresholds respect RLM overrides."""
        strategy = BollingerBandsMeanReversion()

        overrides = {
            "rsi_oversold": "stricter",  # Should decrease by 5
            "rsi_overbought": "relaxed",  # Should decrease by 5
        }

        thresholds = strategy._get_dynamic_thresholds(
            Decimal("2.00"), Decimal("100.00"), overrides=overrides
        )

        # Base thresholds (35, 65) adjusted by overrides
        assert thresholds["rsi_oversold"] == 30.0  # 35 - 5
        assert thresholds["rsi_overbought"] == 60.0  # 65 - 5

    def test_dynamic_thresholds_bounds_enforcement(self):
        """Test thresholds stay within valid bounds."""
        strategy = BollingerBandsMeanReversion()

        # Test extreme override
        overrides = {
            "rsi_oversold": "relaxed",
            "rsi_overbought": "stricter",
        }

        # Apply overrides multiple times to test bounds
        for _ in range(10):
            thresholds = strategy._get_dynamic_thresholds(
                Decimal("0.50"), Decimal("100.00"), overrides=overrides
            )

            # Should be clamped to valid ranges
            assert 20.0 <= thresholds["rsi_oversold"] <= 45.0
            assert 55.0 <= thresholds["rsi_overbought"] <= 80.0
