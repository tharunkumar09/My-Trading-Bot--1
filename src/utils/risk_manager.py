from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.config import RiskConfig


@dataclass
class PositionSizer:
    risk_config: RiskConfig

    def atr_stop_distance(self, atr: pd.Series, multiplier: float) -> pd.Series:
        return atr * multiplier

    def position_size(
        self,
        atr: pd.Series,
        capital: Optional[float] = None,
    ) -> pd.Series:
        capital = capital or self.risk_config.capital
        stop_distance = self.atr_stop_distance(atr, self.risk_config.hard_stop_atr_multiplier)
        risk_amount = capital * self.risk_config.risk_per_trade
        qty = (risk_amount / stop_distance).replace([np.inf, -np.inf], 0.0)
        qty = np.floor(qty).clip(lower=0)
        return qty


def apply_trailing_stop(
    df: pd.DataFrame,
    trail_multiplier: float,
    atr_column: str = "atr",
    direction_column: str = "position",
) -> pd.Series:
    """Generates trailing stop levels using ATR."""

    trail = []
    current_stop = np.nan
    for _, row in df.iterrows():
        if row[direction_column] > 0:
            if np.isnan(current_stop):
                current_stop = row["close"] - trail_multiplier * row[atr_column]
            else:
                # only raise stop for long positions
                candidate = row["close"] - trail_multiplier * row[atr_column]
                current_stop = max(current_stop, candidate)
        elif row[direction_column] < 0:
            if np.isnan(current_stop):
                current_stop = row["close"] + trail_multiplier * row[atr_column]
            else:
                candidate = row["close"] + trail_multiplier * row[atr_column]
                current_stop = min(current_stop, candidate)
        else:
            current_stop = np.nan

        trail.append(current_stop)

    return pd.Series(trail, index=df.index, name="trailing_stop")
