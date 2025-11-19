from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from upstox_api.api import Upstox, UpstoxError
except Exception:  # pragma: no cover
    Upstox = object  # type: ignore
    UpstoxError = Exception  # type: ignore

from trading.utils import retryable


class OrderExecutor:
    def __init__(self, client: Upstox, logger: logging.Logger, trade_log_path: Path):
        self.client = client
        self.logger = logger
        self.trade_log_path = trade_log_path
        self.trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.trade_log_path.exists():
            with open(self.trade_log_path, "w", newline="") as fp:
                writer = csv.writer(fp)
                writer.writerow(
                    [
                        "timestamp",
                        "symbol",
                        "side",
                        "order_type",
                        "qty",
                        "price",
                        "status",
                        "reason",
                    ]
                )

    @retryable(UpstoxError, attempts=4)
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "MIS",
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        trailing_delta: Optional[float] = None,
        validity: str = "DAY",
        tag: str = "algobot",
    ) -> Dict[str, Any]:
        params = {
            "instrument": symbol,
            "transaction_type": side,
            "order_type": order_type,
            "product": product,
            "quantity": quantity,
            "price": limit_price or 0.0,
            "validity": validity,
            "trigger_price": stop_loss or 0.0,
            "tag": tag,
            "disclosed_quantity": 0,
        }
        self.logger.info("Placing %s order: %s", order_type, params)
        response = self.client.place_order(**params)
        self._log_trade(symbol, side, order_type, quantity, limit_price or 0.0, "PLACED", "Order placed")
        return response

    def _log_trade(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: int,
        price: float,
        status: str,
        reason: str,
    ) -> None:
        from datetime import datetime

        with open(self.trade_log_path, "a", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    datetime.utcnow().isoformat(),
                    symbol,
                    side,
                    order_type,
                    qty,
                    round(price, 2),
                    status,
                    reason,
                ]
            )
