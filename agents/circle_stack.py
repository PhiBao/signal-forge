"""
Circle developer stack reference and integration status.
"""

CIRCLE_PRODUCTS = {
    "arc": {
        "name": "Arc",
        "status": "integrated",
        "description": "Stablecoin-native L1 with sub-second deterministic finality",
        "use_case": "Reasoning trace anchoring, USDC settlement",
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
        "name": "Wallets",
        "status": "available",
        "description": "Embed secure wallets in any app",
        "use_case": "Automated key management for autonomous agents",
        "docs": "https://developers.circle.com/wallets",
    },
    "gateway": {
        "name": "Gateway",
        "status": "available",
        "description": "Unified USDC balance across chains, sub-500ms transfers",
        "use_case": "Cross-chain collateral rebalancing for multi-venue agents",
        "docs": "https://developers.circle.com/gateway",
    },
    "cctp": {
        "name": "CCTP",
        "status": "available",
        "description": "Cross-Chain Transfer Protocol for USDC",
        "use_case": "Bridge USDC from Polygon/Ethereum to Arc",
        "docs": "https://developers.circle.com/cctp",
    },
    "paymaster": {
        "name": "Paymaster",
        "status": "available",
        "description": "Allow transaction fees in USDC",
        "use_case": "Gasless UX for user-facing agent interfaces",
        "docs": "https://developers.circle.com/paymaster",
    },
    "nanopayments": {
        "name": "Nanopayments",
        "status": "available",
        "description": "Gas-free USDC payments as small as $0.000001",
        "use_case": "Per-signal micropayments for copy-trading subscribers",
        "docs": "https://developers.circle.com/gateway/nanopayments",
    },
    "usyc": {
        "name": "USYC",
        "status": "available",
        "description": "Tokenized money market fund",
        "use_case": "Park idle capital in yield between trades",
        "docs": "https://www.circle.com/usyc",
    },
}


def get_stack_status() -> dict:
    return CIRCLE_PRODUCTS
