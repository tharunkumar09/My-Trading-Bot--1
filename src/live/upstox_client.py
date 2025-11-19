from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from websocket import WebSocketApp

from src.config import APIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UpstoxAPIError(Exception):
    pass


@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    transaction_type: str  # BUY / SELL
    order_type: str  # MARKET / LIMIT / SL
    product: str = "MIS"
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    validity: str = "DAY"


class UpstoxClient:
    """Thin wrapper over the Upstox V2 REST + WebSocket APIs."""

    def __init__(self, cfg: APIConfig) -> None:
        self.cfg = cfg
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.feed: Optional[WebSocketApp] = None

    @retry(
        retry=retry_if_exception_type(UpstoxAPIError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    def authenticate(self, auth_code: Optional[str] = None) -> str:
        """Exchange auth code for access token."""

        token_url = f"{self.cfg.base_url}/login/authorization/token"
        payload = {
            "code": auth_code,
            "client_id": self.cfg.api_key,
            "client_secret": self.cfg.api_secret,
            "redirect_uri": self.cfg.redirect_uri,
            "grant_type": "authorization_code",
        }
        logger.info("Authenticating with Upstox...")
        response = self.session.post(token_url, data=payload, timeout=30)
        if response.status_code != 200:
            raise UpstoxAPIError(f"Auth failed: {response.text}")
        data = response.json()
        self.access_token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        logger.info("Upstox authentication successful.")
        return self.access_token

    def refresh_session(self) -> None:
        if not self.access_token:
            raise UpstoxAPIError("Authenticate before refreshing session.")
        refresh_url = f"{self.cfg.base_url}/login/authorization/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.access_token,
            "client_id": self.cfg.api_key,
            "client_secret": self.cfg.api_secret,
        }
        response = self.session.post(refresh_url, data=payload, timeout=30)
        if response.status_code != 200:
            raise UpstoxAPIError("Refresh token failed.")
        data = response.json()
        self.access_token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    @retry(
        retry=retry_if_exception_type(UpstoxAPIError),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
    )
    def get_market_quote(self, instrument_key: str) -> Dict[str, Any]:
        quote_url = f"{self.cfg.base_url}/market-quote/quotes"
        params = {"instrument_key": instrument_key}
        response = self.session.get(quote_url, params=params, timeout=5)
        if response.status_code != 200:
            raise UpstoxAPIError(f"Quote fetch failed: {response.text}")
        return response.json()

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        if not self.access_token:
            raise UpstoxAPIError("Authenticate before placing orders.")
        order_url = f"{self.cfg.base_url}/order/place"
        payload = {
            "instrument_token": order.symbol,
            "quantity": order.quantity,
            "transaction_type": order.transaction_type,
            "order_type": order.order_type,
            "product": order.product,
            "price": order.price,
            "trigger_price": order.trigger_price,
            "validity": order.validity,
        }
        response = self.session.post(order_url, json=payload, timeout=5)
        if response.status_code != 200:
            logger.error("Order failed: %s", response.text)
            raise UpstoxAPIError(response.text)
        return response.json()

    def get_positions(self) -> Dict[str, Any]:
        url = f"{self.cfg.base_url}/portfolio/positions"
        response = self.session.get(url, timeout=5)
        response.raise_for_status()
        return response.json()

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        url = f"{self.cfg.base_url}/order/cancel"
        payload = {"order_id": order_id}
        response = self.session.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()

    def _on_tick(self, ws: WebSocketApp, message: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        data = json.loads(message)
        callback(data)

    def _on_error(self, ws: WebSocketApp, error: Exception) -> None:
        logger.error("Upstox feed error: %s", error)

    def _on_close(self, ws: WebSocketApp, code: int, msg: str) -> None:
        logger.warning("Upstox feed closed (%s): %s", code, msg)

    def stream_market_data(
        self,
        instrument_keys: Iterable[str],
        on_tick: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Start a blocking websocket stream."""

        if not self.access_token:
            raise UpstoxAPIError("Authenticate before subscribing to ticks.")

        headers = {"Authorization": f"Bearer {self.access_token}"}

        def on_open(ws: WebSocketApp) -> None:
            logger.info("Upstox feed connected. Subscribing to %s instruments.", len(list(instrument_keys)))
            subscribe_payload = {
                "guid": "algo-bot-subscriber",
                "method": "sub",
                "data": {"instrument_keys": list(instrument_keys)},
            }
            ws.send(json.dumps(subscribe_payload))

        self.feed = WebSocketApp(
            url=self.cfg.websocket_url,
            header=headers,
            on_open=on_open,
            on_message=lambda ws, msg: self._on_tick(ws, msg, on_tick),
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self.feed.run_forever(ping_interval=15, ping_timeout=5)

    def ensure_connection(self) -> None:
        """Simple heartbeat check with exponential backoff."""

        for attempt in range(5):
            try:
                _ = self.get_positions()
                return
            except Exception as exc:
                wait_time = min(2 ** attempt, 60)
                logger.warning("Heartbeat failed (%s). Retrying in %ss", exc, wait_time)
                time.sleep(wait_time)
        raise UpstoxAPIError("Unable to verify Upstox connectivity.")
