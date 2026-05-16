"""
Circle Developer-Controlled Wallet integration.
Handles wallet info, balances, and token transfers via Circle SDK.
Docs: https://developers.circle.com/wallets/dev-controlled/create-your-first-wallet
"""

import os
import logging
from dotenv import load_dotenv
load_dotenv()

from agents.config import settings

logger = logging.getLogger(__name__)

try:
    from circle.web3 import utils, developer_controlled_wallets
    CIRCLE_SDK_AVAILABLE = True
except ImportError:
    CIRCLE_SDK_AVAILABLE = False


class CircleWalletManager:
    def __init__(self):
        self.client = None
        self.wallets_api = None
        self.connected = False
        self.wallet_id = None
        self.wallet_address = None
        self.wallet_set_id = None

        if not CIRCLE_SDK_AVAILABLE:
            logger.warning("Circle SDK not installed")
            return

        api_key = settings.circle_api_key
        entity_secret = os.getenv("CIRCLE_ENTITY_SECRET", "")

        if not api_key or not entity_secret:
            logger.warning("Circle API key or entity secret not configured")
            return

        try:
            self.client = utils.init_developer_controlled_wallets_client(
                api_key=api_key,
                entity_secret=entity_secret,
            )
            self.wallets_api = developer_controlled_wallets.WalletsApi(self.client)
            self.connected = True

            # Load existing wallet info
            self.wallet_id = settings.circle_wallet_id
            if self.wallet_id:
                self._load_wallet_info()

            logger.info(f"Circle Wallet Manager initialized: {self.wallet_address}")
        except Exception as e:
            logger.error(f"Failed to initialize Circle Wallet: {e}")

    def _load_wallet_info(self):
        """Load wallet info from Circle API."""
        try:
            resp = self.wallets_api.get_wallets()
            for w in resp.data.wallets:
                d = w.model_dump()
                if d.get("id") == self.wallet_id:
                    self.wallet_address = d.get("address")
                    self.wallet_set_id = d.get("wallet_set_id")
                    break
        except Exception as e:
            logger.error(f"Failed to load wallet info: {e}")

    def get_balance(self) -> float:
        """Get USDC balance for the Circle wallet on Arc Testnet."""
        if not self.connected or not self.wallet_id:
            return 0
        try:
            resp = self.wallets_api.list_wallet_balance(id=self.wallet_id)
            for tb in resp.data.token_balances:
                if tb.token.get("symbol") == "USDC":
                    return float(tb.amount) / 1e6
            return 0
        except Exception as e:
            logger.error(f"Failed to get Circle wallet balance: {e}")
            return 0

    def get_wallet_info(self) -> dict:
        return {
            "connected": self.connected,
            "wallet_id": self.wallet_id,
            "wallet_address": self.wallet_address,
            "wallet_set_id": self.wallet_set_id,
            "sdk_available": CIRCLE_SDK_AVAILABLE,
        }
