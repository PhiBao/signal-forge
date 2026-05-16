"""
Async HTTP client for Polymarket Gamma API and CLOB API.
"""

import json
import httpx
from agents.config import settings
from agents.models import PredictionMarket, MarketOutcome, MarketStatus


def _parse_outcomes(item: dict) -> list[str]:
    outcomes_raw = item.get("outcomes", [])
    if isinstance(outcomes_raw, str):
        try:
            outcomes_raw = json.loads(outcomes_raw)
        except (json.JSONDecodeError, TypeError):
            return ["Yes", "No"]
    if not isinstance(outcomes_raw, list):
        return ["Yes", "No"]
    return [str(o) for o in outcomes_raw if o]


def _parse_prices(item: dict) -> dict[str, float]:
    prices_raw = item.get("outcomePrices") or item.get("outcome_prices", {})
    if isinstance(prices_raw, str):
        try:
            prices_raw = json.loads(prices_raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    if isinstance(prices_raw, list):
        outcome_names = _parse_outcomes(item)
        return {name: float(prices_raw[i]) for i, name in enumerate(outcome_names) if i < len(prices_raw)}
    if isinstance(prices_raw, dict):
        return {str(k): float(v) for k, v in prices_raw.items()}
    return {}


class PolymarketClient:
    def __init__(self):
        self.gamma_base = settings.poly_gamma_api
        self.clob_base = settings.poly_clob_api
        self._markets_cache: dict[str, PredictionMarket] = {}

    async def list_markets(self, limit: int = 50, offset: int = 0, active: bool = True) -> list[PredictionMarket]:
        params = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": "false",
            "order": "volume",
            "ascending": "false",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.gamma_base}/markets", params=params)
            resp.raise_for_status()
            data = resp.json()

        markets = []
        for item in data[:limit]:
            outcome_names = _parse_outcomes(item)
            prices = _parse_prices(item)
            volume = item.get("volume24hr") or item.get("volume", 0) or 0
            liquidity = item.get("liquidityNum") or item.get("liquidity", 0) or 0
            clob_ids = item.get("clobTokenIds", [])
            if isinstance(clob_ids, str):
                try:
                    clob_ids = json.loads(clob_ids)
                except (json.JSONDecodeError, TypeError):
                    clob_ids = []

            outcomes = []
            for i, name in enumerate(outcome_names):
                outcomes.append(MarketOutcome(
                    name=name,
                    price=prices.get(name, 0),
                    volume_24h=volume,
                ))

            market = PredictionMarket(
                id=str(item.get("id", "")),
                question=item.get("question", ""),
                description=item.get("description", "") or "",
                category=item.get("category", "") or "",
                tags=item.get("tags", []) or [],
                outcomes=outcomes,
                status=MarketStatus.ACTIVE if item.get("active") else MarketStatus.CLOSED,
                end_date=item.get("endDateIso") or item.get("end_date_iso"),
                volume_24h=volume,
                liquidity=liquidity,
                url=f"https://polymarket.com/market/{item.get('slug', '')}",
            )
            # Store clob token IDs for order placement
            market._clob_token_ids = clob_ids  # type: ignore
            markets.append(market)
            self._markets_cache[market.id] = market

        return markets

    async def get_market(self, market_id: str) -> PredictionMarket | None:
        if market_id in self._markets_cache:
            return self._markets_cache[market_id]

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.gamma_base}/markets/{market_id}")
            if resp.status_code != 200:
                return None
            item = resp.json()

        outcome_names = _parse_outcomes(item)
        prices = _parse_prices(item)

        outcomes = []
        for name in outcome_names:
            outcomes.append(MarketOutcome(
                name=name,
                price=prices.get(name, 0),
            ))

        market = PredictionMarket(
            id=item.get("id", ""),
            question=item.get("question", ""),
            description=item.get("description", "") or "",
            category=item.get("category", "") or "",
            tags=item.get("tags", []) or [],
            outcomes=outcomes,
            status=MarketStatus.ACTIVE if item.get("active") else MarketStatus.CLOSED,
            end_date=item.get("end_date_iso"),
            volume_24h=item.get("volume", 0) or 0,
            liquidity=item.get("liquidity", 0) or 0,
            url=f"https://polymarket.com/market/{item.get('slug', '')}",
        )
        self._markets_cache[market.id] = market
        return market

    async def get_midpoint(self, token_id: str) -> float:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.clob_base}/price", params={"token_id": token_id})
            if resp.status_code != 200:
                return 0
            data = resp.json()
            return float(data.get("mid", 0))

    async def get_orderbook(self, token_id: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.clob_base}/book", params={"token_id": token_id})
            if resp.status_code != 200:
                return {"bids": [], "asks": []}
            return resp.json()
