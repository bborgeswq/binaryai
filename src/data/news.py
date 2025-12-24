"""
News API Integration
Fetches crypto and financial news for market sentiment analysis
"""
import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class NewsArticle:
    """Represents a news article."""
    title: str
    description: str
    source: str
    url: str
    published_at: str
    sentiment: Optional[str] = None  # positive, negative, neutral
    relevance_score: float = 0.0
    symbols: List[str] = None

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = []


class NewsProvider:
    """Base class for news providers."""

    async def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
        raise NotImplementedError


class CryptoCompareNews(NewsProvider):
    """CryptoCompare News API (free, no API key required for basic usage)."""

    BASE_URL = "https://min-api.cryptocompare.com/data/v2/news/"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CRYPTOCOMPARE_API_KEY", "")

    async def fetch_news(self, query: str = None, limit: int = 20) -> List[NewsArticle]:
        """Fetch latest crypto news."""
        try:
            params = {"lang": "EN"}
            if self.api_key:
                params["api_key"] = self.api_key

            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []

                        for item in data.get("Data", [])[:limit]:
                            # Extract symbols from categories
                            categories = item.get("categories", "").upper()
                            symbols = []
                            for crypto in ["BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE"]:
                                if crypto in categories or crypto in item.get("title", "").upper():
                                    symbols.append(f"{crypto}/USDT")

                            articles.append(NewsArticle(
                                title=item.get("title", ""),
                                description=item.get("body", "")[:500],
                                source=item.get("source", "CryptoCompare"),
                                url=item.get("url", ""),
                                published_at=datetime.fromtimestamp(
                                    item.get("published_on", 0)
                                ).isoformat(),
                                symbols=symbols
                            ))

                        logger.info(f"Fetched {len(articles)} news articles from CryptoCompare")
                        return articles

        except Exception as e:
            logger.error(f"Error fetching CryptoCompare news: {e}")

        return []


class CoinGeckoNews(NewsProvider):
    """CoinGecko News (free, no API key required)."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    async def fetch_trending(self) -> List[Dict[str, Any]]:
        """Fetch trending coins (useful for market sentiment)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/search/trending") as response:
                    if response.status == 200:
                        data = await response.json()
                        coins = data.get("coins", [])

                        trending = []
                        for coin in coins[:10]:
                            item = coin.get("item", {})
                            trending.append({
                                "name": item.get("name"),
                                "symbol": item.get("symbol", "").upper(),
                                "market_cap_rank": item.get("market_cap_rank"),
                                "price_btc": item.get("price_btc", 0),
                                "score": item.get("score", 0)
                            })

                        logger.info(f"Fetched {len(trending)} trending coins from CoinGecko")
                        return trending

        except Exception as e:
            logger.error(f"Error fetching CoinGecko trending: {e}")

        return []

    async def fetch_news(self, query: str = None, limit: int = 10) -> List[NewsArticle]:
        """CoinGecko doesn't have a news endpoint, return empty."""
        return []


class AlphaVantageNews(NewsProvider):
    """Alpha Vantage News API (requires free API key)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY", "")

    async def fetch_news(self, query: str = "crypto", limit: int = 20) -> List[NewsArticle]:
        """Fetch news from Alpha Vantage."""
        if not self.api_key:
            logger.warning("Alpha Vantage API key not set")
            return []

        try:
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": query,
                "apikey": self.api_key,
                "limit": limit
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []

                        for item in data.get("feed", [])[:limit]:
                            # Get sentiment
                            sentiment_score = float(item.get("overall_sentiment_score", 0))
                            if sentiment_score > 0.15:
                                sentiment = "positive"
                            elif sentiment_score < -0.15:
                                sentiment = "negative"
                            else:
                                sentiment = "neutral"

                            articles.append(NewsArticle(
                                title=item.get("title", ""),
                                description=item.get("summary", "")[:500],
                                source=item.get("source", "Alpha Vantage"),
                                url=item.get("url", ""),
                                published_at=item.get("time_published", ""),
                                sentiment=sentiment,
                                relevance_score=float(item.get("relevance_score", 0))
                            ))

                        logger.info(f"Fetched {len(articles)} news articles from Alpha Vantage")
                        return articles

        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage news: {e}")

        return []


class NewsAggregator:
    """Aggregates news from multiple sources."""

    def __init__(self):
        self.providers = [
            CryptoCompareNews(),
            CoinGeckoNews(),
        ]

        # Add Alpha Vantage if API key is available
        if os.getenv("ALPHAVANTAGE_API_KEY"):
            self.providers.append(AlphaVantageNews())

        self.coingecko = CoinGeckoNews()

    async def fetch_all_news(self, limit: int = 30) -> List[NewsArticle]:
        """Fetch news from all providers."""
        all_articles = []

        tasks = [provider.fetch_news(limit=limit) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"News provider error: {result}")

        # Sort by published date (most recent first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            if article.title not in seen_titles:
                seen_titles.add(article.title)
                unique_articles.append(article)

        return unique_articles[:limit]

    async def fetch_news_for_symbol(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
        """Fetch news relevant to a specific symbol."""
        all_news = await self.fetch_all_news(limit=50)

        # Extract base symbol (e.g., "BTC" from "BTC/USDT")
        base_symbol = symbol.split("/")[0].upper()

        # Filter articles that mention this symbol
        relevant = [
            article for article in all_news
            if base_symbol in article.title.upper()
            or base_symbol in article.description.upper()
            or any(base_symbol in s.upper() for s in article.symbols)
        ]

        return relevant[:limit]

    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """Get trending coins from CoinGecko."""
        return await self.coingecko.fetch_trending()

    async def get_market_sentiment(self) -> Dict[str, Any]:
        """Analyze overall market sentiment from news."""
        articles = await self.fetch_all_news(limit=30)

        if not articles:
            return {
                "overall": "neutral",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "confidence": 0.0
            }

        # Simple keyword-based sentiment analysis
        positive_keywords = [
            "bullish", "surge", "rally", "gains", "growth", "soars",
            "breakthrough", "adoption", "partnership", "upgrade",
            "milestone", "record high", "moon", "pump"
        ]
        negative_keywords = [
            "bearish", "crash", "plunge", "dump", "selloff", "drop",
            "hack", "scam", "fraud", "ban", "regulation", "lawsuit",
            "warning", "risk", "fear", "correction"
        ]

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in articles:
            text = (article.title + " " + article.description).lower()

            pos_score = sum(1 for kw in positive_keywords if kw in text)
            neg_score = sum(1 for kw in negative_keywords if kw in text)

            if article.sentiment == "positive" or pos_score > neg_score:
                positive_count += 1
            elif article.sentiment == "negative" or neg_score > pos_score:
                negative_count += 1
            else:
                neutral_count += 1

        total = positive_count + negative_count + neutral_count

        if positive_count > negative_count * 1.5:
            overall = "bullish"
        elif negative_count > positive_count * 1.5:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "confidence": max(positive_count, negative_count) / total if total > 0 else 0,
            "total_articles": total
        }

    def get_news_context_for_ai(self, articles: List[NewsArticle]) -> str:
        """Generate news context string for AI decision making."""
        if not articles:
            return "No recent news available."

        context = "RECENT NEWS:\n"
        for i, article in enumerate(articles[:5], 1):
            sentiment_str = f" [{article.sentiment}]" if article.sentiment else ""
            context += f"{i}. {article.title}{sentiment_str}\n"
            context += f"   Source: {article.source} | {article.published_at[:10]}\n"

        return context


# Convenience functions
async def get_crypto_news(limit: int = 20) -> List[NewsArticle]:
    """Get latest crypto news."""
    aggregator = NewsAggregator()
    return await aggregator.fetch_all_news(limit)


async def get_market_sentiment() -> Dict[str, Any]:
    """Get current market sentiment."""
    aggregator = NewsAggregator()
    return await aggregator.get_market_sentiment()


async def get_news_for_symbol(symbol: str, limit: int = 10) -> List[NewsArticle]:
    """Get news for a specific symbol."""
    aggregator = NewsAggregator()
    return await aggregator.fetch_news_for_symbol(symbol, limit)
