from __future__ import annotations

import logging
from typing import Optional

try:
    from upstox_api.api import Session, Upstox, UpstoxError
except Exception:  # pragma: no cover - library optional during tests
    Session = Upstox = object  # type: ignore
    UpstoxError = Exception  # type: ignore


from config.settings import UpstoxCredentials
from trading.utils import retryable


class UpstoxAuthenticator:
    """
    Handles authentication lifecycle for Upstox's API including manual authorization code exchange.
    """

    def __init__(self, credentials: UpstoxCredentials, logger: logging.Logger):
        self.credentials = credentials
        self.logger = logger
        self._session: Optional[Session] = None
        self._client: Optional[Upstox] = None

    def build_login_url(self) -> str:
        session = Session(self.credentials.api_key)
        session.set_redirect_uri(self.credentials.redirect_uri)
        session.set_api_secret(self.credentials.api_secret)
        self._session = session
        login_url = session.get_login_url()
        self.logger.info("Open the following URL to authorize the application: %s", login_url)
        return login_url

    @retryable(UpstoxError, attempts=3)
    def exchange_code_for_token(self, authorization_code: str) -> str:
        if not self._session:
            self.build_login_url()
        assert self._session is not None, "Session not initialized"

        self._session.set_code(authorization_code)
        access_token = self._session.retrieve_access_token()
        self.credentials.access_token = access_token
        self.logger.info("Access token retrieved and cached successfully.")
        return access_token

    @retryable(UpstoxError, attempts=3)
    def get_client(self) -> Upstox:
        if self._client:
            return self._client

        if not self.credentials.access_token:
            raise ValueError(
                "Access token is missing. Complete the authorization flow first."
            )

        client = Upstox(self.credentials.api_key, self.credentials.access_token)
        client.get_master_contract("NSE_EQ")
        self._client = client
        self.logger.info("Upstox client initialized and master contract loaded.")
        return client

    def refresh_client(self) -> Upstox:
        self.logger.warning("Attempting to refresh Upstox client after failure...")
        self._client = None
        return self.get_client()
