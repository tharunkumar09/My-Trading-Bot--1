"""
Trading Strategy Implementation
Combines RSI, MACD, Supertrend, and EMA for entry/exit signals
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger

from src.indicators.technical_indicators import TechnicalIndicators
from config import Config


class TradingStrategy:
    """
    Rule-based trading strategy combining multiple indicators
    
    Entry Rules:
    1. RSI < 30 (oversold) OR RSI > 70 (overbought reversal)
    2. MACD crossover (bullish: MACD crosses above signal)
    3. Supertrend indicates uptrend (direction = 1)
    4. Price above 200 EMA (trend filter)
    
    Exit Rules:
    1. Stop loss hit
    2. Trailing stop loss triggered
    3. RSI > 70 (overbought) for long positions
    4. MACD bearish crossover
    5. Supertrend changes to downtrend
    """
    
    def __init__(
        self,
        rsi_period: int = None,
        macd_fast: int = None,
        macd_slow: int = None,
        macd_signal: int = None,
        supertrend_period: int = None,
        supertrend_multiplier: float = None,
        ema_period: int = None
    ):
        """
        Initialize strategy with indicator parameters
        
        Args:
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            supertrend_period: Supertrend period
            supertrend_multiplier: Supertrend multiplier
            ema_period: EMA period
        """
        self.rsi_period = rsi_period or Config.RSI_PERIOD
        self.macd_fast = macd_fast or Config.MACD_FAST
        self.macd_slow = macd_slow or Config.MACD_SLOW
        self.macd_signal = macd_signal or Config.MACD_SIGNAL
        self.supertrend_period = supertrend_period or Config.SUPERTREND_PERIOD
        self.supertrend_multiplier = supertrend_multiplier or Config.SUPERTREND_MULTIPLIER
        self.ema_period = ema_period or Config.EMA_PERIOD
        
        self.indicators = TechnicalIndicators()
    
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate trading signals for given data
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals added
        """
        if len(df) < max(self.ema_period, self.macd_slow, self.supertrend_period):
            logger.warning("Insufficient data for indicator calculation")
            df['Signal'] = 0
            df['Entry_Price'] = np.nan
            df['Stop_Loss'] = np.nan
            return df
        
        # Calculate all indicators
        df = self.indicators.calculate_all_indicators(
            df,
            rsi_period=self.rsi_period,
            macd_fast=self.macd_fast,
            macd_slow=self.macd_slow,
            macd_signal=self.macd_signal,
            supertrend_period=self.supertrend_period,
            supertrend_multiplier=self.supertrend_multiplier,
            ema_period=self.ema_period
        )
        
        # Initialize signal columns
        df['Signal'] = 0  # 0: No signal, 1: Buy, -1: Sell
        df['Entry_Price'] = np.nan
        df['Stop_Loss'] = np.nan
        df['Reason'] = ''
        
        # Calculate signals
        for i in range(1, len(df)):
            signal, entry_price, stop_loss, reason = self._check_entry_conditions(df, i)
            if signal != 0:
                df.loc[df.index[i], 'Signal'] = signal
                df.loc[df.index[i], 'Entry_Price'] = entry_price
                df.loc[df.index[i], 'Stop_Loss'] = stop_loss
                df.loc[df.index[i], 'Reason'] = reason
        
        return df
    
    def _check_entry_conditions(
        self,
        df: pd.DataFrame,
        index: int
    ) -> Tuple[int, float, float, str]:
        """
        Check entry conditions for a given index
        
        Args:
            df: DataFrame with indicators
            index: Current index
            
        Returns:
            Tuple of (signal, entry_price, stop_loss, reason)
        """
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        
        # Check if all indicators are available
        if pd.isna(current['RSI']) or pd.isna(current['MACD']) or pd.isna(current['Supertrend']):
            return 0, np.nan, np.nan, ''
        
        # Entry Conditions for LONG position
        rsi_oversold = current['RSI'] < 30
        rsi_overbought_reversal = current['RSI'] > 70 and previous['RSI'] <= 70
        
        macd_bullish_crossover = (
            current['MACD'] > current['MACD_Signal'] and
            previous['MACD'] <= previous['MACD_Signal']
        )
        macd_above_signal = current['MACD'] > current['MACD_Signal']
        
        supertrend_uptrend = current['Supertrend_Direction'] == 1
        price_above_ema = current['Close'] > current[f'EMA_{self.ema_period}']
        
        # Combined entry logic
        if (rsi_oversold or rsi_overbought_reversal) and macd_bullish_crossover and supertrend_uptrend and price_above_ema:
            entry_price = current['Close']
            stop_loss = entry_price * (1 - Config.STOP_LOSS_PERCENT)
            reason = f"RSI:{current['RSI']:.2f}, MACD crossover, Supertrend uptrend"
            return 1, entry_price, stop_loss, reason
        
        # Alternative entry: Strong MACD + Supertrend alignment
        if macd_above_signal and supertrend_uptrend and price_above_ema and current['RSI'] < 50:
            entry_price = current['Close']
            stop_loss = entry_price * (1 - Config.STOP_LOSS_PERCENT)
            reason = f"MACD bullish, Supertrend uptrend, RSI:{current['RSI']:.2f}"
            return 1, entry_price, stop_loss, reason
        
        return 0, np.nan, np.nan, ''
    
    def check_exit_conditions(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_index: int,
        current_index: int,
        position_type: str = 'LONG'
    ) -> Tuple[bool, str, float]:
        """
        Check exit conditions for an open position
        
        Args:
            df: DataFrame with indicators
            entry_price: Entry price of position
            entry_index: Index when position was entered
            current_index: Current index
            position_type: Position type (LONG or SHORT)
            
        Returns:
            Tuple of (should_exit, reason, exit_price)
        """
        if current_index >= len(df):
            return False, '', np.nan
        
        current = df.iloc[current_index]
        
        # Stop loss check
        if position_type == 'LONG':
            if current['Low'] <= entry_price * (1 - Config.STOP_LOSS_PERCENT):
                return True, 'Stop Loss Hit', entry_price * (1 - Config.STOP_LOSS_PERCENT)
        
        # Trailing stop loss
        highest_since_entry = df.loc[df.index[entry_index]:df.index[current_index], 'High'].max()
        trailing_stop = highest_since_entry * (1 - Config.TRAILING_STOP_PERCENT)
        
        if position_type == 'LONG' and current['Low'] <= trailing_stop:
            return True, 'Trailing Stop Loss', trailing_stop
        
        # RSI overbought exit
        if position_type == 'LONG' and current['RSI'] > 70:
            return True, f'RSI Overbought: {current["RSI"]:.2f}', current['Close']
        
        # MACD bearish crossover exit
        if current_index > 0:
            previous = df.iloc[current_index - 1]
            macd_bearish_crossover = (
                current['MACD'] < current['MACD_Signal'] and
                previous['MACD'] >= previous['MACD_Signal']
            )
            if macd_bearish_crossover:
                return True, 'MACD Bearish Crossover', current['Close']
        
        # Supertrend reversal exit
        if current['Supertrend_Direction'] == -1:
            return True, 'Supertrend Downtrend', current['Close']
        
        # Price below EMA exit
        if current['Close'] < current[f'EMA_{self.ema_period}']:
            return True, 'Price Below EMA', current['Close']
        
        return False, '', np.nan
    
    def get_signal_strength(self, df: pd.DataFrame, index: int) -> float:
        """
        Calculate signal strength (0-1) based on indicator alignment
        
        Args:
            df: DataFrame with indicators
            index: Current index
            
        Returns:
            Signal strength between 0 and 1
        """
        if index >= len(df):
            return 0.0
        
        current = df.iloc[index]
        
        if pd.isna(current['RSI']) or pd.isna(current['MACD']):
            return 0.0
        
        strength = 0.0
        
        # RSI contribution (0-0.3)
        if current['RSI'] < 30:
            strength += 0.3
        elif current['RSI'] < 40:
            strength += 0.2
        
        # MACD contribution (0-0.3)
        if current['MACD'] > current['MACD_Signal']:
            macd_diff = (current['MACD'] - current['MACD_Signal']) / abs(current['MACD_Signal']) if current['MACD_Signal'] != 0 else 0
            strength += min(0.3, macd_diff * 10)
        
        # Supertrend contribution (0-0.2)
        if current['Supertrend_Direction'] == 1:
            strength += 0.2
        
        # EMA trend contribution (0-0.2)
        if current['Close'] > current[f'EMA_{self.ema_period}']:
            strength += 0.2
        
        return min(1.0, strength)
