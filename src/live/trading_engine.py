from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
import yfinance as yf

from src.config import RuntimeConfig
from src.live.upstox_client import OrderRequest, UpstoxClient
from src.strategy.rule_based_strategy import RuleBasedStrategy
from src.utils.logger import get_logger
from src.utils.risk_manager import PositionSizer

logger = get_logger(__name__)
TRADE_LOG = Path(__file__).resolve().parents[2] / "logs" / "live_trades.jsonl"


class TradingEngine:
    """Bridges strategy signals with live order placement."""

    def __init__(self, cfg: RuntimeConfig, client: UpstoxClient) -> None:
        self.cfg = cfg
        self.client = client
        self.strategy = RuleBasedStrategy(cfg.strategy)
        self.position_sizer = PositionSizer(cfg.risk)

    def _download_recent_bars(self, symbol: str, interval: str = "15m", lookback: int = 400) -> pd.DataFrame:
        ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        data = yf.download(ticker, period="60d", interval=interval, progress=False).tail(lookback)
        data = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        data.index.name = "date"
        data["symbol"] = symbol
        return data

    def _log_trade(self, payload: Dict) -> None:
        TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with TRADE_LOG.open("a") as fp:
            fp.write(json.dumps(payload, default=str) + "\n")

    def _build_order(self, symbol: str, signal_row: pd.Series) -> Optional[OrderRequest]:
        atr = signal_row["atr"]
        price = signal_row["close"]
        qty = int(self.position_sizer.position_size(pd.Series([atr]))[0])
        if qty <= 0:
            logger.info("Computed quantity is zero, skipping order for %s", symbol)
            return None

        if signal_row["signal"] == 1:
            txn_type = "BUY"
        elif signal_row["signal"] == -1:
            txn_type = "SELL"
        else:
            return None

        trigger_price = None
        order_type = "MARKET"
        if self.cfg.risk.hard_stop_atr_multiplier > 0:
            stop_distance = atr * self.cfg.risk.hard_stop_atr_multiplier
            trigger_price = price - stop_distance if txn_type == "BUY" else price + stop_distance
            order_type = "SL"

        return OrderRequest(
            symbol=symbol,
            quantity=qty,
            transaction_type=txn_type,
            order_type=order_type,
            price=None if order_type == "MARKET" else price,
            trigger_price=trigger_price,
        )

    def evaluate_symbol(self, symbol: str) -> None:
        df = self._download_recent_bars(symbol, interval="15m")
        signals = self.strategy.generate_signals(df)
        latest = signals.data.iloc[-1]
        logger.info(
            "Latest signal for %s -> signal=%s price=%.2f rsi=%.2f macd=%.4f regime=%s",
            symbol,
            latest["signal"],
            latest["close"],
            latest["rsi"],
            latest["macd"],
            latest["volatility_regime"],
        )

        order = self._build_order(symbol, latest)
        if order is None:
            return

        response = self.client.place_order(order)
        self._log_trade({"symbol": symbol, "order": order.__dict__, "response": response})

    def run_intraday_cycle(self, watchlist: Optional[Iterable[str]] = None) -> None:
        watchlist = list(watchlist or self.cfg.strategy.symbols)
        for symbol in watchlist:
            try:
                self.evaluate_symbol(symbol)
            except Exception as exc:
                logger.exception("Failed to process %s: %s", symbol, exc)

    def start_streaming(self, instrument_keys: Iterable[str]) -> None:
        def on_tick(tick: Dict) -> None:
            symbol = tick.get("symbol")
            last_price = tick.get("ltp")
            logger.debug("Tick %s: %s", symbol, last_price)
            # In production feed, maintain rolling window & call evaluate_symbol on schedule.

        self.client.stream_market_data(instrument_keys, on_tick)
