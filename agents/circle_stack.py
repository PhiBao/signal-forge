"""
Circle developer stack reference and integration status.
"""

CIRCLE_PRODUCTS = {
    "arc": {
        "name": "Arc",
        "status": "integrated",
        "description": "Stablecoin-native L1 with sub-second deterministic finality",
        "use_case": "Reasoning trace anchoring, USDC settlement, x402 nanopayment settlement",
        "docs": "https://docs.arc.network",
    },
    "usdc": {
        "name": "USDC",
        "status": "integrated",
        "description": "Leading digital dollar stablecoin",
        "use_case": "Native gas + settlement currency on Arc",
        "docs": "https://developers.circle.com/stablecoins/what-is-usdc",
    },
    "wallets": {
        "name": "Wallets API",
        "status": "integrated",
        "description": "Direct REST API for wallet management",
        "use_case": "Agent wallet balance & info (replaced SDK)",
        "docs": "https://developers.circle.com/api-reference/payments",
    },
    "gateway": {
        "name": "Gateway",
        "status": "integrated",
        "description": "Unified USDC balance across chains, x402 nanopayments",
        "use_case": "x402 nanopayment settlement, batched on Arc",
        "docs": "https://developers.circle.com/gateway",
    },
    "nanopayments": {
        "name": "Nanopayments (x402)",
        "status": "integrated",
        "description": "Gas-free USDC payments via EIP-712 authorization",
        "use_case": "$0.01/signal subscriptions, batched settlement on Arc",
        "docs": "https://developers.circle.com/gateway/nanopayments",
    },
    "cctp": {
        "name": "CCTP",
        "status": "planned",
        "description": "Cross-Chain Transfer Protocol for USDC",
        "use_case": "Bridge USDC from Polygon/Ethereum to Arc (mainnet)",
        "docs": "https://developers.circle.com/cctp",
    },
    "paymaster": {
        "name": "Paymaster",
        "status": "planned",
        "description": "Allow transaction fees in USDC",
        "use_case": "Gasless UX for user-facing agent interfaces",
        "docs": "https://developers.circle.com/paymaster",
    },
    "usyc": {
        "name": "USYC",
        "status": "planned",
        "description": "Tokenized money market fund",
        "use_case": "Park idle capital in yield between trades",
        "docs": "https://www.circle.com/usyc",
    },
}


def get_stack_status() -> dict:
    return CIRCLE_PRODUCTS
