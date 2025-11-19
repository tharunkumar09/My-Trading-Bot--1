from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables early so every module sees them
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


@dataclass
class UpstoxCredentials:
    api_key: str = os.getenv("UPSTOX_API_KEY", "")
    api_secret: str = os.getenv("UPSTOX_API_SECRET", "")
    redirect_uri: str = os.getenv("UPSTOX_REDIRECT_URI", "")
    access_token: Optional[str] = os.getenv("UPSTOX_ACCESS_TOKEN")
    api_host: str = os.getenv("UPSTOX_API_HOST", "https://api.upstox.com/v2")


@dataclass
class TradingControls:
    base_capital: float = float(os.getenv("BASE_CAPITAL", "1000000"))  # INR 10L default
    max_risk_per_trade: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.01"))
    max_positions: int = int(os.getenv("MAX_CONCURRENT_POSITIONS", "5"))
    slippage_bps: float = float(os.getenv("SLIPPAGE_BPS", "0.5"))
    atr_multiplier: float = float(os.getenv("ATR_MULTIPLIER", "2.0"))
    trailing_multiplier: float = float(os.getenv("TRAILING_MULTIPLIER", "1.5"))
    trade_symbol: str = os.getenv("DEFAULT_SYMBOL", "RELIANCE.NS")
    interval: str = os.getenv("TRADE_INTERVAL", "15minute")


@dataclass
class PathSettings:
    root: Path = Path(__file__).resolve().parents[1]

    @property
    def data_dir(self) -> Path:
        path = self.root / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_dir(self) -> Path:
        path = self.root / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        path = self.root / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class Settings:
    upstox: UpstoxCredentials
    trading: TradingControls
    paths: PathSettings


def get_settings() -> Settings:
    return Settings(
        upstox=UpstoxCredentials(),
        trading=TradingControls(),
        paths=PathSettings(),
    )


settings = get_settings()
