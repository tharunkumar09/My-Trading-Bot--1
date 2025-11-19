"""
Angel One SmartAPI Integration
Handles authentication, market data, and order placement via Angel One SmartAPI
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import pyotp
from smartapi import SmartConnect
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class AngelOneAPI:
    """
    Angel One SmartAPI wrapper for trading operations
    """
    
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str = None):
        """
        Initialize Angel One API client
        
        Args:
            api_key: Angel One API key
            client_id: Client ID
            password: Trading password
            totp_secret: TOTP secret for 2FA
        """
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        
        self.smart_api = SmartConnect(api_key=api_key)
        self.access_token = None
        self.refresh_token = None
        self.feed_token = None
        
        logger.info("Angel One API client initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Angel One
        
        Returns:
            True if successful
        """
        try:
            # Generate TOTP if secret provided
            totp = None
            if self.totp_secret:
                totp = pyotp.TOTP(self.totp_secret).now()
            
            # Login
            data = self.smart_api.generateSession(
                clientCode=self.client_id,
                password=self.password,
                totp=totp
            )
            
            if data['status']:
                self.access_token = data['data']['jwtToken']
                self.refresh_token = data['data']['refreshToken']
                self.feed_token = data['data']['feedToken']
                
                logger.info("Successfully authenticated with Angel One")
                return True
            else:
                logger.error(f"Authentication failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self.access_token is not None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_profile(self) -> Dict:
        """
        Get user profile
        
        Returns:
            Profile data
        """
        try:
            response = self.smart_api.getProfile(self.refresh_token)
            return response.get('data', {})
        except Exception as e:
            logger.error(f"Failed to get profile: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_quote(self, symbol: str, exchange: str = "NSE", token: str = None) -> Dict:
        """
        Get live quote for a symbol
        
        Args:
            symbol: Stock symbol
            exchange: Exchange (NSE, BSE)
            token: Symbol token (optional, will be fetched if not provided)
            
        Returns:
            Quote data
        """
        try:
            if not token:
                token = self._get_symbol_token(symbol, exchange)
            
            response = self.smart_api.ltpData(exchange, symbol, token)
            return response.get('data', {})
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_historical_data(self, symbol: str, exchange: str = "NSE",
                           interval: str = "ONE_DAY", from_date: str = None,
                           to_date: str = None, token: str = None) -> pd.DataFrame:
        """
        Get historical candle data
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: Interval (ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE, 
                     FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY)
            from_date: Start date (YYYY-MM-DD HH:MM)
            to_date: End date (YYYY-MM-DD HH:MM)
            token: Symbol token
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if not token:
                token = self._get_symbol_token(symbol, exchange)
            
            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            
            response = self.smart_api.getCandleData(params)
            data = response.get('data', [])
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def place_order(self, symbol: str, exchange: str, transaction_type: str,
                   quantity: int, order_type: str, price: float = 0,
                   trigger_price: float = 0, product: str = "DELIVERY",
                   validity: str = "DAY", variety: str = "NORMAL",
                   token: str = None) -> Dict:
        """
        Place an order
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            transaction_type: BUY or SELL
            quantity: Quantity
            order_type: MARKET, LIMIT, STOPLOSS_LIMIT, STOPLOSS_MARKET
            price: Price
            trigger_price: Trigger price
            product: DELIVERY, INTRADAY, CARRYFORWARD
            validity: DAY, IOC
            variety: NORMAL, STOPLOSS, AMO, ROBO
            token: Symbol token
            
        Returns:
            Order response
        """
        try:
            if not token:
                token = self._get_symbol_token(symbol, exchange)
            
            order_params = {
                "variety": variety,
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": product,
                "duration": validity,
                "price": price,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity,
                "triggerprice": trigger_price
            }
            
            response = self.smart_api.placeOrder(order_params)
            logger.info(f"Order placed: {transaction_type} {quantity} {symbol} @ {price}")
            
            return response.get('data', {})
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            raise
    
    def place_market_order(self, symbol: str, exchange: str, transaction_type: str,
                          quantity: int, product: str = "DELIVERY", token: str = None) -> Dict:
        """Place a market order"""
        return self.place_order(symbol, exchange, transaction_type, quantity,
                              "MARKET", product=product, token=token)
    
    def place_limit_order(self, symbol: str, exchange: str, transaction_type: str,
                         quantity: int, price: float, product: str = "DELIVERY",
                         token: str = None) -> Dict:
        """Place a limit order"""
        return self.place_order(symbol, exchange, transaction_type, quantity,
                              "LIMIT", price=price, product=product, token=token)
    
    def place_sl_order(self, symbol: str, exchange: str, transaction_type: str,
                      quantity: int, price: float, trigger_price: float,
                      product: str = "DELIVERY", token: str = None) -> Dict:
        """Place a stop-loss order"""
        return self.place_order(symbol, exchange, transaction_type, quantity,
                              "STOPLOSS_LIMIT", price=price, trigger_price=trigger_price,
                              product=product, variety="STOPLOSS", token=token)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def modify_order(self, order_id: str, variety: str = "NORMAL",
                    quantity: int = None, order_type: str = None,
                    price: float = None, trigger_price: float = None) -> Dict:
        """Modify an order"""
        try:
            modify_params = {
                "variety": variety,
                "orderid": order_id
            }
            
            if quantity is not None:
                modify_params["quantity"] = quantity
            if order_type is not None:
                modify_params["ordertype"] = order_type
            if price is not None:
                modify_params["price"] = price
            if trigger_price is not None:
                modify_params["triggerprice"] = trigger_price
            
            response = self.smart_api.modifyOrder(modify_params)
            logger.info(f"Order modified: {order_id}")
            
            return response.get('data', {})
            
        except Exception as e:
            logger.error(f"Failed to modify order: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict:
        """Cancel an order"""
        try:
            response = self.smart_api.cancelOrder(order_id, variety)
            logger.info(f"Order cancelled: {order_id}")
            
            return response.get('data', {})
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_order_book(self) -> List[Dict]:
        """Get order book"""
        try:
            response = self.smart_api.orderBook()
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get order book: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            response = self.smart_api.position()
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_holdings(self) -> List[Dict]:
        """Get holdings"""
        try:
            response = self.smart_api.holding()
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get holdings: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_funds(self) -> Dict:
        """Get account funds"""
        try:
            response = self.smart_api.rmsLimit()
            return response.get('data', {})
        except Exception as e:
            logger.error(f"Failed to get funds: {str(e)}")
            raise
    
    def close_position(self, symbol: str, exchange: str, quantity: int,
                      product: str = "DELIVERY", token: str = None) -> Dict:
        """Close a position"""
        transaction_type = "SELL" if quantity > 0 else "BUY"
        quantity = abs(quantity)
        
        return self.place_market_order(symbol, exchange, transaction_type,
                                      quantity, product, token)
    
    def _get_symbol_token(self, symbol: str, exchange: str) -> str:
        """
        Get symbol token (to be implemented with symbol master)
        For now, returns a placeholder
        """
        # In production, maintain a symbol master file and look up tokens
        # This is a simplified version
        logger.warning(f"Symbol token lookup not implemented for {symbol}")
        return "0"
