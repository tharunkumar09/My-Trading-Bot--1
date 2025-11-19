"""
Upstox API Client for authentication and trading operations.
Handles authentication, market data fetching, and order placement.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from loguru import logger
from websocket import create_connection
import json
import threading

from config import Config


class UpstoxClient:
    """Client for Upstox API integration"""
    
    BASE_URL = "https://api.upstox.com/v2"
    WS_URL = "wss://api.upstox.com/v2/feed"
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Upstox client
        
        Args:
            access_token: Access token for authentication
        """
        self.access_token = access_token or Config.UPSTOX_ACCESS_TOKEN
        self.api_key = Config.UPSTOX_API_KEY
        self.api_secret = Config.UPSTOX_API_SECRET
        self.redirect_uri = Config.UPSTOX_REDIRECT_URI
        self.session = requests.Session()
        self._setup_session()
        self.ws_connection = None
        self.ws_thread = None
        self._rate_limit_delay = 60 / Config.UPSTOX_RATE_LIMIT
        self._last_request_time = 0
        
    def _setup_session(self):
        """Setup session with authentication headers"""
        if self.access_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            })
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - time_since_last_request)
        self._last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make API request with error handling and rate limiting
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data as dictionary
        """
        self._rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {endpoint} - {str(e)}")
            raise
    
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Authenticate using authorization code
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            Authentication response with access token
        """
        endpoint = "/login/authorization/token"
        data = {
            "code": auth_code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}{endpoint}", data=data)
            response.raise_for_status()
            result = response.json()
            self.access_token = result.get("access_token")
            self._setup_session()
            logger.info("Successfully authenticated with Upstox")
            return result
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        return self._make_request("GET", "/user/profile")
    
    def get_funds(self) -> Dict[str, Any]:
        """Get available funds/margin"""
        return self._make_request("GET", "/user/getFundsAndMargin")
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        response = self._make_request("GET", "/portfolio/short-term-positions")
        return response.get("data", [])
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings"""
        response = self._make_request("GET", "/portfolio/long-term-holdings")
        return response.get("data", [])
    
    def get_order_book(self) -> List[Dict[str, Any]]:
        """Get order book"""
        response = self._make_request("GET", "/order/retrieve-all")
        return response.get("data", [])
    
    def get_historical_data(
        self,
        instrument_key: str,
        interval: str = "day",
        from_date: str = None,
        to_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical candle data
        
        Args:
            instrument_key: Instrument key (e.g., NSE_EQ|INE467B01029)
            interval: Candle interval (minute, hour, day)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            List of candle data
        """
        endpoint = f"/historical-candle/{instrument_key}/{interval}"
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        response = self._make_request("GET", endpoint, params=params)
        return response.get("data", {}).get("candles", [])
    
    def get_ltp(self, instrument_key: str) -> Dict[str, Any]:
        """
        Get Last Traded Price
        
        Args:
            instrument_key: Instrument key
            
        Returns:
            LTP data
        """
        endpoint = "/market-quote/ltp"
        params = {"instrument_key": instrument_key}
        response = self._make_request("GET", endpoint, params=params)
        return response.get("data", {})
    
    def get_market_quote(self, instrument_keys: List[str]) -> Dict[str, Any]:
        """
        Get market quotes for multiple instruments
        
        Args:
            instrument_keys: List of instrument keys
            
        Returns:
            Market quote data
        """
        endpoint = "/market-quote/quotes"
        params = {"instrument_key": ",".join(instrument_keys)}
        response = self._make_request("GET", endpoint, params=params)
        return response.get("data", {})
    
    def place_order(
        self,
        instrument_key: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "D",
        validity: str = "DAY",
        price: float = None,
        stop_loss: float = None,
        tag: str = None
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            instrument_key: Instrument key
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, SL-M
            product: Product type (D=Intraday, I=Delivery)
            validity: Order validity (DAY, IOC)
            price: Price for limit orders
            stop_loss: Stop loss price
            tag: Order tag/identifier
            
        Returns:
            Order response
        """
        endpoint = "/order/place"
        
        order_data = {
            "quantity": quantity,
            "product": product,
            "validity": validity,
            "price": price if order_type in ["LIMIT", "SL", "SL-M"] else 0,
            "tag": tag or "ALGO_BOT",
            "instrument_token": instrument_key,
            "order_type": order_type,
            "transaction_type": "BUY"  # Will be set by strategy
        }
        
        if stop_loss:
            order_data["stop_loss"] = stop_loss
        
        try:
            response = self._make_request("POST", endpoint, json=order_data)
            logger.info(f"Order placed: {response}")
            return response
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise
    
    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        order_type: str = None,
        validity: str = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            order_type: New order type
            validity: New validity
            
        Returns:
            Modification response
        """
        endpoint = f"/order/modify/{order_id}"
        
        modify_data = {}
        if quantity:
            modify_data["quantity"] = quantity
        if price:
            modify_data["price"] = price
        if order_type:
            modify_data["order_type"] = order_type
        if validity:
            modify_data["validity"] = validity
        
        return self._make_request("PUT", endpoint, json=modify_data)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        endpoint = f"/order/cancel/{order_id}"
        return self._make_request("DELETE", endpoint)
    
    def connect_websocket(self, instrument_keys: List[str], callback):
        """
        Connect to WebSocket for live market data
        
        Args:
            instrument_keys: List of instrument keys to subscribe
            callback: Callback function for market data updates
        """
        def ws_thread():
            try:
                ws = create_connection(
                    f"{self.WS_URL}?api_key={self.api_key}&access_token={self.access_token}"
                )
                self.ws_connection = ws
                
                # Subscribe to instruments
                subscribe_msg = {
                    "action": "subscribe",
                    "instrumentKeys": instrument_keys
                }
                ws.send(json.dumps(subscribe_msg))
                
                logger.info(f"WebSocket connected and subscribed to {len(instrument_keys)} instruments")
                
                while True:
                    try:
                        message = ws.recv()
                        data = json.loads(message)
                        callback(data)
                    except Exception as e:
                        logger.error(f"WebSocket error: {str(e)}")
                        break
                        
            except Exception as e:
                logger.error(f"WebSocket connection failed: {str(e)}")
        
        self.ws_thread = threading.Thread(target=ws_thread, daemon=True)
        self.ws_thread.start()
    
    def disconnect_websocket(self):
        """Disconnect WebSocket connection"""
        if self.ws_connection:
            self.ws_connection.close()
            self.ws_connection = None
            logger.info("WebSocket disconnected")
