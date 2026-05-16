from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from agents.models import RiskLevel, StrategyMode


class UserStrategy(BaseModel):
    mode: StrategyMode = StrategyMode.BALANCED
    risk: RiskLevel = RiskLevel.MODERATE
    max_position_usd: float = Field(default=25.0, ge=1, le=500)
    min_ev_pct: float = Field(default=2.0, ge=0.5, le=20)
    min_confidence: float = Field(default=30.0, ge=10, le=90)
    kelly_fraction: float = Field(default=0.25, ge=0.1, le=1.0)
    auto_cycle_minutes: int = Field(default=0, ge=0)
    paper_trade: bool = True


class Settings(BaseSettings):
    arc_rpc_url: str = "https://rpc.testnet.arc-node.thecanteenapp.com"
    arc_rpc_api_key: str = ""
    arc_private_key: str = ""
    arc_chain_id: int = 5042002
    usdc_contract_address: str = "0x3600000000000000000000000000000000000000"

    dgrid_api_key: str = ""
    dgrid_model: str = "openai/gpt-4o-mini"

    poly_gamma_api: str = "https://gamma-api.polymarket.com"
    poly_clob_api: str = "https://clob.polymarket.com"

    circle_api_key: str = ""
    circle_api_secret: str = ""
    circle_wallet_id: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
