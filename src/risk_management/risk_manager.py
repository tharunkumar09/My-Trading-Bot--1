"""
Risk Management System
Handles position sizing, stop loss, take profit, and trailing stops
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management for trading positions
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk manager
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        
        # Portfolio risk parameters
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.02)
        self.max_position_size = config.get('max_position_size', 0.10)
        self.max_open_positions = config.get('max_open_positions', 5)
        
        # Stop loss parameters
        self.sl_config = config.get('stop_loss', {})
        self.sl_type = self.sl_config.get('type', 'atr')
        self.sl_atr_multiplier = self.sl_config.get('atr_multiplier', 2.0)
        self.sl_percentage = self.sl_config.get('percentage', 0.02)
        
        # Take profit parameters
        self.tp_config = config.get('take_profit', {})
        self.risk_reward_ratio = self.tp_config.get('risk_reward_ratio', 2.0)
        
        # Trailing stop parameters
        self.ts_config = config.get('trailing_stop', {})
        self.ts_enabled = self.ts_config.get('enabled', True)
        self.ts_activation_pct = self.ts_config.get('activation_pct', 0.03)
        self.ts_trail_pct = self.ts_config.get('trail_pct', 0.015)
        
        # Position sizing
        self.ps_config = config.get('position_sizing', {})
        self.ps_method = self.ps_config.get('method', 'risk_based')
        
        # Track active positions
        self.active_positions = {}
        
        logger.info("Risk manager initialized")
    
    def calculate_position_size(self, symbol: str, entry_price: float,
                                stop_loss: float, portfolio_value: float) -> int:
        """
        Calculate position size based on risk management rules
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            portfolio_value: Current portfolio value
            
        Returns:
            Number of shares to trade
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            logger.warning(f"Zero risk per share for {symbol}, using default")
            risk_per_share = entry_price * 0.02
        
        if self.ps_method == 'risk_based':
            # Risk-based position sizing
            risk_amount = portfolio_value * self.max_portfolio_risk
            position_size = int(risk_amount / risk_per_share)
            
        elif self.ps_method == 'fixed':
            # Fixed percentage of portfolio
            max_investment = portfolio_value * self.max_position_size
            position_size = int(max_investment / entry_price)
            
        elif self.ps_method == 'kelly':
            # Kelly Criterion (simplified)
            # K = W - [(1-W) / R] where W = win rate, R = avg win/avg loss
            # For safety, we use fractional Kelly (typically 25-50%)
            kelly_fraction = 0.25  # Conservative
            win_rate = 0.55  # Default assumption, should be updated with historical data
            win_loss_ratio = self.risk_reward_ratio
            
            kelly_pct = kelly_fraction * (win_rate - ((1 - win_rate) / win_loss_ratio))
            kelly_pct = max(0, min(kelly_pct, self.max_position_size))  # Cap at max position size
            
            position_size = int((portfolio_value * kelly_pct) / entry_price)
        
        else:
            raise ValueError(f"Unknown position sizing method: {self.ps_method}")
        
        # Apply maximum position size constraint
        max_shares = int((portfolio_value * self.max_position_size) / entry_price)
        position_size = min(position_size, max_shares)
        
        # Ensure at least 1 share if we have enough capital
        if position_size == 0 and portfolio_value >= entry_price:
            position_size = 1
        
        logger.info(f"Calculated position size for {symbol}: {position_size} shares")
        
        return position_size
    
    def calculate_stop_loss(self, symbol: str, entry_price: float,
                           atr: float = None, direction: str = 'long') -> float:
        """
        Calculate stop loss price
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            atr: Average True Range (required for ATR-based SL)
            direction: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        if self.sl_type == 'atr':
            if atr is None:
                raise ValueError("ATR required for ATR-based stop loss")
            
            stop_distance = atr * self.sl_atr_multiplier
            
            if direction == 'long':
                stop_loss = entry_price - stop_distance
            else:
                stop_loss = entry_price + stop_distance
        
        elif self.sl_type == 'percentage':
            if direction == 'long':
                stop_loss = entry_price * (1 - self.sl_percentage)
            else:
                stop_loss = entry_price * (1 + self.sl_percentage)
        
        elif self.sl_type == 'fixed':
            fixed_amount = self.sl_config.get('amount', 10)
            if direction == 'long':
                stop_loss = entry_price - fixed_amount
            else:
                stop_loss = entry_price + fixed_amount
        
        else:
            raise ValueError(f"Unknown stop loss type: {self.sl_type}")
        
        logger.debug(f"Calculated {direction} stop loss for {symbol}: {stop_loss:.2f}")
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                             direction: str = 'long') -> float:
        """
        Calculate take profit price based on risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'long' or 'short'
            
        Returns:
            Take profit price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * self.risk_reward_ratio
        
        if direction == 'long':
            take_profit = entry_price + reward
        else:
            take_profit = entry_price - reward
        
        logger.debug(f"Calculated take profit: {take_profit:.2f} (R:R = 1:{self.risk_reward_ratio})")
        
        return take_profit
    
    def update_trailing_stop(self, symbol: str, current_price: float,
                            position: Dict) -> Optional[float]:
        """
        Update trailing stop loss
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            position: Position dictionary
            
        Returns:
            New stop loss price or None if no update
        """
        if not self.ts_enabled:
            return None
        
        entry_price = position['entry_price']
        current_sl = position['stop_loss']
        direction = position.get('direction', 'long')
        
        if direction == 'long':
            # Calculate profit percentage
            profit_pct = (current_price - entry_price) / entry_price
            
            # Check if trailing stop should be activated
            if profit_pct >= self.ts_activation_pct:
                # Calculate new trailing stop
                trailing_sl = current_price * (1 - self.ts_trail_pct)
                
                # Only update if new SL is higher than current SL
                if trailing_sl > current_sl:
                    logger.info(f"Updating trailing stop for {symbol}: {current_sl:.2f} -> {trailing_sl:.2f}")
                    return trailing_sl
        
        else:  # short position
            profit_pct = (entry_price - current_price) / entry_price
            
            if profit_pct >= self.ts_activation_pct:
                trailing_sl = current_price * (1 + self.ts_trail_pct)
                
                if trailing_sl < current_sl:
                    logger.info(f"Updating trailing stop for {symbol}: {current_sl:.2f} -> {trailing_sl:.2f}")
                    return trailing_sl
        
        return None
    
    def can_open_position(self, symbol: str = None) -> bool:
        """
        Check if we can open a new position
        
        Args:
            symbol: Optional symbol to check if already have position
            
        Returns:
            True if we can open position
        """
        # Check if we already have a position in this symbol
        if symbol and symbol in self.active_positions:
            logger.warning(f"Already have open position in {symbol}")
            return False
        
        # Check if we've reached max open positions
        if len(self.active_positions) >= self.max_open_positions:
            logger.warning(f"Max open positions ({self.max_open_positions}) reached")
            return False
        
        return True
    
    def add_position(self, symbol: str, entry_price: float, quantity: int,
                    stop_loss: float, take_profit: float, direction: str = 'long'):
        """
        Add a new position to tracking
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Position quantity
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: 'long' or 'short'
        """
        self.active_positions[symbol] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'direction': direction,
            'entry_time': datetime.now(),
            'highest_price': entry_price if direction == 'long' else float('inf'),
            'lowest_price': entry_price if direction == 'short' else float('inf')
        }
        
        logger.info(f"Added position: {symbol} {quantity} @ {entry_price}")
    
    def remove_position(self, symbol: str):
        """
        Remove a position from tracking
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.active_positions:
            del self.active_positions[symbol]
            logger.info(f"Removed position: {symbol}")
    
    def check_exit_conditions(self, symbol: str, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should be exited
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Tuple of (should_exit, reason)
        """
        if symbol not in self.active_positions:
            return False, ""
        
        position = self.active_positions[symbol]
        direction = position['direction']
        
        # Update trailing stop if applicable
        new_sl = self.update_trailing_stop(symbol, current_price, position)
        if new_sl is not None:
            position['stop_loss'] = new_sl
        
        # Check stop loss
        if direction == 'long' and current_price <= position['stop_loss']:
            return True, "stop_loss"
        elif direction == 'short' and current_price >= position['stop_loss']:
            return True, "stop_loss"
        
        # Check take profit
        if direction == 'long' and current_price >= position['take_profit']:
            return True, "take_profit"
        elif direction == 'short' and current_price <= position['take_profit']:
            return True, "take_profit"
        
        # Update highest/lowest prices for trailing
        if direction == 'long':
            position['highest_price'] = max(position['highest_price'], current_price)
        else:
            position['lowest_price'] = min(position['lowest_price'], current_price)
        
        return False, ""
    
    def get_portfolio_risk(self, portfolio_value: float) -> float:
        """
        Calculate current portfolio risk
        
        Args:
            portfolio_value: Current portfolio value
            
        Returns:
            Portfolio risk as percentage
        """
        total_risk = 0
        
        for symbol, position in self.active_positions.items():
            entry_value = position['entry_price'] * position['quantity']
            risk_amount = abs(position['entry_price'] - position['stop_loss']) * position['quantity']
            total_risk += risk_amount
        
        if portfolio_value > 0:
            risk_pct = total_risk / portfolio_value
        else:
            risk_pct = 0
        
        return risk_pct
