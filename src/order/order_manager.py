"""
Order Manager
Handles order placement, modification, and tracking
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from enum import Enum

from src.api.upstox_client import UpstoxClient
from src.api.angel_one_client import AngelOneClient
from config import Config


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss
    SL_M = "SL-M"  # Stop Loss Market


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    PLACED = "PLACED"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderManager:
    """Manages order placement and tracking"""
    
    def __init__(self, api_client):
        """
        Initialize order manager
        
        Args:
            api_client: API client (UpstoxClient or AngelOneClient)
        """
        self.api_client = api_client
        self.orders: Dict[str, Dict] = {}
        self.order_counter = 0
    
    def place_order(
        self,
        symbol: str,
        instrument_key: str,
        quantity: int,
        order_type: OrderType,
        transaction_type: str = "BUY",
        price: float = None,
        stop_loss: float = None,
        product: str = "D"
    ) -> str:
        """
        Place an order
        
        Args:
            symbol: Stock symbol
            instrument_key: Instrument key for API
            quantity: Order quantity
            order_type: Order type
            transaction_type: BUY or SELL
            price: Price for limit orders
            stop_loss: Stop loss price
            product: Product type (D=Intraday, I=Delivery)
            
        Returns:
            Order ID
        """
        self.order_counter += 1
        order_id = f"ORDER_{self.order_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if isinstance(self.api_client, UpstoxClient):
                response = self.api_client.place_order(
                    instrument_key=instrument_key,
                    quantity=quantity,
                    order_type=order_type.value,
                    product=product,
                    price=price,
                    stop_loss=stop_loss,
                    tag=order_id
                )
            elif isinstance(self.api_client, AngelOneClient):
                response = self.api_client.place_order(
                    symbol=symbol,
                    exchange=Config.EXCHANGE,
                    quantity=quantity,
                    order_type=order_type.value,
                    price=price,
                    stop_loss=stop_loss
                )
            else:
                raise ValueError("Unknown API client type")
            
            # Store order information
            order_info = {
                'order_id': order_id,
                'api_order_id': response.get('data', {}).get('order_id', ''),
                'symbol': symbol,
                'instrument_key': instrument_key,
                'quantity': quantity,
                'order_type': order_type.value,
                'transaction_type': transaction_type,
                'price': price,
                'stop_loss': stop_loss,
                'status': OrderStatus.PLACED.value,
                'placed_at': datetime.now(),
                'product': product
            }
            
            self.orders[order_id] = order_info
            logger.info(f"Order placed: {order_id} - {symbol} {transaction_type} {quantity} @ {price or 'MARKET'}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place order {order_id}: {str(e)}")
            raise
    
    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        order_type: OrderType = None
    ) -> bool:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID
            quantity: New quantity
            price: New price
            order_type: New order type
            
        Returns:
            True if successful
        """
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        try:
            if isinstance(self.api_client, UpstoxClient):
                response = self.api_client.modify_order(
                    order_id=order['api_order_id'],
                    quantity=quantity,
                    price=price,
                    order_type=order_type.value if order_type else None
                )
            elif isinstance(self.api_client, AngelOneClient):
                response = self.api_client.modify_order(
                    order_id=order['api_order_id'],
                    quantity=quantity,
                    price=price
                )
            else:
                raise ValueError("Unknown API client type")
            
            # Update order information
            if quantity:
                order['quantity'] = quantity
            if price:
                order['price'] = price
            if order_type:
                order['order_type'] = order_type.value
            
            order['modified_at'] = datetime.now()
            logger.info(f"Order modified: {order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {str(e)}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID
            
        Returns:
            True if successful
        """
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        try:
            if isinstance(self.api_client, UpstoxClient):
                response = self.api_client.cancel_order(order['api_order_id'])
            elif isinstance(self.api_client, AngelOneClient):
                response = self.api_client.cancel_order(order['api_order_id'])
            else:
                raise ValueError("Unknown API client type")
            
            order['status'] = OrderStatus.CANCELLED.value
            order['cancelled_at'] = datetime.now()
            logger.info(f"Order cancelled: {order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return False
    
    def update_order_status(self, order_id: str, status: OrderStatus):
        """
        Update order status
        
        Args:
            order_id: Order ID
            status: New status
        """
        if order_id in self.orders:
            self.orders[order_id]['status'] = status.value
            self.orders[order_id]['updated_at'] = datetime.now()
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order information"""
        return self.orders.get(order_id)
    
    def get_all_orders(self) -> List[Dict]:
        """Get all orders"""
        return list(self.orders.values())
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        return [o for o in self.orders.values() if o['status'] == OrderStatus.PENDING.value or o['status'] == OrderStatus.PLACED.value]
