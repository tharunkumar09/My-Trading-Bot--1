"""
Technical indicators module.
"""
import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate various technical indicators."""
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            data: DataFrame with 'close' column
            period: RSI period (default 14)
        
        Returns:
            Series with RSI values
        """
        try:
            import talib
            close = data['close'].values
            rsi = talib.RSI(close, timeperiod=period)
            return pd.Series(rsi, index=data.index)
        except ImportError:
            # Fallback to manual calculation
            logger.warning("TA-Lib not available, using manual RSI calculation")
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            data: DataFrame with 'close' column
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
        
        Returns:
            DataFrame with macd, signal, and histogram columns
        """
        try:
            import talib
            close = data['close'].values
            macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal)
            
            return pd.DataFrame({
                'macd': macd,
                'signal': macd_signal,
                'histogram': macd_hist
            }, index=data.index)
        except ImportError:
            # Fallback to manual calculation
            logger.warning("TA-Lib not available, using manual MACD calculation")
            ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signal, adjust=False).mean()
            histogram = macd - signal
            
            return pd.DataFrame({
                'macd': macd,
                'signal': signal,
                'histogram': histogram
            }, index=data.index)
    
    @staticmethod
    def calculate_supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
        """
        Calculate Supertrend indicator.
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            period: ATR period
            multiplier: ATR multiplier
        
        Returns:
            Series with Supertrend values
        """
        try:
            import talib
            
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            # Calculate ATR
            atr = talib.ATR(high, low, close, timeperiod=period)
            
            # Calculate basic bands
            hl_avg = (high + low) / 2
            upper_band = hl_avg + (multiplier * atr)
            lower_band = hl_avg - (multiplier * atr)
            
            # Initialize supertrend
            supertrend = np.zeros(len(data))
            direction = np.zeros(len(data))
            
            for i in range(1, len(data)):
                if close[i] > upper_band[i-1]:
                    direction[i] = 1
                elif close[i] < lower_band[i-1]:
                    direction[i] = -1
                else:
                    direction[i] = direction[i-1]
                
                if direction[i] == 1:
                    supertrend[i] = lower_band[i]
                else:
                    supertrend[i] = upper_band[i]
            
            return pd.Series(supertrend, index=data.index)
            
        except ImportError:
            # Fallback to manual calculation
            logger.warning("TA-Lib not available, using manual Supertrend calculation")
            
            # Calculate ATR manually
            high_low = data['high'] - data['low']
            high_close = np.abs(data['high'] - data['close'].shift())
            low_close = np.abs(data['low'] - data['close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            atr = true_range.rolling(period).mean()
            
            # Calculate basic bands
            hl_avg = (data['high'] + data['low']) / 2
            upper_band = hl_avg + (multiplier * atr)
            lower_band = hl_avg - (multiplier * atr)
            
            # Initialize supertrend
            supertrend = pd.Series(index=data.index, dtype=float)
            direction = pd.Series(index=data.index, dtype=float)
            
            for i in range(1, len(data)):
                if data['close'].iloc[i] > upper_band.iloc[i-1]:
                    direction.iloc[i] = 1
                elif data['close'].iloc[i] < lower_band.iloc[i-1]:
                    direction.iloc[i] = -1
                else:
                    direction.iloc[i] = direction.iloc[i-1]
                
                if direction.iloc[i] == 1:
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
            
            return supertrend
    
    @staticmethod
    def calculate_ema(data: pd.DataFrame, period: int = 200) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).
        
        Args:
            data: DataFrame with 'close' column
            period: EMA period
        
        Returns:
            Series with EMA values
        """
        return data['close'].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_volatility(data: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Calculate rolling volatility (standard deviation of returns).
        
        Args:
            data: DataFrame with 'close' column
            window: Rolling window size
        
        Returns:
            Series with volatility values
        """
        returns = data['close'].pct_change()
        return returns.rolling(window=window).std()
    
    @staticmethod
    def detect_volume_spike(data: pd.DataFrame, multiplier: float = 3.0, window: int = 20) -> pd.Series:
        """
        Detect volume spikes.
        
        Args:
            data: DataFrame with 'volume' column
            multiplier: Multiplier for average volume
            window: Rolling window for average volume
        
        Returns:
            Series with boolean values (True for volume spike)
        """
        avg_volume = data['volume'].rolling(window=window).mean()
        return data['volume'] > (multiplier * avg_volume)
    
    @staticmethod
    def add_all_indicators(data: pd.DataFrame, 
                          rsi_period: int = 14,
                          macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9,
                          supertrend_period: int = 10, supertrend_multiplier: float = 3.0,
                          ema_period: int = 200) -> pd.DataFrame:
        """
        Add all technical indicators to the dataframe.
        
        Returns:
            DataFrame with all indicators added
        """
        df = data.copy()
        
        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, rsi_period)
        
        # MACD
        macd_df = TechnicalIndicators.calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df['macd'] = macd_df['macd']
        df['macd_signal'] = macd_df['signal']
        df['macd_histogram'] = macd_df['histogram']
        
        # Supertrend
        df['supertrend'] = TechnicalIndicators.calculate_supertrend(df, supertrend_period, supertrend_multiplier)
        
        # EMA
        df['ema_200'] = TechnicalIndicators.calculate_ema(df, ema_period)
        
        # Volatility
        df['volatility'] = TechnicalIndicators.calculate_volatility(df)
        
        # Volume spike detection
        df['volume_spike'] = TechnicalIndicators.detect_volume_spike(df)
        
        return df
