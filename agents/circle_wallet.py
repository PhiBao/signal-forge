"""
Circle Wallet integration.
Handles wallet info, balances via Circle Payments API.
Docs: https://developers.circle.com/api-reference/payments
"""

import os
import logging
import httpx
from dotenv import load_dotenv
load_dotenv()

from agents.config import settings

logger = logging.getLogger(__name__)


class CircleWalletManager:
    def __init__(self):
        self.api_key = settings.circle_api_key
        self.connected = False
        self.wallet_id = None
        self.wallet_address = None
        self.wallet_type = None
        self._balance = 0.0

        if not self.api_key:
            logger.warning("Circle API key not configured")
            return

        self.wallet_id = settings.circle_wallet_id
        if self.wallet_id:
            self._load_wallet_info()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _load_wallet_info(self):
        """Load wallet info from Circle API."""
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"https://api-sandbox.circle.com/v1/wallets/{self.wallet_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    self.wallet_address = data.get("address")
                    self.wallet_type = data.get("type", "merchant")
                    self.connected = True
                    balances = data.get("balances", [])
                    for b in balances:
                        if b.get("currency") == "USDC":
                            self._balance = float(b.get("amount", 0))
                    logger.info(f"Circle Wallet loaded: {self.wallet_type} ({self.wallet_id})")
                else:
                    logger.error(f"Failed to load wallet: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Failed to load wallet info: {e}")

    def get_balance(self) -> float:
        """Get USDC balance for the Circle wallet."""
        if not self.connected or not self.wallet_id:
            return 0
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"https://api-sandbox.circle.com/v1/wallets/{self.wallet_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    balances = data.get("balances", [])
                    for b in balances:
                        if b.get("currency") == "USDC":
                            return float(b.get("amount", 0))
        except Exception as e:
            logger.error(f"Failed to get Circle wallet balance: {e}")
        return self._balance

    def get_wallet_info(self) -> dict:
        return {
            "connected": self.connected,
            "wallet_id": self.wallet_id,
            "wallet_address": self.wallet_address,
            "wallet_type": self.wallet_type,
            "sdk_available": True,
        }
