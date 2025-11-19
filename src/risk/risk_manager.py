"""
Risk Management Module
Handles position sizing, stop losses, trailing stops, and risk limits
"""

import pandas as pd
from typing import Dict, Optional, List
from loguru import logger
from datetime import datetime

from config import Config


class RiskManager:
    """Risk management for trading positions"""
    
    def __init__(self, capital: float = None):
        """
        Initialize risk manager
        
        Args:
            capital: Available capital
        """
        self.capital = capital or Config.CAPITAL
        self.risk_per_trade = Config.RISK_PER_TRADE
        self.max_positions = Config.MAX_POSITIONS
        self.stop_loss_percent = Config.STOP_LOSS_PERCENT
        self.trailing_stop_percent = Config.TRAILING_STOP_PERCENT
        self.max_daily_loss = Config.MAX_DAILY_LOSS
        self.max_position_size = Config.MAX_POSITION_SIZE
        
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.open_positions: List[Dict] = []
    
    def reset_daily_limits(self):
        """Reset daily limits at start of trading day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("Daily risk limits reset")
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        signal_strength: float = 1.0
    ) -> int:
        """
        Calculate position size based on risk per trade
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            signal_strength: Signal strength (0-1) for position sizing
            
        Returns:
            Number of shares to buy
        """
        self.reset_daily_limits()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.capital * self.max_daily_loss:
            logger.warning("Daily loss limit reached, no new positions")
            return 0
        
        # Risk per trade in absolute terms
        risk_amount = self.capital * self.risk_per_trade * signal_strength
        
        # Price risk per share
        price_risk = abs(entry_price - stop_loss_price)
        
        if price_risk == 0:
            logger.warning("Zero price risk, cannot calculate position size")
            return 0
        
        # Calculate position size
        position_size = int(risk_amount / price_risk)
        
        # Calculate position value
        position_value = position_size * entry_price
        
        # Apply maximum position size limit
        max_position_value = self.capital * self.max_position_size
        if position_value > max_position_value:
            position_size = int(max_position_value / entry_price)
            logger.info(f"Position size capped at {position_size} shares due to max position size limit")
        
        # Ensure minimum 1 share if risk allows
        if position_size == 0 and risk_amount > 0:
            position_size = 1
        
        logger.info(
            f"Position size calculated: {position_size} shares, "
            f"Value: {position_value:.2f}, Risk: {risk_amount:.2f}"
        )
        
        return position_size
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        position_type: str = 'LONG'
    ) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price
            position_type: Position type (LONG or SHORT)
            
        Returns:
            Stop loss price
        """
        if position_type == 'LONG':
            return entry_price * (1 - self.stop_loss_percent)
        else:
            return entry_price * (1 + self.stop_loss_percent)
    
    def calculate_trailing_stop(
        self,
        entry_price: float,
        highest_price: float,
        position_type: str = 'LONG'
    ) -> float:
        """
        Calculate trailing stop loss price
        
        Args:
            entry_price: Entry price
            highest_price: Highest price since entry
            position_type: Position type (LONG or SHORT)
            
        Returns:
            Trailing stop loss price
        """
        if position_type == 'LONG':
            return highest_price * (1 - self.trailing_stop_percent)
        else:
            return highest_price * (1 + self.trailing_stop_percent)
    
    def can_open_position(self) -> bool:
        """
        Check if a new position can be opened
        
        Returns:
            True if position can be opened
        """
        self.reset_daily_limits()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.capital * self.max_daily_loss:
            logger.warning("Daily loss limit reached")
            return False
        
        # Check maximum positions limit
        if len(self.open_positions) >= self.max_positions:
            logger.warning(f"Maximum positions limit reached: {self.max_positions}")
            return False
        
        return True
    
    def update_position(
        self,
        position_id: str,
        current_price: float,
        highest_price: float = None
    ) -> Optional[Dict]:
        """
        Update position with current price and check stop losses
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            highest_price: Highest price since entry (for trailing stop)
            
        Returns:
            Updated position dictionary or None if position not found
        """
        position = next((p for p in self.open_positions if p['id'] == position_id), None)
        
        if not position:
            return None
        
        # Update current price
        position['current_price'] = current_price
        
        # Calculate unrealized P&L
        if position['type'] == 'LONG':
            position['unrealized_pnl'] = (current_price - position['entry_price']) * position['quantity']
        else:
            position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['quantity']
        
        # Update trailing stop
        if highest_price:
            position['highest_price'] = max(position.get('highest_price', position['entry_price']), highest_price)
            position['trailing_stop'] = self.calculate_trailing_stop(
                position['entry_price'],
                position['highest_price'],
                position['type']
            )
        
        # Check stop loss
        if position['type'] == 'LONG':
            if current_price <= position['stop_loss']:
                position['exit_reason'] = 'Stop Loss'
                position['should_exit'] = True
            elif highest_price and current_price <= position['trailing_stop']:
                position['exit_reason'] = 'Trailing Stop Loss'
                position['should_exit'] = True
        else:
            if current_price >= position['stop_loss']:
                position['exit_reason'] = 'Stop Loss'
                position['should_exit'] = True
            elif highest_price and current_price >= position['trailing_stop']:
                position['exit_reason'] = 'Trailing Stop Loss'
                position['should_exit'] = True
        
        return position
    
    def add_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        position_type: str = 'LONG'
    ) -> str:
        """
        Add a new position
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            quantity: Number of shares
            stop_loss: Stop loss price
            position_type: Position type (LONG or SHORT)
            
        Returns:
            Position ID
        """
        position_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        position = {
            'id': position_id,
            'symbol': symbol,
            'type': position_type,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'trailing_stop': entry_price,  # Will be updated
            'highest_price': entry_price,
            'current_price': entry_price,
            'unrealized_pnl': 0.0,
            'entry_time': datetime.now(),
            'should_exit': False,
            'exit_reason': ''
        }
        
        self.open_positions.append(position)
        logger.info(f"Position added: {position_id} - {symbol} x{quantity} @ {entry_price}")
        
        return position_id
    
    def remove_position(self, position_id: str) -> Optional[Dict]:
        """
        Remove a position
        
        Args:
            position_id: Position identifier
            
        Returns:
            Removed position dictionary or None
        """
        position = next((p for p in self.open_positions if p['id'] == position_id), None)
        
        if position:
            self.open_positions.remove(position)
            # Update daily P&L
            self.daily_pnl += position.get('realized_pnl', position['unrealized_pnl'])
            logger.info(f"Position removed: {position_id}, Daily P&L: {self.daily_pnl:.2f}")
        
        return position
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        return self.open_positions.copy()
    
    def get_total_exposure(self) -> float:
        """Calculate total exposure across all positions"""
        return sum(p['current_price'] * p['quantity'] for p in self.open_positions)
    
    def get_total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        return sum(p['unrealized_pnl'] for p in self.open_positions)
