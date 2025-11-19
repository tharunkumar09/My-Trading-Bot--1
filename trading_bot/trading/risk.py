from __future__ import annotations

import logging
import math
from dataclasses import dataclass


@dataclass
class RiskConfig:
    capital: float
    risk_per_trade: float
    max_positions: int
    trailing_multiplier: float


class RiskManager:
    def __init__(self, config: RiskConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.current_positions = 0

    def can_enter_new_position(self) -> bool:
        return self.current_positions < self.config.max_positions

    def register_fill(self):
        self.current_positions += 1

    def register_exit(self):
        if self.current_positions > 0:
            self.current_positions -= 1

    def calculate_position_size(self, entry: float, stop: float) -> int:
        risk_amount = self.config.capital * self.config.risk_per_trade
        risk_per_share = abs(entry - stop)
        if risk_per_share == 0:
            return 0
        qty = math.floor(risk_amount / risk_per_share)
        self.logger.debug(
            "Position sizing => entry: %.2f stop: %.2f qty: %s", entry, stop, qty
        )
        return max(qty, 0)

    def trailing_stop(self, direction: str, entry: float, atr: float, current_price: float) -> float:
        move = self.config.trailing_multiplier * atr
        if direction == "BUY":
            return max(entry - move, current_price - move)
        return min(entry + move, current_price + move)
