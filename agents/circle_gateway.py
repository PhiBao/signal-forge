"""
Circle Gateway integration for cross-chain USDC and Nanopayments.
Docs: https://developers.circle.com/gateway
"""

import os
import logging
import httpx
import time
import hashlib
import json
from dotenv import load_dotenv
load_dotenv()

from agents.config import settings

logger = logging.getLogger(__name__)

GATEWAY_WALLET_CONTRACT = "0x0077777d7EBA4688BDeF3E311b846F25870A19B9"  # Arc Testnet
ARC_CHAIN_ID = 5042002


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
        self.gateway_url = "https://gateway-api-testnet.circle.com"
        self.payments_url = "https://api-sandbox.circle.com/v1"

        if not self.api_key:
            logger.warning("Circle Gateway: API key not configured")
            return

        self.connected = True
        logger.info("Circle Gateway Manager initialized")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_payment_requirements(self, seller_address: str, amount_usdc: str) -> dict:
        """
        Get the payment requirements for a nanopayment.
        Frontend uses this to construct the EIP-712 domain and sign.
        """
        network = "eip155:5042002"  # Arc Testnet CAIP-2
        amount_atomic = str(int(float(amount_usdc) * 1e6))  # USDC has 6 decimals

        return {
            "scheme": "exact",
            "network": network,
            "asset": settings.usdc_contract_address,
            "amount": amount_atomic,
            "payTo": seller_address,
            "maxTimeoutSeconds": 604800,  # 7 days
            "extra": {
                "name": "GatewayWalletBatched",
                "version": "1",
                "verifyingContract": GATEWAY_WALLET_CONTRACT,
            },
            "eip712_domain": {
                "name": "GatewayWalletBatched",
                "version": "1",
                "chainId": ARC_CHAIN_ID,
                "verifyingContract": GATEWAY_WALLET_CONTRACT,
            },
        }

    async def nanopayment_settle(
        self,
        payer_address: str,
        seller_address: str,
        amount_usdc: str,
        resource_url: str = "/api/signals",
        signed_payload: dict | None = None,
    ) -> dict:
        """
        Settle an x402 nanopayment via Circle Gateway.
        
        If signed_payload is provided (from frontend), attempts real settlement.
        Otherwise falls back to demo mode.
        """
        if not self.connected:
            return {"success": False, "error": "gateway_not_connected"}

        network = "eip155:5042002"
        amount_atomic = str(int(float(amount_usdc) * 1e6))

        try:
            requirements = {
                "scheme": "exact",
                "network": network,
                "asset": settings.usdc_contract_address,
                "amount": amount_atomic,
                "payTo": seller_address,
                "maxTimeoutSeconds": 604800,
                "extra": {
                    "name": "GatewayWalletBatched",
                    "version": "1",
                    "verifyingContract": GATEWAY_WALLET_CONTRACT,
                },
            }

            if signed_payload:
                # Real settlement with frontend-signed payload
                payment_payload = {
                    "x402Version": 2,
                    "resource": {
                        "url": resource_url,
                        "description": "SignalForge AI prediction market signal",
                        "mimeType": "application/json",
                    },
                    "accepted": requirements,
                    "payload": signed_payload,
                }

                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{self.gateway_url}/v1/x402/settle",
                        headers=self._headers(),
                        json={
                            "paymentPayload": payment_payload,
                            "paymentRequirements": requirements,
                        },
                    )

                    result = resp.json()
                    if result.get("success"):
                        tx_hash = result.get("transaction", "")
                        logger.info(f"Nanopayment settled: {amount_usdc} USDC from {payer_address[:10]}... tx={tx_hash[:16]}...")
                        return {
                            "success": True,
                            "transaction": tx_hash,
                            "network": result.get("network", network),
                            "amount": amount_usdc,
                        }
                    else:
                        error_reason = result.get("errorReason", result.get("message", "unknown"))
                        logger.warning(f"Nanopayment settlement failed: {error_reason}")
                        return {
                            "success": False,
                            "error": error_reason,
                            "raw_response": result,
                        }
            else:
                # No signature provided — reject, don't fall back to demo
                logger.warning(f"Nanopayment rejected: no signed payload from {payer_address[:10]}...")
                return {
                    "success": False,
                    "error": "no_signed_payload",
                }
        except Exception as e:
            logger.error(f"Nanopayment settlement failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def transfer_unified(
        self,
        wallet_id: str,
        destination_address: str,
        amount: str,
        chain: str = "ARC-TESTNET",
    ) -> dict:
        """
        Transfer USDC from unified balance to any address on any chain.
        """
        if not self.connected:
            return {"status": "skipped", "reason": "not_connected"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/v1/wallets/{wallet_id}/transfers",
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

    async def deposit_to_gateway(
        self,
        wallet_id: str,
        amount: str,
        source_chain: str = "MATIC-AMOY",
    ) -> dict:
        """
        Deposit USDC from a source chain into the Gateway unified balance.
        """
        if not self.connected:
            return {"status": "skipped", "reason": "not_connected"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/v1/wallets/{wallet_id}/deposits",
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
