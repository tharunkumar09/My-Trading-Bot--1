from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from src.config import StrategyConfig
from src.indicators.technicals import compute_indicators
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SignalResult:
    data: pd.DataFrame
    stats: Dict[str, float]


class RuleBasedStrategy:
    """RSI + MACD + Supertrend + EMA trend filter strategy."""

    def __init__(self, cfg: StrategyConfig) -> None:
        self.cfg = cfg

    @staticmethod
    def _macd_cross(series: pd.Series, signal: pd.Series) -> Tuple[pd.Series, pd.Series]:
        bullish = (series > signal) & (series.shift(1) <= signal.shift(1))
        bearish = (series < signal) & (series.shift(1) >= signal.shift(1))
        return bullish, bearish

    @staticmethod
    def _rsi_extremes(rsi: pd.Series, oversold: int = 30, overbought: int = 70) -> Tuple[pd.Series, pd.Series]:
        long_ready = (rsi.shift(1) < oversold) & (rsi >= oversold)
        short_ready = (rsi.shift(1) > overbought) & (rsi <= overbought)
        return long_ready, short_ready

    @staticmethod
    def _shock_filter(close: pd.Series, threshold: float = 0.04) -> pd.Series:
        gap = close.pct_change().abs()
        return gap < threshold

    def _volatility_regime(self, atr: pd.Series) -> pd.Series:
        atr_sma = atr.rolling(window=50).mean()
        return np.where(atr > atr_sma * 1.5, "high", "normal")

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        enriched = compute_indicators(df, self.cfg)
        enriched["volatility_regime"] = self._volatility_regime(enriched["atr"])
        enriched["shock_filter"] = self._shock_filter(enriched["close"])
        return enriched

    def generate_signals(self, df: pd.DataFrame) -> SignalResult:
        enriched = self.prepare(df)
        macd_up, macd_down = self._macd_cross(enriched["macd"], enriched["macd_signal"])
        rsi_long, rsi_short = self._rsi_extremes(enriched["rsi"])

        bullish_trend = (enriched["close"] > enriched["ema_200"]) & (enriched["supertrend_direction"] > 0)
        bearish_trend = (enriched["close"] < enriched["ema_200"]) & (enriched["supertrend_direction"] < 0)
        liquidity_filter = enriched["volume_sma_20"] > self.cfg.min_volume_average

        long_signal = (
            bullish_trend
            & macd_up
            & rsi_long
            & liquidity_filter
            & enriched["shock_filter"]
        )

        short_signal = (
            bearish_trend
            & macd_down
            & rsi_short
            & liquidity_filter
            & enriched["shock_filter"]
        )

        enriched["signal"] = 0
        enriched.loc[long_signal, "signal"] = 1
        enriched.loc[short_signal, "signal"] = -1

        enriched["position"] = enriched["signal"].replace(0, np.nan).ffill().fillna(0)
        enriched["position"] = enriched["position"].clip(-1, 1)
        enriched["signal_strength"] = (
            long_signal.astype(int) * 1.0
            + short_signal.astype(int) * -1.0
            + (enriched["volatility_regime"] == "normal").astype(int) * 0.25
        )

        stats = {
            "long_triggers": float(long_signal.sum()),
            "short_triggers": float(short_signal.sum()),
            "avg_rsi": float(enriched["rsi"].mean()),
            "avg_atr": float(enriched["atr"].mean()),
        }

        return SignalResult(data=enriched, stats=stats)
