"""
Technical Indicators Implementation
RSI, MACD, Supertrend, EMA
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from loguru import logger

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available, using pandas-based implementations")


class TechnicalIndicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: Price series (typically close prices)
            period: RSI period (default 14)
            
        Returns:
            RSI values as pandas Series
        """
        if TALIB_AVAILABLE:
            return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
        
        # Manual RSI calculation
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data: Price series (typically close prices)
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        if TALIB_AVAILABLE:
            macd, signal, histogram = talib.MACD(
                data.values,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )
            return (
                pd.Series(macd, index=data.index),
                pd.Series(signal, index=data.index),
                pd.Series(histogram, index=data.index)
            )
        
        # Manual MACD calculation
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_supertrend(
        df: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Supertrend indicator
        
        Args:
            df: DataFrame with High, Low, Close columns
            period: ATR period (default 10)
            multiplier: ATR multiplier (default 3.0)
            
        Returns:
            Tuple of (Supertrend values, Trend direction: 1 for uptrend, -1 for downtrend)
        """
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate ATR
        if TALIB_AVAILABLE:
            atr = pd.Series(talib.ATR(high.values, low.values, close.values, timeperiod=period), index=df.index)
        else:
            # Manual ATR calculation
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
        
        # Calculate basic bands
        hl_avg = (high + low) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Initialize Supertrend
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(len(df)):
            if i == 0:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = 1
            else:
                # Update upper and lower bands
                if close.iloc[i] <= supertrend.iloc[i-1]:
                    upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i-1])
                else:
                    upper_band.iloc[i] = upper_band.iloc[i]
                
                if close.iloc[i] >= supertrend.iloc[i-1]:
                    lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i-1])
                else:
                    lower_band.iloc[i] = lower_band.iloc[i]
                
                # Determine Supertrend
                if close.iloc[i] <= supertrend.iloc[i-1]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
        
        return supertrend, direction
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int = 200) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: Price series
            period: EMA period (default 200)
            
        Returns:
            EMA values as pandas Series
        """
        if TALIB_AVAILABLE:
            return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
        
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            data: Price series
            period: SMA period
            
        Returns:
            SMA values as pandas Series
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            data: Price series
            period: Moving average period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        if TALIB_AVAILABLE:
            upper, middle, lower = talib.BBANDS(
                data.values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev
            )
            return (
                pd.Series(upper, index=data.index),
                pd.Series(middle, index=data.index),
                pd.Series(lower, index=data.index)
            )
        
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        supertrend_period: int = 10,
        supertrend_multiplier: float = 3.0,
        ema_period: int = 200
    ) -> pd.DataFrame:
        """
        Calculate all indicators and add to DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            supertrend_period: Supertrend period
            supertrend_multiplier: Supertrend multiplier
            ema_period: EMA period
            
        Returns:
            DataFrame with all indicators added
        """
        result_df = df.copy()
        
        # RSI
        result_df['RSI'] = TechnicalIndicators.calculate_rsi(df['Close'], rsi_period)
        
        # MACD
        macd, signal, histogram = TechnicalIndicators.calculate_macd(
            df['Close'], macd_fast, macd_slow, macd_signal
        )
        result_df['MACD'] = macd
        result_df['MACD_Signal'] = signal
        result_df['MACD_Histogram'] = histogram
        
        # Supertrend
        supertrend, direction = TechnicalIndicators.calculate_supertrend(
            df, supertrend_period, supertrend_multiplier
        )
        result_df['Supertrend'] = supertrend
        result_df['Supertrend_Direction'] = direction
        
        # EMA
        result_df[f'EMA_{ema_period}'] = TechnicalIndicators.calculate_ema(df['Close'], ema_period)
        
        return result_df
