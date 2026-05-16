"""
Circle Gateway integration for cross-chain USDC and Nanopayments.
Docs: https://developers.circle.com/gateway
"""

import os
import logging
import httpx
from dotenv import load_dotenv
load_dotenv()

from agents.config import settings

logger = logging.getLogger(__name__)


class CircleGatewayManager:
    """
    Manages Circle Gateway for:
    - Unified USDC balance across chains
    - Nanopayments (gas-free USDC down to $0.000001)
    - Cross-chain transfers
    """

    def __init__(self):
        self.api_key = settings.circle_api_key
        self.entity_secret = os.getenv("CIRCLE_ENTITY_SECRET", "")
        self.connected = False
        self.gateway_url = "https://api-sandbox.circle.com/v1"

        if not self.api_key or not self.entity_secret:
            logger.warning("Circle Gateway: API key or entity secret not configured")
            return

        self.connected = True
        logger.info("Circle Gateway Manager initialized")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_unified_balance(self, wallet_id: str) -> dict:
        """
        Get unified USDC balance across all chains for a wallet.
        Gateway combines USDC from multiple chains into one spendable balance.
        """
        if not self.connected:
            return {"available": "0", "chains": {}}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.gateway_url}/wallets/{wallet_id}/balances",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {})
                return {"available": "0", "chains": {}}
        except Exception as e:
            logger.error(f"Gateway balance fetch failed: {e}")
            return {"available": "0", "chains": {}}

    async def transfer_unified(
        self,
        wallet_id: str,
        destination_address: str,
        amount: str,
        chain: str = "ARC-TESTNET",
    ) -> dict:
        """
        Transfer USDC from unified balance to any address on any chain.
        Gateway handles the cross-chain routing automatically.
        """
        if not self.connected:
            return {"status": "skipped", "reason": "not_connected"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/wallets/{wallet_id}/transfers",
                    headers=self._headers(),
                    json={
                        "destinationAddress": destination_address,
                        "amount": amount,
                        "chain": chain,
                    },
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Gateway transfer failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def nanopayment(
        self,
        wallet_id: str,
        merchant_address: str,
        amount: str,
        idempotency_key: str,
    ) -> dict:
        """
        Send a nanopayment (gas-free USDC as small as $0.000001).
        Used for per-signal micropayments from subscribers to the agent.
        """
        if not self.connected:
            return {"status": "skipped", "reason": "not_connected"}

        try:
            headers = {
                **self._headers(),
                "Idempotency-Key": idempotency_key,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.gateway_url}/wallets/{wallet_id}/nanopayments",
                    headers=headers,
                    json={
                        "merchantAddress": merchant_address,
                        "amount": amount,
                    },
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Nanopayment failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def deposit_to_gateway(
        self,
        wallet_id: str,
        amount: str,
        source_chain: str = "MATIC-AMOY",
    ) -> dict:
        """
        Deposit USDC from a source chain into the Gateway unified balance.
        Enables cross-chain USDC for the agent.
        """
        if not self.connected:
            return {"status": "skipped", "reason": "not_connected"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/wallets/{wallet_id}/deposits",
                    headers=self._headers(),
                    json={
                        "amount": amount,
                        "sourceChain": source_chain,
                    },
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Gateway deposit failed: {e}")
            return {"status": "error", "reason": str(e)}

    def get_info(self) -> dict:
        return {
            "connected": self.connected,
            "features": [
                "unified_balance",
                "cross_chain_transfer",
                "nanopayments",
                "gas_free_usdc",
            ],
        }
