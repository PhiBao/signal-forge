"""
Scout: coordinates market fetching + news gathering for analysis context.
"""

import httpx
from agents.polymarket import PolymarketClient
from agents.models import PredictionMarket


class NewsFetcher:
    """Fetches relevant news context for market analysis."""

    RSS_FEEDS = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ]

    async def fetch_headlines(self, limit: int = 15) -> str:
        headlines = []
        async with httpx.AsyncClient(timeout=10) as client:
            for feed_url in self.RSS_FEEDS:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code == 200:
                        titles = self._parse_rss_titles(resp.text)
                        headlines.extend(titles)
                except Exception:
                    continue

        return "\n".join(f"- {h}" for h in headlines[:limit])

    def _parse_rss_titles(self, xml: str) -> list[str]:
        import re
        titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", xml)
        if not titles:
            titles = re.findall(r"<title>(.+?)</title>", xml)
        return [t for t in titles if t and t.lower() not in ("rss", "news")]


class ScoutAgent:
    def __init__(self):
        self.poly = PolymarketClient()
        self.news = NewsFetcher()
        self._markets_cache: list[PredictionMarket] = []

    async def scan(self, limit: int = 50) -> tuple[list[PredictionMarket], str]:
        """Fetch markets + news in parallel."""
        import asyncio
        markets_task = self.poly.list_markets(limit=limit)
        news_task = self.news.fetch_headlines()

        markets, news = await asyncio.gather(markets_task, news_task)
        self._markets_cache = markets
        return markets, news

    async def refresh_markets(self, limit: int = 50) -> list[PredictionMarket]:
        self._markets_cache = await self.poly.list_markets(limit=limit)
        return self._markets_cache

    @property
    def markets(self) -> list[PredictionMarket]:
        return self._markets_cache
