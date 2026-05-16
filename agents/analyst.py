"""
DGrid AI-powered market analyst.
Uses DGrid's OpenAI-compatible API to generate structured reasoning traces.
"""

import json
import logging
from openai import AsyncOpenAI
from agents.config import settings
from agents.models import PredictionMarket

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SignalForge, an autonomous prediction market analyst.
Your job is to identify +EV betting opportunities on Polymarket.

Analyze each market and provide:
1. Your estimated true probability of the outcome
2. Confidence in your estimate (0-100)
3. Key factors supporting your view
4. Risks and uncertainties
5. A clear BUY/SELL/HOLD recommendation

Consider:
- Market price vs your estimate (edge)
- Volume and liquidity (can you actually trade this size?)
- Time horizon (how long until resolution?)
- Information asymmetry (do you know something the market doesn't?)
- Catalyst events (what could change the probability?)

Be concise. Be specific. Never hedge with "it depends."
Give a number, give a direction, give reasoning."""


ANALYSIS_PROMPT = """Analyze this prediction market for +EV opportunities.

MARKET: {question}
CATEGORY: {category}
TAGS: {tags}
CURRENT PRICE (Yes): {yes_price}
CURRENT PRICE (No): {no_price}
24H VOLUME: ${volume_24h:,.0f}
LIQUIDITY: ${liquidity:,.0f}
TIME TO RESOLUTION: {time_info}

{news_context}

Respond in this EXACT JSON format:
{{
  "estimated_probability_yes": 0.72,
  "confidence": 65,
  "recommendation": "BUY_YES",
  "edge_pct": 12.0,
  "key_factors": ["factor 1", "factor 2"],
  "risks": ["risk 1", "risk 2"],
  "analysis": "2-3 sentence reasoning explaining your view"
}}

recommendation must be one of: BUY_YES, BUY_NO, SELL_YES, SELL_NO, HOLD
estimated_probability_yes must be between 0.01 and 0.99
confidence must be between 10 and 95
edge_pct is your estimated_probability minus market_implied_probability (can be negative)"""


class DGridAnalyst:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.dgrid_api_key,
            base_url="https://api.dgrid.ai/v1",
        )
        self.model = settings.dgrid_model
        self._call_count = 0

    async def analyze_market(
        self,
        market: PredictionMarket,
        news_context: str = "",
        time_info: str = "unknown",
    ) -> dict | None:
        yes_price = market.outcomes[0].price if len(market.outcomes) > 0 else 0.5
        no_price = market.outcomes[1].price if len(market.outcomes) > 1 else 1 - yes_price

        prompt = ANALYSIS_PROMPT.format(
            question=market.question,
            category=market.category,
            tags=", ".join(market.tags[:5]),
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=market.volume_24h,
            liquidity=market.liquidity,
            time_info=time_info,
            news_context=f"RECENT NEWS:\n{news_context}" if news_context else "",
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            self._call_count += 1
            content = resp.choices[0].message.content.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            result["model_used"] = self.model
            result["call_count"] = self._call_count
            return result

        except Exception as e:
            logger.error(f"DGrid analysis failed for market {market.id}: {e}")
            return None

    async def batch_analyze(
        self,
        markets: list[PredictionMarket],
        news_context: str = "",
        max_concurrent: int = 5,
    ) -> list[tuple[PredictionMarket, dict | None]]:
        import asyncio

        async def analyze_one(m: PredictionMarket) -> tuple:
            result = await self.analyze_market(m, news_context)
            return (m, result)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited(m: PredictionMarket) -> tuple:
            async with semaphore:
                return await analyze_one(m)

        tasks = [limited(m) for m in markets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = []
        for r in results:
            if isinstance(r, Exception):
                continue
            valid.append(r)

        return valid
