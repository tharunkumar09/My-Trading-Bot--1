from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, Optional

import pandas as pd

try:
    from upstox_api.api import Upstox, WebSocket, UpstoxError
except Exception:  # pragma: no cover
    Upstox = WebSocket = object  # type: ignore
    UpstoxError = Exception  # type: ignore

import yfinance as yf

from trading.utils import retryable


class MarketDataClient:
    """
    Wraps Upstox data APIs and provides graceful fallbacks plus reconnection logic.
    """

    def __init__(
        self,
        client: Upstox,
        logger: logging.Logger,
        fallback_source: str = "yfinance",
    ):
        self.client = client
        self.logger = logger
        self.fallback_source = fallback_source
        self.websocket: Optional[WebSocket] = None

    @retryable(UpstoxError, attempts=4)
    def get_ohlc(
        self,
        symbol: str,
        interval: str,
        lookback_days: int = 5,
    ) -> pd.DataFrame:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days)

        try:
            candles = self.client.get_ohlc(
                instrument=symbol,
                interval=interval,
                to_date=end_date.strftime("%Y-%m-%d"),
                from_date=start_date.strftime("%Y-%m-%d"),
            )
            df = pd.DataFrame(candles)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            return df
        except Exception as exc:  # fall back to Yahoo
            self.logger.warning(
                "Upstox OHLC fetch failed for %s (%s). Falling back to %s.",
                symbol,
                exc,
                self.fallback_source,
            )
            return self._fallback_download(symbol, start_date, end_date, interval)

    def _fallback_download(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> pd.DataFrame:
        if self.fallback_source != "yfinance":
            raise RuntimeError("No fallback data source configured.")

        converted_interval = {"1minute": "1m", "5minute": "5m", "15minute": "15m"}.get(
            interval, "15m"
        )
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            interval=converted_interval,
            start=start,
            end=end,
            actions=False,
        )
        return df.rename(
            columns={
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Volume": "Volume",
            }
        )

    def connect_streaming(
        self,
        instruments: Iterable[str],
        on_tick: Callable[[Dict[str, Any]], None],
        auto_reconnect: bool = True,
    ) -> None:
        if WebSocket is object:
            self.logger.error("Upstox websocket SDK not available in this environment.")
            return

        def _on_open(ws):  # pragma: no cover - requires live session
            self.logger.info("Streaming connection opened.")
            ws.subscribe(
                instruments=instruments,
                feed_type=WebSocket.FeedType.Live,
                market_data_type=WebSocket.MarketDataType.Full,
            )

        def _on_close(ws):  # pragma: no cover
            self.logger.warning("Streaming connection closed.")
            if auto_reconnect:
                self.logger.info("Attempting to reconnect websocket ...")
                self.connect_streaming(instruments, on_tick, auto_reconnect)

        def _on_error(ws, error):  # pragma: no cover
            self.logger.error("Websocket error: %s", error)

        def _on_message(ws, message):  # pragma: no cover
            on_tick(message)

        self.websocket = WebSocket(
            api_key=self.client.api_key,
            access_token=self.client.access_token,  # type: ignore[attr-defined]
        )
        self.websocket.on_open = _on_open
        self.websocket.on_message = _on_message
        self.websocket.on_error = _on_error
        self.websocket.on_close = _on_close
        self.websocket.connect()
