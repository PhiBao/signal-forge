"""
Polymarket CLOB trading client.
Places real orders on Polymarket via CLOB API.
Uses the connected Arc wallet for signing — no separate private key needed.
Docs: https://docs.polymarket.com/
"""

import hashlib
import hmac
import time
import logging
import httpx
from agents.config import settings

logger = logging.getLogger(__name__)


class PolymarketCLOBClient:
    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.base_url = settings.poly_clob_api
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.has_credentials = bool(api_key and api_secret)

    async def get_orderbook(self, token_id: str) -> dict:
        """Get orderbook for a token."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/book", params={"token_id": token_id})
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"CLOB orderbook failed: {e}")
        return {"bids": [], "asks": []}

    async def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/price", params={"token_id": token_id})
                if resp.status_code == 200:
                    return float(resp.json().get("mid", 0))
        except Exception as e:
            logger.error(f"CLOB midpoint failed: {e}")
        return 0

    async def place_order(
        self,
        order: dict,
        signature: str,
    ) -> dict:
        """
        Place an order on Polymarket CLOB.
        order: {
            "order": { ... },
            "owner": "0x...",
            "orderType": "GTC" | "GTD" | "FOK",
        }
        signature: EIP-712 signature of the order
        """
        if not self.has_credentials:
            logger.warning("No CLOB credentials configured, skipping order placement")
            return {"status": "skipped", "reason": "no_credentials"}

        timestamp = str(int(time.time()))
        path = "/order"

        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}{path}",
                    json=order,
                    headers=headers,
                )
                return resp.json()
        except Exception as e:
            logger.error(f"CLOB order placement failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an order."""
        if not self.has_credentials:
            return {"status": "skipped"}

        timestamp = str(int(time.time()))
        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(
                    f"{self.base_url}/order/{order_id}",
                    headers=headers,
                )
                return resp.json()
        except Exception as e:
            logger.error(f"CLOB cancel failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def get_orders(self) -> list:
        """Get open orders."""
        if not self.has_credentials:
            return []

        timestamp = str(int(time.time()))
        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/data/orders", headers=headers)
                return resp.json().get("orders", [])
        except Exception:
            return []

    async def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/price", params={"token_id": token_id})
            if resp.status_code != 200:
                return 0
            data = resp.json()
            return float(data.get("mid", 0))

    async def get_orderbook(self, token_id: str) -> dict:
        """Get orderbook for a token."""
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/book", params={"token_id": token_id})
            if resp.status_code != 200:
                return {"bids": [], "asks": []}
            return resp.json()

    async def place_order(
        self,
        order: dict,
        signature: str,
    ) -> dict:
        """
        Place an order on Polymarket CLOB.
        order: {
            "order": {
                "salt": "...",
                "maker": "0x...",
                "signer": "0x...",
                "taker": "0x...",
                "tokenId": "...",
                "makerAmount": "...",
                "takerAmount": "...",
                "expiration": "...",
                "nonce": "...",
                "feeRateBps": "...",
                "side": "BUY" | "SELL",
                "signatureType": 0 | 1 | 2,
            },
            "owner": "0x...",
            "orderType": "GTC" | "GTD" | "FOK",
        }
        """
        if not self.has_credentials:
            logger.warning("No CLOB credentials configured, skipping order placement")
            return {"status": "skipped", "reason": "no_credentials"}

        import httpx
        timestamp = str(int(time.time()))
        path = "/order"
        body = ""  # Signature is in header, body is empty for GET-style auth

        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}{path}",
                    json=order,
                    headers=headers,
                )
                return resp.json()
        except Exception as e:
            logger.error(f"CLOB order placement failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an order."""
        if not self.has_credentials:
            return {"status": "skipped"}

        import httpx
        timestamp = str(int(time.time()))
        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(
                    f"{self.base_url}/order/{order_id}",
                    headers=headers,
                )
                return resp.json()
        except Exception as e:
            logger.error(f"CLOB cancel failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def get_orders(self) -> list:
        """Get open orders."""
        if not self.has_credentials:
            return []

        import httpx
        timestamp = str(int(time.time()))
        headers = {
            "POLY_ADDRESS": self.api_key,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/data/orders", headers=headers)
                return resp.json().get("orders", [])
        except Exception:
            return []
