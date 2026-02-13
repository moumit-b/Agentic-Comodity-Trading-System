"""MCP server for multi-source news aggregation.

Aggregates news from:
- Finnhub (commodity-specific news)
- Reddit (social sentiment from r/oil, r/commodities)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import praw

logger = logging.getLogger(__name__)


class NewsMCPServer:
    """
    MCP server for news aggregation from multiple sources.

    Exposes tools:
    - get_finnhub_news: Fetch Finnhub news for symbol
    - get_reddit_sentiment: Get Reddit sentiment
    - aggregate_news: Combine all sources
    """

    def __init__(self):
        """Initialize news aggregation service."""
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "TradingBot/1.0")

        # Initialize Reddit client if credentials available
        self.reddit = None
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent,
                )
                logger.info("Reddit client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit client: {e}")

    async def get_finnhub_news(
        self,
        symbol: str,
        lookback_days: int = 1,
    ) -> dict[str, Any]:
        """
        Fetch news from Finnhub API.

        Args:
            symbol: Stock symbol (e.g., USO, UNG)
            lookback_days: How many days of news to fetch

        Returns:
            Dict with headlines, summaries, and sources
        """
        if not self.finnhub_key:
            return {"headlines": [], "source": "finnhub", "error": "No API key"}

        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": symbol,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "token": self.finnhub_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        headlines = [
                            {
                                "headline": article.get("headline", ""),
                                "summary": article.get("summary", "")[:200],
                                "source": article.get("source", "Unknown"),
                                "datetime": article.get("datetime", 0),
                            }
                            for article in data[:20]  # Limit to 20 most recent
                        ]

                        logger.info(f"Fetched {len(headlines)} Finnhub news for {symbol}")
                        return {
                            "headlines": headlines,
                            "source": "finnhub",
                            "count": len(headlines),
                        }
                    else:
                        logger.error(f"Finnhub API error: {response.status}")
                        return {"headlines": [], "source": "finnhub", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Failed to fetch Finnhub news: {e}")
            return {"headlines": [], "source": "finnhub", "error": str(e)}

    async def get_reddit_sentiment(
        self,
        symbol: str,
        subreddits: list[str] | None = None,
        lookback_hours: int = 24,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Fetch Reddit posts and sentiment.

        Args:
            symbol: Stock symbol or commodity name
            subreddits: List of subreddits to search (defaults to commodity-focused)
            lookback_hours: How far back to look
            limit: Max posts to fetch per subreddit

        Returns:
            Dict with posts, sentiment indicators
        """
        if not self.reddit:
            return {"posts": [], "source": "reddit", "error": "Reddit client not initialized"}

        if subreddits is None:
            # Default commodity-focused subreddits
            subreddits = ["oil", "commodities", "energy", "trading"]

        # Map symbol to search terms
        search_terms = {
            "USO": ["USO", "crude oil", "WTI", "oil"],
            "UNG": ["UNG", "natural gas", "gas"],
        }
        keywords = search_terms.get(symbol, [symbol.lower()])

        all_posts = []
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)

        try:
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Search for keywords in hot and new posts
                    for keyword in keywords:
                        for submission in subreddit.search(keyword, limit=limit // len(keywords), time_filter="day"):
                            post_time = datetime.fromtimestamp(submission.created_utc)
                            if post_time < cutoff_time:
                                continue

                            all_posts.append(
                                {
                                    "title": submission.title,
                                    "score": submission.score,
                                    "num_comments": submission.num_comments,
                                    "upvote_ratio": submission.upvote_ratio,
                                    "created_utc": submission.created_utc,
                                    "subreddit": subreddit_name,
                                    "url": submission.url,
                                }
                            )

                except Exception as e:
                    logger.warning(f"Failed to fetch from r/{subreddit_name}: {e}")

            # Calculate basic sentiment indicators
            if all_posts:
                avg_score = sum(p["score"] for p in all_posts) / len(all_posts)
                avg_upvote_ratio = sum(p["upvote_ratio"] for p in all_posts) / len(all_posts)

                # Simple sentiment: high scores + high upvote ratio = bullish
                sentiment = "bullish" if avg_score > 10 and avg_upvote_ratio > 0.7 else "neutral"
                if avg_score < 5 or avg_upvote_ratio < 0.5:
                    sentiment = "bearish"
            else:
                sentiment = "neutral"
                avg_score = 0
                avg_upvote_ratio = 0.5

            logger.info(f"Fetched {len(all_posts)} Reddit posts for {symbol}, sentiment: {sentiment}")
            return {
                "posts": all_posts[:20],  # Return top 20
                "source": "reddit",
                "count": len(all_posts),
                "sentiment": sentiment,
                "avg_score": avg_score,
                "avg_upvote_ratio": avg_upvote_ratio,
            }

        except Exception as e:
            logger.error(f"Failed to fetch Reddit sentiment: {e}")
            return {"posts": [], "source": "reddit", "error": str(e)}

    async def aggregate_news(
        self,
        symbol: str,
        lookback_days: int = 1,
    ) -> dict[str, Any]:
        """
        Aggregate news from all sources.

        Args:
            symbol: Stock symbol
            lookback_days: Lookback period

        Returns:
            Unified dict with all news sources combined
        """
        # Fetch from all sources concurrently
        finnhub_task = asyncio.create_task(self.get_finnhub_news(symbol, lookback_days))
        reddit_task = asyncio.create_task(self.get_reddit_sentiment(symbol, lookback_hours=lookback_days * 24))

        finnhub_news, reddit_sentiment = await asyncio.gather(finnhub_task, reddit_task)

        # Combine headlines from all sources
        all_headlines = []

        # Finnhub headlines
        for article in finnhub_news.get("headlines", []):
            all_headlines.append(
                {
                    "text": article["headline"],
                    "source": "finnhub",
                    "summary": article.get("summary", ""),
                    "datetime": article.get("datetime", 0),
                }
            )

        # Reddit posts as "headlines"
        for post in reddit_sentiment.get("posts", []):
            all_headlines.append(
                {
                    "text": post["title"],
                    "source": "reddit",
                    "score": post["score"],
                    "upvote_ratio": post["upvote_ratio"],
                    "datetime": post.get("created_utc", 0),
                }
            )

        # Sort by datetime (most recent first)
        all_headlines.sort(key=lambda x: x.get("datetime", 0), reverse=True)

        return {
            "symbol": symbol,
            "total_headlines": len(all_headlines),
            "headlines": all_headlines[:30],  # Return top 30
            "sources": {
                "finnhub": finnhub_news.get("count", 0),
                "reddit": reddit_sentiment.get("count", 0),
            },
            "reddit_sentiment": reddit_sentiment.get("sentiment", "neutral"),
            "fetched_at": datetime.now().isoformat(),
        }


# MCP Server entry point
if __name__ == "__main__":
    # This would be run as an MCP server
    # For now, it's imported as a module by ContextAgent
    server = NewsMCPServer()
    print("News MCP Server initialized")
