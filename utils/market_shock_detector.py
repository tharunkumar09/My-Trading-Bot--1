"""
Market shock detection module for handling sudden market events.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import get_logger
from config.config import (
    VOLATILITY_THRESHOLD, VOLUME_SPIKE_MULTIPLIER, SHOCK_DETECTION_WINDOW
)

logger = get_logger(__name__)


class MarketShockDetector:
    """Detect and handle market shocks and sudden events."""
    
    def __init__(self):
        self.shock_history = []
        self.alert_thresholds = {
            'price_change': 0.05,  # 5% price change
            'volume_spike': VOLUME_SPIKE_MULTIPLIER,
            'volatility': VOLATILITY_THRESHOLD,
            'time_window': SHOCK_DETECTION_WINDOW  # minutes
        }
    
    def detect_price_shock(self, data: pd.DataFrame, window: int = 5) -> Optional[Dict]:
        """
        Detect sudden price movements (potential earnings, news, etc.).
        
        Args:
            data: DataFrame with price data
            window: Time window in minutes to check
        
        Returns:
            Dict with shock details if detected, None otherwise
        """
        if len(data) < window + 1:
            return None
        
        recent_data = data.tail(window + 1)
        price_change = abs((recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0])
        
        if price_change >= self.alert_thresholds['price_change']:
            shock_info = {
                'type': 'price_shock',
                'magnitude': price_change,
                'direction': 'up' if recent_data['close'].iloc[-1] > recent_data['close'].iloc[0] else 'down',
                'timestamp': datetime.now(),
                'price_before': recent_data['close'].iloc[0],
                'price_after': recent_data['close'].iloc[-1]
            }
            logger.warning(f"Price shock detected: {price_change*100:.2f}% {shock_info['direction']}")
            self.shock_history.append(shock_info)
            return shock_info
        
        return None
    
    def detect_volume_shock(self, data: pd.DataFrame, window: int = 20) -> Optional[Dict]:
        """
        Detect volume spikes (potential news, events, etc.).
        
        Args:
            data: DataFrame with volume data
            window: Rolling window for average volume
        
        Returns:
            Dict with shock details if detected, None otherwise
        """
        if len(data) < window + 1:
            return None
        
        recent_data = data.tail(window + 1)
        avg_volume = recent_data['volume'].iloc[:-1].mean()
        current_volume = recent_data['volume'].iloc[-1]
        
        if avg_volume > 0 and current_volume >= (avg_volume * self.alert_thresholds['volume_spike']):
            volume_ratio = current_volume / avg_volume
            shock_info = {
                'type': 'volume_shock',
                'magnitude': volume_ratio,
                'timestamp': datetime.now(),
                'avg_volume': avg_volume,
                'current_volume': current_volume
            }
            logger.warning(f"Volume shock detected: {volume_ratio:.2f}x average volume")
            self.shock_history.append(shock_info)
            return shock_info
        
        return None
    
    def detect_volatility_shock(self, data: pd.DataFrame, window: int = 20) -> Optional[Dict]:
        """
        Detect sudden volatility increase.
        
        Args:
            data: DataFrame with price data
            window: Rolling window for volatility calculation
        
        Returns:
            Dict with shock details if detected, None otherwise
        """
        if len(data) < window + 1:
            return None
        
        recent_data = data.tail(window + 1)
        returns = recent_data['close'].pct_change().dropna()
        current_volatility = returns.std()
        
        if current_volatility >= self.alert_thresholds['volatility']:
            shock_info = {
                'type': 'volatility_shock',
                'magnitude': current_volatility,
                'timestamp': datetime.now()
            }
            logger.warning(f"Volatility shock detected: {current_volatility:.4f}")
            self.shock_history.append(shock_info)
            return shock_info
        
        return None
    
    def detect_gap(self, previous_close: float, current_open: float) -> Optional[Dict]:
        """
        Detect price gaps (overnight news, earnings, etc.).
        
        Args:
            previous_close: Previous day's close
            current_open: Current day's open
        
        Returns:
            Dict with gap details if significant, None otherwise
        """
        if previous_close == 0:
            return None
        
        gap_percentage = abs((current_open - previous_close) / previous_close)
        
        if gap_percentage >= 0.02:  # 2% gap threshold
            gap_info = {
                'type': 'gap',
                'magnitude': gap_percentage,
                'direction': 'up' if current_open > previous_close else 'down',
                'timestamp': datetime.now(),
                'previous_close': previous_close,
                'current_open': current_open
            }
            logger.warning(f"Price gap detected: {gap_percentage*100:.2f}% {gap_info['direction']}")
            self.shock_history.append(gap_info)
            return gap_info
        
        return None
    
    def detect_all_shocks(self, data: pd.DataFrame, previous_close: float = None) -> Dict:
        """
        Run all shock detection methods.
        
        Returns:
            Dict with all detected shocks
        """
        shocks = {}
        
        # Price shock
        price_shock = self.detect_price_shock(data)
        if price_shock:
            shocks['price'] = price_shock
        
        # Volume shock
        volume_shock = self.detect_volume_shock(data)
        if volume_shock:
            shocks['volume'] = volume_shock
        
        # Volatility shock
        volatility_shock = self.detect_volatility_shock(data)
        if volatility_shock:
            shocks['volatility'] = volatility_shock
        
        # Gap detection (if previous close available)
        if previous_close is not None and len(data) > 0:
            gap = self.detect_gap(previous_close, data['open'].iloc[-1])
            if gap:
                shocks['gap'] = gap
        
        return shocks
    
    def should_reduce_position_size(self, shocks: Dict) -> bool:
        """
        Determine if position size should be reduced due to market shocks.
        
        Returns:
            True if position size should be reduced
        """
        # Reduce position size if multiple shocks detected
        if len(shocks) >= 2:
            return True
        
        # Reduce if extreme price shock
        if 'price' in shocks and shocks['price']['magnitude'] >= 0.10:  # 10% move
            return True
        
        # Reduce if extreme volatility
        if 'volatility' in shocks and shocks['volatility']['magnitude'] >= 0.08:  # 8% volatility
            return True
        
        return False
    
    def should_exit_positions(self, shocks: Dict) -> bool:
        """
        Determine if all positions should be exited due to extreme market conditions.
        
        Returns:
            True if positions should be exited
        """
        # Exit if extreme price shock (>15%)
        if 'price' in shocks and shocks['price']['magnitude'] >= 0.15:
            return True
        
        # Exit if extreme volatility (>10%)
        if 'volatility' in shocks and shocks['volatility']['magnitude'] >= 0.10:
            return True
        
        # Exit if gap > 5%
        if 'gap' in shocks and shocks['gap']['magnitude'] >= 0.05:
            return True
        
        return False
    
    def get_adaptive_risk_multiplier(self, shocks: Dict) -> float:
        """
        Get adaptive risk multiplier based on detected shocks.
        Reduces risk during uncertain market conditions.
        
        Returns:
            Risk multiplier (0.0 to 1.0)
        """
        if not shocks:
            return 1.0  # Normal risk
        
        # Start with full risk
        multiplier = 1.0
        
        # Reduce risk for each shock type
        if 'price' in shocks:
            multiplier *= 0.7  # Reduce to 70%
        
        if 'volume' in shocks:
            multiplier *= 0.8  # Reduce to 80%
        
        if 'volatility' in shocks:
            multiplier *= 0.6  # Reduce to 60%
        
        if 'gap' in shocks:
            multiplier *= 0.5  # Reduce to 50%
        
        # Minimum multiplier
        multiplier = max(multiplier, 0.2)
        
        logger.info(f"Adaptive risk multiplier: {multiplier:.2f}")
        return multiplier
