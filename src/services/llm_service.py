"""Multi-provider LLM service with Groq (primary) and Gemini (fallback).

Supports rate limiting, Redis caching, automatic failover, and structured prompts
for sentiment analysis and RLM reflection.
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from src.core.config import GeminiConfig, GroqConfig
from src.services.redis_cache import RedisCache

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM service."""

    content: str
    model: str
    provider: str  # "groq" or "gemini"
    tokens_used: int
    cached: bool
    latency_ms: float


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rpm: int, tpm: int, rpd: int):
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        self._minute_requests: deque[float] = deque()
        self._minute_tokens: deque[tuple[float, int]] = deque()
        self._day_requests: deque[float] = deque()

    async def acquire(self, estimated_tokens: int = 500) -> None:
        """Wait until rate limit allows request."""
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400

        while self._minute_requests and self._minute_requests[0] < minute_ago:
            self._minute_requests.popleft()
        while self._minute_tokens and self._minute_tokens[0][0] < minute_ago:
            self._minute_tokens.popleft()
        while self._day_requests and self._day_requests[0] < day_ago:
            self._day_requests.popleft()

        current_rpm = len(self._minute_requests)
        current_tpm = sum(t[1] for t in self._minute_tokens)
        current_rpd = len(self._day_requests)

        if current_rpm >= self.rpm or current_tpm + estimated_tokens > self.tpm:
            wait_time = 60 - (now - self._minute_requests[0]) if self._minute_requests else 60
            logger.warning(f"Rate limit approaching, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

        if current_rpd >= self.rpd:
            raise Exception("Daily rate limit exceeded")

    def record_request(self, tokens: int) -> None:
        """Record a completed request."""
        now = time.time()
        self._minute_requests.append(now)
        self._minute_tokens.append((now, tokens))
        self._day_requests.append(now)

    @property
    def daily_remaining(self) -> int:
        """Estimate remaining daily requests."""
        now = time.time()
        day_ago = now - 86400
        while self._day_requests and self._day_requests[0] < day_ago:
            self._day_requests.popleft()
        return max(0, self.rpd - len(self._day_requests))


class LLMService:
    """
    Multi-provider async LLM service.

    Provider priority: Groq (primary) -> Gemini (fallback)

    Features:
    - Automatic failover between providers
    - Per-provider rate limiting
    - Redis caching for repeated queries
    - Structured prompt templates for sentiment and reflection
    """

    def __init__(
        self,
        gemini_config: GeminiConfig,
        groq_config: GroqConfig | None = None,
        cache: RedisCache | None = None,
    ):
        self.gemini_config = gemini_config
        self.groq_config = groq_config
        self.cache = cache

        # Provider clients
        self._gemini_model: Any = None
        self._groq_client: Any = None

        # Per-provider rate limiters
        self._gemini_limiter = RateLimiter(
            rpm=gemini_config.max_requests_per_minute,
            tpm=gemini_config.max_tokens_per_minute,
            rpd=gemini_config.max_requests_per_day,
        )
        self._groq_limiter: RateLimiter | None = None

        # Initialize providers
        if groq_config and groq_config.enable_groq and groq_config.api_key.get_secret_value():
            self._init_groq(groq_config)

        if gemini_config.enable_llm and gemini_config.api_key.get_secret_value():
            self._init_gemini(gemini_config)

        # Log provider status
        providers = []
        if self._groq_client:
            providers.append(f"Groq ({groq_config.model_name})")
        if self._gemini_model:
            providers.append(f"Gemini ({gemini_config.model_name})")
        if providers:
            logger.info(f"LLM providers initialized: {' -> '.join(providers)}")
        else:
            logger.warning("No LLM providers configured - LLM features disabled")

    def _init_groq(self, config: GroqConfig) -> None:
        """Initialize Groq client."""
        try:
            from groq import Groq

            self._groq_client = Groq(api_key=config.api_key.get_secret_value())
            self._groq_limiter = RateLimiter(
                rpm=config.max_requests_per_minute,
                tpm=config.max_tokens_per_minute,
                rpd=config.max_requests_per_day,
            )
            logger.info(f"Groq client initialized: {config.model_name}")
        except ImportError:
            logger.warning("groq package not installed, skipping Groq provider")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")

    def _init_gemini(self, config: GeminiConfig) -> None:
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=config.api_key.get_secret_value())
            self._gemini_model = genai.GenerativeModel(
                config.model_name,
                generation_config={
                    "temperature": config.temperature,
                    "max_output_tokens": config.max_output_tokens,
                },
            )
            logger.info(f"Gemini client initialized: {config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if at least one LLM provider is available."""
        return self._groq_client is not None or self._gemini_model is not None

    async def generate(
        self,
        prompt: str,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
    ) -> LLMResponse:
        """
        Generate response from LLM with automatic failover.

        Tries Groq first (faster), falls back to Gemini.
        """
        # Check cache first (works even when providers are disabled)
        if cache_key and self.cache:
            cached = self.cache.get(f"llm:{cache_key}")
            if cached:
                logger.debug(f"LLM cache hit: {cache_key}")
                return LLMResponse(
                    content=cached,
                    model="cached",
                    provider="cache",
                    tokens_used=0,
                    cached=True,
                    latency_ms=0,
                )

        if not self.is_enabled:
            return LLMResponse(
                content="[LLM disabled]",
                model="none",
                provider="none",
                tokens_used=0,
                cached=False,
                latency_ms=0,
            )

        # Try Groq first (primary), then Gemini (fallback)
        last_error = None

        if self._groq_client and self._groq_limiter and self._groq_limiter.daily_remaining > 0:
            try:
                response = await self._call_groq(prompt)
                self._cache_response(cache_key, response.content, cache_ttl)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"Groq failed, falling back to Gemini: {e}")

        if self._gemini_model and self._gemini_limiter.daily_remaining > 0:
            try:
                response = await self._call_gemini(prompt)
                self._cache_response(cache_key, response.content, cache_ttl)
                return response
            except Exception as e:
                last_error = e
                logger.error(f"Gemini also failed: {e}")

        if last_error:
            raise last_error
        raise Exception("No LLM providers available")

    async def _call_groq(self, prompt: str) -> LLMResponse:
        """Call Groq API."""
        await self._groq_limiter.acquire(estimated_tokens=len(prompt) // 4 + 500)
        start_time = time.time()

        response = await asyncio.to_thread(
            self._groq_client.chat.completions.create,
            model=self.groq_config.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.groq_config.temperature,
            max_tokens=self.groq_config.max_tokens,
        )

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        self._groq_limiter.record_request(tokens_used)
        latency_ms = (time.time() - start_time) * 1000

        logger.info(f"Groq response: {tokens_used} tokens, {latency_ms:.0f}ms")
        return LLMResponse(
            content=content,
            model=self.groq_config.model_name,
            provider="groq",
            tokens_used=tokens_used,
            cached=False,
            latency_ms=latency_ms,
        )

    async def _call_gemini(self, prompt: str) -> LLMResponse:
        """Call Gemini API."""
        await self._gemini_limiter.acquire(estimated_tokens=len(prompt) // 4 + 500)
        start_time = time.time()

        response = await asyncio.to_thread(self._gemini_model.generate_content, prompt)
        content = response.text
        tokens_used = (
            response.usage_metadata.total_token_count
            if hasattr(response, "usage_metadata") and response.usage_metadata
            else 0
        )
        self._gemini_limiter.record_request(tokens_used)
        latency_ms = (time.time() - start_time) * 1000

        logger.info(f"Gemini response: {tokens_used} tokens, {latency_ms:.0f}ms")
        return LLMResponse(
            content=content,
            model=self.gemini_config.model_name,
            provider="gemini",
            tokens_used=tokens_used,
            cached=False,
            latency_ms=latency_ms,
        )

    def _cache_response(self, cache_key: str | None, content: str, cache_ttl: int | None) -> None:
        """Cache LLM response if cache is available."""
        if cache_key and self.cache:
            ttl = cache_ttl or self.gemini_config.cache_ttl_seconds
            self.cache.set(f"llm:{cache_key}", content, ttl=ttl)

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from LLM response, handling markdown code fences."""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)

    async def analyze_sentiment(
        self,
        symbol: str,
        headlines: list[str],
        market_metrics: dict,
    ) -> dict:
        """
        Analyze sentiment from news headlines.

        Returns dict with sentiment_score (-1 to 1), regime_tag, confidence, reasoning.
        """
        prompt = f"""Analyze the sentiment for {symbol} based on these inputs:

NEWS HEADLINES:
{chr(10).join(f"- {h}" for h in headlines[:10])}

MARKET METRICS:
- Current Price: ${market_metrics.get('price', 'N/A')}
- Daily Change: {market_metrics.get('daily_change_pct', 'N/A')}%
- Volume vs Avg: {market_metrics.get('volume_ratio', 'N/A')}x
- RSI: {market_metrics.get('rsi', 'N/A')}

RESPOND IN JSON FORMAT ONLY:
{{
    "sentiment_score": <float from -1.0 (very bearish) to 1.0 (very bullish)>,
    "regime_tag": "<one of: Geopolitical_Risk, Supply_Shock, Demand_Surge, Weather_Event, Inventory_Report, Technical_Breakout, Normal>",
    "confidence": <float from 0.0 to 1.0>,
    "reasoning": "<one sentence explanation>"
}}"""

        cache_key = f"sentiment:{symbol}:{hash(tuple(headlines[:5]))}"
        response = await self.generate(prompt, cache_key=cache_key)

        try:
            return self._parse_json_response(response.content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response.content[:100]}")
            return {
                "sentiment_score": 0.0,
                "regime_tag": "Normal",
                "confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
            }

    async def generate_reflection(
        self,
        prediction: dict,
        actual_outcome: dict,
        historical_accuracy: dict,
    ) -> dict:
        """
        Generate reflection on prediction accuracy for RLM.

        Returns dict with reflection text and suggested adjustments.
        """
        prompt = f"""You are a trading strategy analyst. Reflect on this prediction:

PREDICTION:
- Symbol: {prediction.get('symbol')}
- Direction: {prediction.get('direction')}
- Strategy: {prediction.get('strategy')}
- Predicted Target: ${prediction.get('target')}
- Entry Price: ${prediction.get('entry')}

ACTUAL OUTCOME:
- Exit Price: ${actual_outcome.get('exit_price')}
- Prediction Correct: {actual_outcome.get('correct')}
- P&L: {actual_outcome.get('pnl_pct')}%

HISTORICAL ACCURACY (this strategy):
- Win Rate: {historical_accuracy.get('win_rate', 'N/A')}%
- Avg Win: {historical_accuracy.get('avg_win', 'N/A')}%
- Avg Loss: {historical_accuracy.get('avg_loss', 'N/A')}%

RESPOND IN JSON FORMAT ONLY:
{{
    "reflection": "<2-3 sentences analyzing why prediction was correct/incorrect>",
    "suggested_adjustment": {{
        "parameter": "<parameter to adjust or 'none'>",
        "direction": "<increase/decrease/none>",
        "magnitude": "<small/medium/large/none>",
        "reason": "<one sentence justification>"
    }}
}}"""

        response = await self.generate(prompt)

        try:
            return self._parse_json_response(response.content)
        except json.JSONDecodeError:
            return {
                "reflection": response.content[:500],
                "suggested_adjustment": {"parameter": "none"},
            }

    def get_provider_status(self) -> dict:
        """Get status of all LLM providers."""
        status = {"enabled": self.is_enabled, "providers": {}}

        if self._groq_client and self._groq_limiter:
            status["providers"]["groq"] = {
                "available": True,
                "model": self.groq_config.model_name,
                "daily_remaining": self._groq_limiter.daily_remaining,
            }

        if self._gemini_model:
            status["providers"]["gemini"] = {
                "available": True,
                "model": self.gemini_config.model_name,
                "daily_remaining": self._gemini_limiter.daily_remaining,
            }

        return status
