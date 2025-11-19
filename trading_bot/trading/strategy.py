from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import talib


@dataclass
class StrategyParameters:
    rsi_buy_level: float = 35.0
    rsi_sell_level: float = 65.0
    macd_confirmation: float = 0.0
    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    target_rr: float = 2.0
    shock_threshold: float = 0.04  # 4% bar range filter


@dataclass
class Signal:
    side: str
    entry_price: float
    stop_loss: float
    target: float
    reason: str


class ConfluenceStrategy:
    """
    Combines RSI, MACD crossover, Supertrend, and EMA-200 trend filter.
    Adds volatility shock protection via ATR.
    """

    def __init__(
        self,
        params: StrategyParameters,
        logger: logging.Logger,
    ):
        self.params = params
        self.logger = logger

    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        if len(df) < max(200, self.params.atr_period * 5):
            self.logger.debug("Insufficient data for strategy evaluation.")
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        atr = talib.ATR(df["High"], df["Low"], df["Close"], timeperiod=self.params.atr_period)
        atr_latest = atr.iloc[-1]
        bar_range = (latest["High"] - latest["Low"]) / latest["Close"]
        if bar_range > self.params.shock_threshold:
            self.logger.info("Shock filter active (%.2f%% > %.2f%%).", bar_range * 100, self.params.shock_threshold * 100)
            return None

        if self._is_long_setup(latest, prev):
            stop = latest["Close"] - self.params.stop_atr_multiple * atr_latest
            target = latest["Close"] + self.params.target_rr * (latest["Close"] - stop)
            return Signal(
                side="BUY",
                entry_price=latest["Close"],
                stop_loss=stop,
                target=target,
                reason="RSI oversold + MACD bull cross + uptrend confirmation",
            )

        if self._is_short_setup(latest, prev):
            stop = latest["Close"] + self.params.stop_atr_multiple * atr_latest
            target = latest["Close"] - self.params.target_rr * (stop - latest["Close"])
            return Signal(
                side="SELL",
                entry_price=latest["Close"],
                stop_loss=stop,
                target=target,
                reason="RSI overbought + MACD bear cross + downtrend confirmation",
            )

        return None

    def _is_long_setup(self, latest: pd.Series, prev: pd.Series) -> bool:
        return (
            latest["trend_filter"] > 0
            and latest["Close"] > latest["supertrend"]
            and latest["rsi"] <= self.params.rsi_buy_level
            and prev["macd"] <= prev["macd_signal"]
            and latest["macd"] > latest["macd_signal"]
        )

    def _is_short_setup(self, latest: pd.Series, prev: pd.Series) -> bool:
        return (
            latest["trend_filter"] < 0
            and latest["Close"] < latest["supertrend"]
            and latest["rsi"] >= self.params.rsi_sell_level
            and prev["macd"] >= prev["macd_signal"]
            and latest["macd"] < latest["macd_signal"]
        )
