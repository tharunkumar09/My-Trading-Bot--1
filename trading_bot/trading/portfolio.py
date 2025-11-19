from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Position:
    symbol: str
    qty: int
    entry_price: float
    side: str
    stop_loss: float
    target: float
    entry_time: datetime


class PortfolioManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.positions: Dict[str, Position] = {}

    def add_position(
        self,
        symbol: str,
        qty: int,
        entry_price: float,
        side: str,
        stop_loss: float,
        target: float,
    ) -> None:
        position = Position(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price,
            side=side,
            stop_loss=stop_loss,
            target=target,
            entry_time=datetime.utcnow(),
        )
        self.positions[symbol] = position
        self.logger.info("Position added: %s", position)

    def update_stop(self, symbol: str, new_stop: float) -> None:
        if symbol in self.positions:
            self.logger.info("Updating stop for %s -> %.2f", symbol, new_stop)
            self.positions[symbol].stop_loss = new_stop

    def remove_position(self, symbol: str) -> Optional[Position]:
        position = self.positions.pop(symbol, None)
        if position:
            self.logger.info("Position closed: %s", position)
        return position

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)
