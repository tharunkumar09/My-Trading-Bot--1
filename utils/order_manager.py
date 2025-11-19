"""
Order management module for placing and managing orders.
"""
import time
from typing import Optional, Dict, List
from enum import Enum
from utils.logger import get_logger
from config.config import API_PROVIDER, REQUEST_DELAY, EXCHANGE, PRODUCT_TYPE

logger = get_logger(__name__)


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class TransactionType(Enum):
    """Transaction type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderManager:
    """Manage order placement and tracking."""
    
    def __init__(self, auth_handler):
        self.auth_handler = auth_handler
        self.session = None
        if auth_handler:
            self.session = auth_handler.get_session()
    
    def place_order_upstox(self, symbol: str, transaction_type: str, quantity: int,
                          order_type: str = "MARKET", price: float = None,
                          trigger_price: float = None, stop_loss: float = None) -> Optional[Dict]:
        """
        Place order via Upstox API.
        
        Args:
            symbol: Trading symbol
            transaction_type: "BUY" or "SELL"
            quantity: Order quantity
            order_type: "MARKET", "LIMIT", "STOP_LOSS", etc.
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for STOP_LOSS orders)
            stop_loss: Stop loss price
        
        Returns:
            Order response dict
        """
        try:
            from upstox_client.api.order_api import OrderApi
            from upstox_client.model.place_order_request import PlaceOrderRequest
            
            if not self.session:
                logger.error("Upstox session not available")
                return None
            
            api_instance = OrderApi(self.session)
            
            # Prepare order request
            order_request = PlaceOrderRequest(
                quantity=quantity,
                product=PRODUCT_TYPE,
                validity="DAY",
                price=price if order_type == "LIMIT" else None,
                tag="TradingBot",
                instrument_token=symbol,
                order_type=order_type,
                transaction_type=transaction_type,
                disclosed_quantity=0,
                trigger_price=trigger_price,
                is_amo=False
            )
            
            # Place order
            response = api_instance.place_order(body=order_request)
            
            if response:
                logger.info(f"Order placed successfully: {response.data.get('order_id')}")
                return {
                    'order_id': response.data.get('order_id'),
                    'status': 'SUCCESS',
                    'message': 'Order placed successfully'
                }
            
        except Exception as e:
            logger.error(f"Error placing order via Upstox: {e}")
            return {
                'status': 'FAILED',
                'message': str(e)
            }
    
    def place_order_angel_one(self, symbol: str, transaction_type: str, quantity: int,
                             order_type: str = "MARKET", price: float = None,
                             trigger_price: float = None, stop_loss: float = None) -> Optional[Dict]:
        """
        Place order via Angel One SmartAPI.
        
        Args:
            symbol: Trading symbol
            transaction_type: "BUY" or "SELL"
            quantity: Order quantity
            order_type: "MARKET", "LIMIT", "STOP_LOSS", etc.
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for STOP_LOSS orders)
            stop_loss: Stop loss price
        
        Returns:
            Order response dict
        """
        try:
            if not self.session:
                logger.error("Angel One session not available")
                return None
            
            # Map order types
            order_type_map = {
                "MARKET": "MARKET",
                "LIMIT": "LIMIT",
                "STOP_LOSS": "STOPLOSS",
                "STOP_LOSS_LIMIT": "STOPLOSS_LIMIT"
            }
            
            # Prepare order params
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": symbol,  # Need to get from symbol master
                "transactiontype": transaction_type,
                "exchange": EXCHANGE,
                "ordertype": order_type_map.get(order_type, "MARKET"),
                "producttype": PRODUCT_TYPE,
                "duration": "DAY",
                "price": str(price) if price else "0",
                "squareoff": "0",
                "stoploss": str(stop_loss) if stop_loss else "0",
                "quantity": str(quantity)
            }
            
            if trigger_price:
                order_params["triggerprice"] = str(trigger_price)
            
            # Place order
            response = self.session.placeOrder(order_params)
            
            if response and response.get('status'):
                logger.info(f"Order placed successfully: {response.get('data', {}).get('orderid')}")
                return {
                    'order_id': response.get('data', {}).get('orderid'),
                    'status': 'SUCCESS',
                    'message': 'Order placed successfully'
                }
            else:
                logger.error(f"Order placement failed: {response.get('message', 'Unknown error')}")
                return {
                    'status': 'FAILED',
                    'message': response.get('message', 'Unknown error')
                }
            
        except Exception as e:
            logger.error(f"Error placing order via Angel One: {e}")
            return {
                'status': 'FAILED',
                'message': str(e)
            }
    
    def place_order(self, symbol: str, transaction_type: str, quantity: int,
                   order_type: str = "MARKET", price: float = None,
                   trigger_price: float = None, stop_loss: float = None) -> Optional[Dict]:
        """Place order based on configured API provider."""
        time.sleep(REQUEST_DELAY)  # Rate limiting
        
        if API_PROVIDER.lower() == "upstox":
            return self.place_order_upstox(symbol, transaction_type, quantity, order_type, price, trigger_price, stop_loss)
        elif API_PROVIDER.lower() == "angel_one":
            return self.place_order_angel_one(symbol, transaction_type, quantity, order_type, price, trigger_price, stop_loss)
        else:
            logger.error(f"Unknown API provider: {API_PROVIDER}")
            return None
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status."""
        try:
            time.sleep(REQUEST_DELAY)
            
            if API_PROVIDER.lower() == "upstox":
                from upstox_client.api.order_api import OrderApi
                api_instance = OrderApi(self.session)
                response = api_instance.get_order_details(order_id)
                return response.data if response else None
            elif API_PROVIDER.lower() == "angel_one":
                response = self.session.orderBook()
                if response and response.get('status'):
                    orders = response.get('data', [])
                    for order in orders:
                        if order.get('orderid') == order_id:
                            return order
                return None
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            time.sleep(REQUEST_DELAY)
            
            if API_PROVIDER.lower() == "upstox":
                from upstox_client.api.order_api import OrderApi
                api_instance = OrderApi(self.session)
                response = api_instance.cancel_order(order_id)
                return response.status == 'success' if response else False
            elif API_PROVIDER.lower() == "angel_one":
                response = self.session.cancelOrder(order_id, "NORMAL")
                return response.get('status', False) if response else False
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return False
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        try:
            time.sleep(REQUEST_DELAY)
            
            if API_PROVIDER.lower() == "upstox":
                from upstox_client.api.portfolio_api import PortfolioApi
                api_instance = PortfolioApi(self.session)
                response = api_instance.get_positions()
                return response.data if response else []
            elif API_PROVIDER.lower() == "angel_one":
                response = self.session.position()
                if response and response.get('status'):
                    return response.get('data', [])
                return []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
