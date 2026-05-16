"""
Arc blockchain interaction: balance checks, USDC transfers, trace anchoring.
"""

import logging
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from agents.config import settings

logger = logging.getLogger(__name__)

USDC_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
]


class ArcWallet:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.account = None
        self.usdc_contract = None
        self.connected = False

    def connect(self) -> bool:
        if not settings.arc_private_key or settings.arc_private_key == "your_private_key":
            logger.warning("Arc private key not configured, running in simulated mode")
            return False

        try:
            self.account = self.w3.eth.account.from_key(settings.arc_private_key)
            self.usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(settings.usdc_contract_address),
                abi=USDC_ABI,
            )
            self.connected = True
            logger.info(f"Arc wallet connected: {self.account.address}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect Arc wallet: {e}")
            return False

    def get_usdc_balance(self) -> float:
        if not self.connected or not self.account:
            return 0
        try:
            balance = self.usdc_contract.functions.balanceOf(self.account.address).call()
            return balance / 1e6
        except Exception as e:
            logger.error(f"Failed to get USDC balance: {e}")
            return 0

    def get_native_balance(self) -> float:
        if not self.connected or not self.account:
            return 0
        try:
            balance = self.w3.eth.get_balance(self.account.address)
            return self.w3.from_wei(balance, "ether")
        except Exception:
            return 0

    def hash_and_store_trace(self, trace_hash: str) -> str | None:
        """
        Anchor a reasoning trace hash on Arc via a self-transaction.
        The hash is embedded in the tx data field.
        """
        if not self.connected or not self.account:
            return None

        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # Arc uses simple gas pricing, not EIP-1559
            gas_price = self.w3.eth.gas_price

            tx = {
                "from": self.account.address,
                "to": self.account.address,
                "value": 0,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": gas_price,
                "chainId": settings.arc_chain_id,
                "data": Web3.to_bytes(hexstr=trace_hash),
            }

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, 'hex') else tx_hash
            # Ensure 0x prefix for ArcScan compatibility
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = "0x" + tx_hash_hex
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

            if receipt.status == 1:
                return tx_hash_hex
            return None

        except Exception as e:
            logger.error(f"Failed to anchor trace on Arc: {e}")
            return None
