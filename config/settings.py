"""Runtime settings loaded from the environment.

Limitations:
- Endpoint rate limits are modeled with a shared token bucket and not per-IP.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="NOBITEX_")

    env: str = Field(default="testnet")
    api_token: str = Field(default="")
    commission_rate: float = Field(default=0.0015)
    spread_bps: float = Field(default=5.0)
    slippage_bps: float = Field(default=5.0)
    random_seed: int = Field(default=42)
    rate_limit_capacity: int = Field(default=300)
    rate_limit_window_seconds: int = Field(default=600)
    data_dir: Path = Field(default=Path("data"))
    reports_dir: Path = Field(default=Path("reports"))
    execution_model: str = Field(default="next_open")
    execution_mode: str = Field(default="static")
    execution_profile_path: str = Field(default="")
    max_positions: int = Field(default=1)
    allow_shorting: bool = Field(default=False)
    stop_file: Path = Field(default=Path("STOP_TRADING"))
    paper_capital: float = Field(default=10_000)
    paper_fee_rate: float = Field(default=0.0015)
    live_api_key: str = Field(default="")
    live_api_secret: str = Field(default="")
    live_max_position_size: float = Field(default=0.1)
    live_max_daily_loss: float = Field(default=0.02)
    live_risk_per_trade: float = Field(default=0.01)
    websocket_url_override: str = Field(default="wss://ws.nobitex.ir")
    market_data_poll_seconds: float = Field(default=5.0)
    live_order_timeout_seconds: int = Field(default=30)

    @property
    def base_rest_url(self) -> str:
        return "https://testnetapiv2.nobitex.ir" if self.env == "testnet" else "https://apiv2.nobitex.ir"

    @property
    def websocket_url(self) -> str:
        if self.websocket_url_override.endswith("/connection/websocket"):
            return self.websocket_url_override
        return f"{self.websocket_url_override.rstrip('/')}/connection/websocket"
