"""
Risk management module for position sizing, stop losses, and risk controls.
"""
import pandas as pd
from typing import Optional, Dict
from datetime import datetime
from utils.logger import get_logger
from config.config import (
    MAX_POSITION_SIZE, MAX_PORTFOLIO_RISK, STOP_LOSS_PERCENTAGE,
    TRAILING_STOP_PERCENTAGE, MAX_DAILY_LOSS, VOLATILITY_THRESHOLD
)

logger = get_logger(__name__)


class RiskManager:
    """Manage risk and position sizing."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_pnl = 0.0
        self.positions = {}  # Track open positions
        self.last_reset_date = datetime.now().date()
    
    def reset_daily_metrics(self):
        """Reset daily metrics at start of trading day."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("Daily metrics reset")
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               account_value: float = None) -> int:
        """
        Calculate position size based on risk management rules.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            account_value: Current account value (defaults to current_capital)
        
        Returns:
            Number of shares to trade
        """
        if account_value is None:
            account_value = self.current_capital
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share == 0:
            logger.warning("Risk per share is zero, using default position size")
            return 0
        
        # Calculate maximum risk amount
        max_risk_amount = account_value * MAX_PORTFOLIO_RISK
        
        # Calculate position size based on risk
        position_size = int(max_risk_amount / risk_per_share)
        
        # Apply maximum position size limit
        max_shares_by_capital = int(MAX_POSITION_SIZE / entry_price)
        position_size = min(position_size, max_shares_by_capital)
        
        logger.info(f"Calculated position size: {position_size} shares (risk: {risk_per_share:.2f} per share)")
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, is_long: bool = True) -> float:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            is_long: True for long position, False for short
        
        Returns:
            Stop loss price
        """
        if is_long:
            stop_loss = entry_price * (1 - STOP_LOSS_PERCENTAGE)
        else:
            stop_loss = entry_price * (1 + STOP_LOSS_PERCENTAGE)
        
        return round(stop_loss, 2)
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                               highest_price: float, is_long: bool = True) -> float:
        """
        Calculate trailing stop loss.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            highest_price: Highest price since entry (for long) or lowest (for short)
            is_long: True for long position, False for short
        
        Returns:
            Trailing stop loss price
        """
        if is_long:
            # For long positions, trail from highest price
            trailing_stop = highest_price * (1 - TRAILING_STOP_PERCENTAGE)
            # Don't let trailing stop go below initial stop loss
            initial_stop = self.calculate_stop_loss(entry_price, is_long=True)
            trailing_stop = max(trailing_stop, initial_stop)
        else:
            # For short positions, trail from lowest price
            trailing_stop = lowest_price * (1 + TRAILING_STOP_PERCENTAGE)
            # Don't let trailing stop go above initial stop loss
            initial_stop = self.calculate_stop_loss(entry_price, is_long=False)
            trailing_stop = min(trailing_stop, initial_stop)
        
        return round(trailing_stop, 2)
    
    def check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            True if trading should continue, False if limit reached
        """
        self.reset_daily_metrics()
        
        if self.daily_pnl <= -MAX_DAILY_LOSS:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f}")
            return False
        return True
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L."""
        self.daily_pnl += pnl
        logger.info(f"Daily P&L updated: {self.daily_pnl:.2f}")
    
    def check_volatility_risk(self, data: pd.DataFrame, window: int = 20) -> bool:
        """
        Check if volatility is too high for trading.
        
        Args:
            data: DataFrame with price data
            window: Window for volatility calculation
        
        Returns:
            True if volatility is acceptable, False if too high
        """
        if len(data) < window:
            return True
        
        recent_data = data.tail(window)
        volatility = recent_data['close'].pct_change().std()
        
        if volatility > VOLATILITY_THRESHOLD:
            logger.warning(f"High volatility detected: {volatility:.4f}")
            return False
        return True
    
    def add_position(self, symbol: str, entry_price: float, quantity: int,
                    stop_loss: float, is_long: bool = True, trailing_stop: float = None):
        """Add a new position to tracking."""
        self.positions[symbol] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'trailing_stop': trailing_stop or stop_loss,
            'highest_price': entry_price if is_long else None,
            'lowest_price': entry_price if not is_long else None,
            'is_long': is_long,
            'entry_time': datetime.now()
        }
        logger.info(f"Position added: {symbol} - {quantity} shares @ {entry_price}")
    
    def update_position(self, symbol: str, current_price: float):
        """Update position with current price and trailing stop."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Update highest/lowest price
        if position['is_long']:
            if position['highest_price'] is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
            trailing_stop = self.calculate_trailing_stop(
                position['entry_price'], current_price, position['highest_price'], is_long=True
            )
        else:
            if position['lowest_price'] is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
            trailing_stop = self.calculate_trailing_stop(
                position['entry_price'], current_price, position['lowest_price'], is_long=False
            )
        
        position['trailing_stop'] = trailing_stop
        position['current_price'] = current_price
    
    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """
        Check if stop loss should be triggered.
        
        Returns:
            True if stop loss should be triggered
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        stop_loss = position['trailing_stop']
        
        if position['is_long']:
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss
    
    def remove_position(self, symbol: str):
        """Remove position from tracking."""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Position removed: {symbol}")
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position details."""
        return self.positions.get(symbol)
