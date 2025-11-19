from __future__ import annotations

import numpy as np
import pandas as pd
import talib


def calculate_supertrend(
    df: pd.DataFrame, period: int = 10, multiplier: float = 3.0
) -> pd.Series:
    atr = talib.ATR(df["High"], df["Low"], df["Close"], timeperiod=period)
    hl2 = (df["High"] + df["Low"]) / 2
    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    direction = np.ones(len(df))
    supertrend = np.zeros(len(df))

    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upperband.iloc[i - 1]:
            direction[i] = 1
        elif df["Close"].iloc[i] < lowerband.iloc[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
            if direction[i] > 0 and lowerband.iloc[i] < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]
            if direction[i] < 0 and upperband.iloc[i] > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

        supertrend[i] = (
            lowerband.iloc[i] if direction[i] > 0 else upperband.iloc[i]
        )

    return pd.Series(supertrend, index=df.index, name="supertrend")


class IndicatorEngine:
    def __init__(
        self,
        rsi_period: int = 14,
        ema_period: int = 200,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        supertrend_period: int = 10,
        supertrend_multiplier: float = 3.0,
    ):
        self.rsi_period = rsi_period
        self.ema_period = ema_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.supertrend_period = supertrend_period
        self.supertrend_multiplier = supertrend_multiplier

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        prices = df.copy()
        prices["rsi"] = talib.RSI(prices["Close"], timeperiod=self.rsi_period)
        macd, macd_signal, macd_hist = talib.MACD(
            prices["Close"],
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal,
        )
        prices["macd"] = macd
        prices["macd_signal"] = macd_signal
        prices["macd_hist"] = macd_hist
        prices["ema200"] = talib.EMA(prices["Close"], timeperiod=self.ema_period)
        prices["supertrend"] = calculate_supertrend(
            prices, period=self.supertrend_period, multiplier=self.supertrend_multiplier
        )
        prices["trend_filter"] = np.where(prices["Close"] > prices["ema200"], 1, -1)
        prices.dropna(inplace=True)
        return prices
