from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"


@dataclass
class APIConfig:
    """Holds connectivity settings for the Upstox API."""

    api_key: str
    api_secret: str
    redirect_uri: str
    client_code: str
    totp_secret: Optional[str] = None
    base_url: str = "https://api.upstox.com/v2"
    websocket_url: str = "wss://api.upstox.com/feed/market-data-stream"


@dataclass
class StrategyConfig:
    """Parameters used by the indicator-based strategy."""

    symbols: List[str] = field(default_factory=lambda: ["RELIANCE", "TCS", "INFY"])
    interval: str = "1d"
    lookback_years: int = 20
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    supertrend_period: int = 10
    supertrend_multiplier: float = 3.0
    ema_period: int = 200
    min_volume_average: int = 100_000


@dataclass
class RiskConfig:
    """Risk and position sizing rules."""

    capital: float = 1_000_000.0  # INR
    risk_per_trade: float = 0.01  # 1% of capital
    max_positions: int = 5
    slippage_bps: float = 5.0
    trail_atr_multiplier: float = 1.5
    hard_stop_atr_multiplier: float = 2.5


@dataclass
class BacktestConfig:
    """Backtesting & data parameters."""

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    equity_curve_path: Path = BASE_DIR / "assets" / "equity_curve.png"
    trades_log_path: Path = BASE_DIR / "logs" / "backtest_trades.csv"
    benchmark_symbol: str = "^NSEI"


@dataclass
class RuntimeConfig:
    """Aggregated configuration passed across modules."""

    api: APIConfig
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)


def _load_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        load_dotenv()


def load_config() -> RuntimeConfig:
    """Load configuration values, prioritising environment variables."""

    _load_env()

    api_config = APIConfig(
        api_key=os.getenv("UPSTOX_API_KEY", ""),
        api_secret=os.getenv("UPSTOX_API_SECRET", ""),
        redirect_uri=os.getenv("UPSTOX_REDIRECT_URI", ""),
        client_code=os.getenv("UPSTOX_CLIENT_CODE", ""),
        totp_secret=os.getenv("UPSTOX_TOTP_SECRET"),
    )

    strategy_config = StrategyConfig()

    history_start = os.getenv("BACKTEST_START")
    history_end = os.getenv("BACKTEST_END")
    if history_start is None:
        history_start = (
            datetime.utcnow().replace(year=datetime.utcnow().year - strategy_config.lookback_years).strftime(
                "%Y-%m-%d"
            )
        )
    if history_end is None:
        history_end = datetime.utcnow().strftime("%Y-%m-%d")

    backtest_config = BacktestConfig(start_date=history_start, end_date=history_end)

    risk_config = RiskConfig(
        capital=float(os.getenv("RISK_CAPITAL", RiskConfig.capital)),
        risk_per_trade=float(os.getenv("RISK_PER_TRADE", RiskConfig.risk_per_trade)),
        max_positions=int(os.getenv("RISK_MAX_POSITIONS", RiskConfig.max_positions)),
        slippage_bps=float(os.getenv("RISK_SLIPPAGE_BPS", RiskConfig.slippage_bps)),
        trail_atr_multiplier=float(
            os.getenv("RISK_TRAIL_ATR_MULTIPLIER", RiskConfig.trail_atr_multiplier)
        ),
        hard_stop_atr_multiplier=float(
            os.getenv("RISK_HARD_STOP_ATR_MULTIPLIER", RiskConfig.hard_stop_atr_multiplier)
        ),
    )

    return RuntimeConfig(api=api_config, strategy=strategy_config, risk=risk_config, backtest=backtest_config)
