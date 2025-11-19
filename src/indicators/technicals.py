from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.config import StrategyConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import talib
except ImportError as exc:  # pragma: no cover - ensures informative error later
    talib = None
    logger.warning("TA-Lib is not available: %s. Install ta-lib to enable indicators.", exc)


def _require_talib() -> None:
    if talib is None:
        raise ImportError("TA-Lib is required for indicator computation. Please ensure ta-lib is installed.")


def compute_supertrend(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    """Custom Supertrend implementation."""

    _require_talib()
    atr_values = talib.ATR(df["high"].values, df["low"].values, df["close"].values, timeperiod=period)
    atr = pd.Series(atr_values, index=df.index, name="atr")
    hl2 = (df["high"] + df["low"]) / 2
    basic_upperband = (hl2 + multiplier * atr).copy()
    basic_lowerband = (hl2 - multiplier * atr).copy()

    final_upperband = basic_upperband.copy()
    final_lowerband = basic_lowerband.copy()

    for i in range(1, len(df)):
        if df["close"].iloc[i - 1] <= final_upperband.iloc[i - 1]:
            final_upperband.iloc[i] = min(basic_upperband.iloc[i], final_upperband.iloc[i - 1])
        else:
            final_upperband.iloc[i] = basic_upperband.iloc[i]

        if df["close"].iloc[i - 1] >= final_lowerband.iloc[i - 1]:
            final_lowerband.iloc[i] = max(basic_lowerband.iloc[i], final_lowerband.iloc[i - 1])
        else:
            final_lowerband.iloc[i] = basic_lowerband.iloc[i]

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    for i in range(len(df)):
        if i == 0:
            supertrend.iloc[i] = final_lowerband.iloc[i]
            direction.iloc[i] = 1 if df["close"].iloc[i] > supertrend.iloc[i] else -1
            continue

        if df["close"].iloc[i - 1] <= supertrend.iloc[i - 1]:
            supertrend.iloc[i] = final_upperband.iloc[i]
        else:
            supertrend.iloc[i] = final_lowerband.iloc[i]

        direction.iloc[i] = 1 if df["close"].iloc[i] > supertrend.iloc[i] else -1

    return supertrend.rename("supertrend"), atr, direction.rename("supertrend_direction")


def compute_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Attach RSI, MACD, Supertrend, EMA200 and other helper columns."""

    _require_talib()
    enriched = df.copy()

    enriched["rsi"] = talib.RSI(enriched["close"].values, timeperiod=cfg.rsi_period)

    macd, macd_signal, macd_hist = talib.MACD(
        enriched["close"].values,
        fastperiod=cfg.macd_fast,
        slowperiod=cfg.macd_slow,
        signalperiod=cfg.macd_signal,
    )
    enriched["macd"] = macd
    enriched["macd_signal"] = macd_signal
    enriched["macd_hist"] = macd_hist

    supertrend, atr, direction = compute_supertrend(enriched, cfg.supertrend_period, cfg.supertrend_multiplier)
    enriched["supertrend"] = supertrend
    enriched["atr"] = atr
    enriched["supertrend_direction"] = direction
    enriched["ema_200"] = enriched["close"].ewm(span=cfg.ema_period, adjust=False).mean()
    enriched["volume_sma_20"] = enriched["volume"].rolling(window=20).mean()

    return enriched.dropna()
