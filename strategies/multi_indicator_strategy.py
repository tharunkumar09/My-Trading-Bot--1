"""
Multi-indicator trading strategy combining RSI, MACD, Supertrend, and EMA.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from utils.logger import get_logger
from utils.indicators import TechnicalIndicators
from config.config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
    EMA_PERIOD
)

logger = get_logger(__name__)


class MultiIndicatorStrategy:
    """Trading strategy using multiple technical indicators."""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.last_signal = None  # Track last signal to avoid whipsaws
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on multiple indicators.
        
        Strategy Rules:
        - BUY Signal:
          1. RSI < 30 (oversold)
          2. MACD line crosses above signal line (bullish crossover)
          3. Price above Supertrend (uptrend)
          4. Price above 200-day EMA (long-term uptrend)
        
        - SELL Signal:
          1. RSI > 70 (overbought)
          2. MACD line crosses below signal line (bearish crossover)
          3. Price below Supertrend (downtrend)
          4. Price below 200-day EMA (long-term downtrend)
        
        Returns:
            DataFrame with signals added
        """
        df = data.copy()
        
        # Ensure we have all required indicators
        if 'rsi' not in df.columns:
            df = self.indicators.add_all_indicators(
                df,
                rsi_period=RSI_PERIOD,
                macd_fast=MACD_FAST, macd_slow=MACD_SLOW, macd_signal=MACD_SIGNAL,
                supertrend_period=SUPERTREND_PERIOD, supertrend_multiplier=SUPERTREND_MULTIPLIER,
                ema_period=EMA_PERIOD
            )
        
        # Initialize signal column
        df['signal'] = 0
        df['position'] = 0
        
        # Generate signals
        for i in range(1, len(df)):
            # Check for BUY signal
            buy_conditions = (
                df['rsi'].iloc[i] < RSI_OVERSOLD and  # RSI oversold
                df['macd'].iloc[i] > df['macd_signal'].iloc[i] and  # MACD bullish
                df['macd'].iloc[i-1] <= df['macd_signal'].iloc[i-1] and  # MACD crossover
                df['close'].iloc[i] > df['supertrend'].iloc[i] and  # Above Supertrend
                df['close'].iloc[i] > df['ema_200'].iloc[i]  # Above 200 EMA
            )
            
            # Check for SELL signal
            sell_conditions = (
                df['rsi'].iloc[i] > RSI_OVERBOUGHT and  # RSI overbought
                df['macd'].iloc[i] < df['macd_signal'].iloc[i] and  # MACD bearish
                df['macd'].iloc[i-1] >= df['macd_signal'].iloc[i-1] and  # MACD crossover
                df['close'].iloc[i] < df['supertrend'].iloc[i] and  # Below Supertrend
                df['close'].iloc[i] < df['ema_200'].iloc[i]  # Below 200 EMA
            )
            
            if buy_conditions:
                df.loc[df.index[i], 'signal'] = 1  # BUY
            elif sell_conditions:
                df.loc[df.index[i], 'signal'] = -1  # SELL
        
        # Generate positions (hold until opposite signal)
        position = 0
        for i in range(len(df)):
            if df['signal'].iloc[i] == 1:
                position = 1  # Long
            elif df['signal'].iloc[i] == -1:
                position = -1  # Short/Exit
            df.loc[df.index[i], 'position'] = position
        
        return df
    
    def get_current_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Get current trading signal from latest data.
        
        Returns:
            Dict with signal details or None
        """
        if len(data) < 2:
            return None
        
        # Ensure indicators are calculated
        if 'rsi' not in data.columns:
            data = self.indicators.add_all_indicators(
                data,
                rsi_period=RSI_PERIOD,
                macd_fast=MACD_FAST, macd_slow=MACD_SLOW, macd_signal=MACD_SIGNAL,
                supertrend_period=SUPERTREND_PERIOD, supertrend_multiplier=SUPERTREND_MULTIPLIER,
                ema_period=EMA_PERIOD
            )
        
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Check BUY conditions
        buy_conditions = (
            latest['rsi'] < RSI_OVERSOLD and
            latest['macd'] > latest['macd_signal'] and
            previous['macd'] <= previous['macd_signal'] and
            latest['close'] > latest['supertrend'] and
            latest['close'] > latest['ema_200']
        )
        
        # Check SELL conditions
        sell_conditions = (
            latest['rsi'] > RSI_OVERBOUGHT and
            latest['macd'] < latest['macd_signal'] and
            previous['macd'] >= previous['macd_signal'] and
            latest['close'] < latest['supertrend'] and
            latest['close'] < latest['ema_200']
        )
        
        if buy_conditions:
            return {
                'signal': 'BUY',
                'strength': self._calculate_signal_strength(latest, 'BUY'),
                'price': latest['close'],
                'rsi': latest['rsi'],
                'macd': latest['macd'],
                'macd_signal': latest['macd_signal']
            }
        elif sell_conditions:
            return {
                'signal': 'SELL',
                'strength': self._calculate_signal_strength(latest, 'SELL'),
                'price': latest['close'],
                'rsi': latest['rsi'],
                'macd': latest['macd'],
                'macd_signal': latest['macd_signal']
            }
        
        return None
    
    def _calculate_signal_strength(self, row: pd.Series, signal_type: str) -> float:
        """
        Calculate signal strength (0.0 to 1.0).
        
        Args:
            row: Latest data row
            signal_type: 'BUY' or 'SELL'
        
        Returns:
            Signal strength (0.0 to 1.0)
        """
        strength = 0.0
        
        if signal_type == 'BUY':
            # RSI contribution (lower is better for buy)
            rsi_score = max(0, (RSI_OVERSOLD - row['rsi']) / RSI_OVERSOLD)
            strength += rsi_score * 0.25
            
            # MACD contribution
            if row['macd'] > row['macd_signal']:
                macd_diff = (row['macd'] - row['macd_signal']) / abs(row['macd_signal']) if row['macd_signal'] != 0 else 0
                strength += min(macd_diff * 10, 1.0) * 0.25
            
            # Supertrend contribution
            if row['close'] > row['supertrend']:
                supertrend_diff = (row['close'] - row['supertrend']) / row['supertrend']
                strength += min(supertrend_diff * 10, 1.0) * 0.25
            
            # EMA contribution
            if row['close'] > row['ema_200']:
                ema_diff = (row['close'] - row['ema_200']) / row['ema_200']
                strength += min(ema_diff * 5, 1.0) * 0.25
        
        else:  # SELL
            # RSI contribution (higher is better for sell)
            rsi_score = max(0, (row['rsi'] - RSI_OVERBOUGHT) / (100 - RSI_OVERBOUGHT))
            strength += rsi_score * 0.25
            
            # MACD contribution
            if row['macd'] < row['macd_signal']:
                macd_diff = (row['macd_signal'] - row['macd']) / abs(row['macd_signal']) if row['macd_signal'] != 0 else 0
                strength += min(macd_diff * 10, 1.0) * 0.25
            
            # Supertrend contribution
            if row['close'] < row['supertrend']:
                supertrend_diff = (row['supertrend'] - row['close']) / row['supertrend']
                strength += min(supertrend_diff * 10, 1.0) * 0.25
            
            # EMA contribution
            if row['close'] < row['ema_200']:
                ema_diff = (row['ema_200'] - row['close']) / row['ema_200']
                strength += min(ema_diff * 5, 1.0) * 0.25
        
        return min(strength, 1.0)
    
    def should_enter_trade(self, signal: Dict, current_position: Optional[Dict] = None) -> bool:
        """
        Determine if trade should be entered based on signal and current position.
        
        Args:
            signal: Signal dict from get_current_signal
            current_position: Current position dict (if any)
        
        Returns:
            True if trade should be entered
        """
        if not signal:
            return False
        
        # Don't enter if already in position
        if current_position:
            return False
        
        # Only enter if signal strength is above threshold
        if signal.get('strength', 0) < 0.5:
            return False
        
        # Avoid whipsaws - don't enter if same signal type as last time
        if self.last_signal and self.last_signal.get('signal') == signal.get('signal'):
            return False
        
        self.last_signal = signal
        return True
    
    def should_exit_trade(self, signal: Dict, current_position: Optional[Dict] = None) -> bool:
        """
        Determine if trade should be exited.
        
        Args:
            signal: Signal dict from get_current_signal
            current_position: Current position dict
        
        Returns:
            True if trade should be exited
        """
        if not current_position:
            return False
        
        # Exit on opposite signal
        if signal and signal.get('signal') == 'SELL' and current_position.get('is_long', True):
            return True
        
        return False
