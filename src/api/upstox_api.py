"""
Upstox API Integration
Handles authentication, market data, and order placement via Upstox API
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class UpstoxAPI:
    """
    Upstox API wrapper for trading operations
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str = None):
        """
        Initialize Upstox API client
        
        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            redirect_uri: OAuth redirect URI
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri or "https://127.0.0.1:8080"
        self.access_token = None
        self.token_expiry = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds
        
        logger.info("Upstox API client initialized")
    
    def get_login_url(self) -> str:
        """
        Get OAuth login URL
        
        Returns:
            Login URL string
        """
        url = f"https://api.upstox.com/v2/login/authorization/dialog"
        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri
        }
        
        login_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        logger.info(f"Login URL generated: {login_url}")
        return login_url
    
    def authenticate(self, authorization_code: str) -> bool:
        """
        Authenticate using authorization code
        
        Args:
            authorization_code: Code received after user login
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/login/authorization/token"
            
            data = {
                "code": authorization_code,
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result.get('access_token')
            
            # Token typically expires in 24 hours
            self.token_expiry = datetime.now() + timedelta(hours=24)
            
            logger.info("Successfully authenticated with Upstox")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def set_access_token(self, access_token: str):
        """
        Set access token directly (e.g., from saved session)
        
        Args:
            access_token: Valid access token
        """
        self.access_token = access_token
        self.token_expiry = datetime.now() + timedelta(hours=24)
        logger.info("Access token set manually")
    
    def is_authenticated(self) -> bool:
        """Check if authenticated and token is valid"""
        if not self.access_token:
            return False
        
        if self.token_expiry and datetime.now() >= self.token_expiry:
            logger.warning("Access token expired")
            return False
        
        return True
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                      data: Dict = None) -> Dict:
        """
        Make API request with error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data
        """
        if not self.is_authenticated():
            raise Exception("Not authenticated. Please authenticate first.")
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Invalid HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}, Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_profile(self) -> Dict:
        """
        Get user profile
        
        Returns:
            Profile data
        """
        return self._make_request("GET", "/user/profile")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict:
        """
        Get live quote for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            exchange: Exchange name (NSE, BSE)
            
        Returns:
            Quote data with LTP, OHLC, volume etc.
        """
        instrument_key = f"{exchange}_EQ|{symbol}"
        endpoint = "/market-quote/quotes"
        params = {"instrument_key": instrument_key}
        
        response = self._make_request("GET", endpoint, params=params)
        return response.get('data', {}).get(instrument_key, {})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_historical_data(self, symbol: str, exchange: str = "NSE",
                           interval: str = "day", from_date: str = None,
                           to_date: str = None) -> pd.DataFrame:
        """
        Get historical candle data
        
        Args:
            symbol: Stock symbol
            exchange: Exchange name
            interval: Candle interval (1minute, 5minute, 30minute, day, week, month)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with OHLCV data
        """
        instrument_key = f"{exchange}_EQ|{symbol}"
        endpoint = f"/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
        
        response = self._make_request("GET", endpoint)
        candles = response.get('data', {}).get('candles', [])
        
        if not candles:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def place_order(self, symbol: str, exchange: str, transaction_type: str,
                   quantity: int, order_type: str, price: float = 0,
                   trigger_price: float = 0, product: str = "D",
                   validity: str = "DAY") -> Dict:
        """
        Place an order
        
        Args:
            symbol: Stock symbol
            exchange: Exchange (NSE, BSE)
            transaction_type: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (for LIMIT/SL orders)
            trigger_price: Trigger price (for SL orders)
            product: Product type (D=Delivery, I=Intraday, CO=Cover Order, OCO=One Cancels Other)
            validity: Order validity (DAY, IOC)
            
        Returns:
            Order response with order_id
        """
        instrument_key = f"{exchange}_EQ|{symbol}"
        
        order_data = {
            "quantity": quantity,
            "product": product,
            "validity": validity,
            "price": price,
            "tag": "AlgoTrade",
            "instrument_token": instrument_key,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "disclosed_quantity": 0,
            "trigger_price": trigger_price,
            "is_amo": False
        }
        
        response = self._make_request("POST", "/order/place", data=order_data)
        logger.info(f"Order placed: {transaction_type} {quantity} {symbol} @ {price}")
        
        return response.get('data', {})
    
    def place_market_order(self, symbol: str, exchange: str, transaction_type: str,
                          quantity: int, product: str = "D") -> Dict:
        """Place a market order"""
        return self.place_order(symbol, exchange, transaction_type, quantity, 
                              "MARKET", product=product)
    
    def place_limit_order(self, symbol: str, exchange: str, transaction_type: str,
                         quantity: int, price: float, product: str = "D") -> Dict:
        """Place a limit order"""
        return self.place_order(symbol, exchange, transaction_type, quantity,
                              "LIMIT", price=price, product=product)
    
    def place_sl_order(self, symbol: str, exchange: str, transaction_type: str,
                      quantity: int, price: float, trigger_price: float,
                      product: str = "D") -> Dict:
        """Place a stop-loss order"""
        return self.place_order(symbol, exchange, transaction_type, quantity,
                              "SL", price=price, trigger_price=trigger_price,
                              product=product)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def modify_order(self, order_id: str, quantity: int = None, 
                    order_type: str = None, price: float = None,
                    trigger_price: float = None, validity: str = None) -> Dict:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity
            order_type: New order type
            price: New price
            trigger_price: New trigger price
            validity: New validity
            
        Returns:
            Modification response
        """
        modify_data = {"order_id": order_id}
        
        if quantity is not None:
            modify_data["quantity"] = quantity
        if order_type is not None:
            modify_data["order_type"] = order_type
        if price is not None:
            modify_data["price"] = price
        if trigger_price is not None:
            modify_data["trigger_price"] = trigger_price
        if validity is not None:
            modify_data["validity"] = validity
        
        response = self._make_request("PUT", "/order/modify", data=modify_data)
        logger.info(f"Order modified: {order_id}")
        
        return response.get('data', {})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        response = self._make_request("DELETE", f"/order/cancel", params={"order_id": order_id})
        logger.info(f"Order cancelled: {order_id}")
        
        return response.get('data', {})
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_order_history(self, order_id: str = None) -> List[Dict]:
        """
        Get order history
        
        Args:
            order_id: Specific order ID (optional)
            
        Returns:
            List of orders
        """
        if order_id:
            endpoint = f"/order/history"
            params = {"order_id": order_id}
        else:
            endpoint = "/order/retrieve-all"
            params = None
        
        response = self._make_request("GET", endpoint, params=params)
        return response.get('data', [])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_positions(self) -> List[Dict]:
        """
        Get current positions
        
        Returns:
            List of positions
        """
        response = self._make_request("GET", "/portfolio/short-term-positions")
        return response.get('data', [])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_holdings(self) -> List[Dict]:
        """
        Get long-term holdings
        
        Returns:
            List of holdings
        """
        response = self._make_request("GET", "/portfolio/long-term-holdings")
        return response.get('data', [])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_funds(self) -> Dict:
        """
        Get account funds/margins
        
        Returns:
            Fund details
        """
        response = self._make_request("GET", "/user/get-funds-and-margin")
        return response.get('data', {})
    
    def close_position(self, symbol: str, exchange: str, quantity: int, product: str = "D") -> Dict:
        """
        Close an open position
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            quantity: Quantity to close (positive for long, negative for short)
            product: Product type
            
        Returns:
            Order response
        """
        transaction_type = "SELL" if quantity > 0 else "BUY"
        quantity = abs(quantity)
        
        return self.place_market_order(symbol, exchange, transaction_type, quantity, product)
