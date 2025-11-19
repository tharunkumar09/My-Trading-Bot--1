"""
Technical Indicators
Implementation of RSI, MACD, Supertrend, EMA and other indicators
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Technical indicator calculations
    """
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: Price series (typically close prices)
            period: RSI period (default: 14)
            
        Returns:
            RSI series
        """
        delta = data.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26,
                       signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: Price series
            period: EMA period
            
        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            data: Price series
            period: SMA period
            
        Returns:
            SMA series
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_supertrend(df: pd.DataFrame, period: int = 10,
                            multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Supertrend indicator
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period
            multiplier: ATR multiplier
            
        Returns:
            Tuple of (Supertrend, Direction) where Direction is 1 for buy, -1 for sell
        """
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        
        # Calculate basic upper and lower bands
        hl2 = (df['high'] + df['low']) / 2
        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)
        
        # Calculate final upper and lower bands
        final_upper = pd.Series(index=df.index, dtype=float)
        final_lower = pd.Series(index=df.index, dtype=float)
        
        for i in range(period, len(df)):
            if i == period:
                final_upper.iloc[i] = basic_upper.iloc[i]
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                # Upper band
                if basic_upper.iloc[i] < final_upper.iloc[i-1] or df['close'].iloc[i-1] > final_upper.iloc[i-1]:
                    final_upper.iloc[i] = basic_upper.iloc[i]
                else:
                    final_upper.iloc[i] = final_upper.iloc[i-1]
                
                # Lower band
                if basic_lower.iloc[i] > final_lower.iloc[i-1] or df['close'].iloc[i-1] < final_lower.iloc[i-1]:
                    final_lower.iloc[i] = basic_lower.iloc[i]
                else:
                    final_lower.iloc[i] = final_lower.iloc[i-1]
        
        # Calculate Supertrend
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=float)
        
        for i in range(period, len(df)):
            if i == period:
                if df['close'].iloc[i] <= final_upper.iloc[i]:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
            else:
                if direction.iloc[i-1] == 1:
                    if df['close'].iloc[i] <= final_lower.iloc[i]:
                        supertrend.iloc[i] = final_upper.iloc[i]
                        direction.iloc[i] = -1
                    else:
                        supertrend.iloc[i] = final_lower.iloc[i]
                        direction.iloc[i] = 1
                else:
                    if df['close'].iloc[i] >= final_upper.iloc[i]:
                        supertrend.iloc[i] = final_lower.iloc[i]
                        direction.iloc[i] = 1
                    else:
                        supertrend.iloc[i] = final_upper.iloc[i]
                        direction.iloc[i] = -1
        
        return supertrend, direction
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period
            
        Returns:
            ATR series
        """
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20,
                                 std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            data: Price series
            period: Moving average period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle_band = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, k_period: int = 14,
                            d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            k_period: %K period
            d_period: %D period
            
        Returns:
            Tuple of (%K, %D)
        """
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX)
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ADX period
            
        Returns:
            ADX series
        """
        # Calculate +DM and -DM
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        pos_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        neg_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Calculate ATR
        atr = TechnicalIndicators.calculate_atr(df, period)
        
        # Calculate +DI and -DI
        pos_di = 100 * (pos_dm.rolling(window=period).mean() / atr)
        neg_di = 100 * (neg_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * np.abs(pos_di - neg_di) / (pos_di + neg_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV)
        
        Args:
            df: DataFrame with 'close' and 'volume' columns
            
        Returns:
            OBV series
        """
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['volume'].iloc[0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            
        Returns:
            VWAP series
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        return vwap
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
        """
        Add all technical indicators to DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            config: Configuration dict with indicator parameters
            
        Returns:
            DataFrame with all indicators added
        """
        if config is None:
            config = {
                'rsi': {'period': 14},
                'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                'ema': {'period': 200},
                'supertrend': {'period': 10, 'multiplier': 3.0}
            }
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # RSI
        if 'rsi' in config:
            df['rsi'] = TechnicalIndicators.calculate_rsi(
                df['close'],
                period=config['rsi'].get('period', 14)
            )
        
        # MACD
        if 'macd' in config:
            macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(
                df['close'],
                fast=config['macd'].get('fast_period', 12),
                slow=config['macd'].get('slow_period', 26),
                signal=config['macd'].get('signal_period', 9)
            )
            df['macd_line'] = macd_line
            df['macd_signal'] = signal_line
            df['macd_histogram'] = histogram
        
        # EMA
        if 'ema' in config:
            df['ema_200'] = TechnicalIndicators.calculate_ema(
                df['close'],
                period=config['ema'].get('period', 200)
            )
        
        # Supertrend
        if 'supertrend' in config:
            supertrend, direction = TechnicalIndicators.calculate_supertrend(
                df,
                period=config['supertrend'].get('period', 10),
                multiplier=config['supertrend'].get('multiplier', 3.0)
            )
            df['supertrend'] = supertrend
            df['supertrend_direction'] = direction
        
        # ATR (for stop loss calculations)
        df['atr'] = TechnicalIndicators.calculate_atr(df, period=14)
        
        # Additional indicators
        df['ema_50'] = TechnicalIndicators.calculate_ema(df['close'], period=50)
        df['sma_20'] = TechnicalIndicators.calculate_sma(df['close'], period=20)
        
        logger.info(f"Added {len([c for c in df.columns if c not in required_cols])} indicators to DataFrame")
        
        return df
