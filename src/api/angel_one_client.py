"""
Angel One SmartAPI Client (Alternative to Upstox)
"""

import time
from typing import Dict, List, Optional, Any
from loguru import logger
from smartapi import SmartConnect

from config import Config


class AngelOneClient:
    """Client for Angel One SmartAPI integration"""
    
    def __init__(self):
        """Initialize Angel One client"""
        self.api_key = Config.ANGEL_ONE_API_KEY
        self.username = Config.ANGEL_ONE_USERNAME
        self.password = Config.ANGEL_ONE_PASSWORD
        self.pin = Config.ANGEL_ONE_PIN
        self.client = None
        self._rate_limit_delay = 60 / Config.ANGEL_ONE_RATE_LIMIT
        self._last_request_time = 0
        
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - time_since_last_request)
        self._last_request_time = time.time()
    
    def authenticate(self) -> bool:
        """
        Authenticate with Angel One
        
        Returns:
            True if authentication successful
        """
        try:
            self.client = SmartConnect(api_key=self.api_key)
            data = self.client.generateSession(
                self.username,
                self.password,
                self.pin
            )
            
            if data.get("status"):
                logger.info("Successfully authenticated with Angel One")
                return True
            else:
                logger.error(f"Authentication failed: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile"""
        self._rate_limit()
        return self.client.getProfile()
    
    def get_funds(self) -> Dict[str, Any]:
        """Get available funds"""
        self._rate_limit()
        return self.client.rmsLimit()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        self._rate_limit()
        return self.client.position()
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings"""
        self._rate_limit()
        return self.client.holding()
    
    def get_order_book(self) -> List[Dict[str, Any]]:
        """Get order book"""
        self._rate_limit()
        return self.client.orderBook()
    
    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: str = "ONE_DAY",
        from_date: str = None,
        to_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical candle data
        
        Args:
            symbol: Stock symbol
            exchange: Exchange (NSE, BSE)
            interval: Candle interval
            from_date: Start date
            to_date: End date
            
        Returns:
            Historical candle data
        """
        self._rate_limit()
        try:
            params = {
                "exchange": exchange,
                "symboltoken": self._get_token(symbol, exchange),
                "interval": interval,
                "fromdate": from_date or "",
                "todate": to_date or ""
            }
            return self.client.getCandleData(params)
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {str(e)}")
            return []
    
    def _get_token(self, symbol: str, exchange: str) -> str:
        """Get instrument token for symbol"""
        # This would typically require a master contract lookup
        # For now, return placeholder
        return ""
    
    def place_order(
        self,
        symbol: str,
        exchange: str,
        quantity: int,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        price: float = None,
        stop_loss: float = None
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            quantity: Order quantity
            order_type: Order type
            product_type: Product type
            price: Price for limit orders
            stop_loss: Stop loss price
            
        Returns:
            Order response
        """
        self._rate_limit()
        try:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": self._get_token(symbol, exchange),
                "transactiontype": "BUY",
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "price": str(price) if price else "0",
                "squareoff": "0",
                "stoploss": str(stop_loss) if stop_loss else "0",
                "quantity": str(quantity)
            }
            
            response = self.client.placeOrder(order_params)
            logger.info(f"Order placed: {response}")
            return response
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise
    
    def modify_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        """Modify an order"""
        self._rate_limit()
        return self.client.modifyOrder(order_id, **kwargs)
    
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        """Cancel an order"""
        self._rate_limit()
        return self.client.cancelOrder(order_id, variety)
