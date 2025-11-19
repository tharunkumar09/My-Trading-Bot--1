"""
Momentum Trading Strategy
Multi-indicator strategy combining RSI, MACD, Supertrend, and EMA trend filter
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from src.indicators.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class MomentumStrategy:
    """
    Multi-indicator momentum strategy
    
    Entry Rules (All must be true):
    1. RSI < oversold threshold (default: 30)
    2. MACD line crosses above signal line (bullish crossover)
    3. Price above 200 EMA (uptrend filter)
    4. Supertrend indicates buy signal
    
    Exit Rules (Any can trigger):
    1. RSI > overbought threshold (default: 70)
    2. MACD line crosses below signal line (bearish crossover)
    3. Stop loss hit
    4. Target hit
    5. Trailing stop triggered
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize strategy with configuration
        
        Args:
            config: Strategy configuration dict
        """
        self.config = config or {}
        
        # Indicator parameters
        self.rsi_period = self.config.get('indicators', {}).get('rsi', {}).get('period', 14)
        self.rsi_oversold = self.config.get('indicators', {}).get('rsi', {}).get('oversold', 30)
        self.rsi_overbought = self.config.get('indicators', {}).get('rsi', {}).get('overbought', 70)
        
        self.macd_fast = self.config.get('indicators', {}).get('macd', {}).get('fast_period', 12)
        self.macd_slow = self.config.get('indicators', {}).get('macd', {}).get('slow_period', 26)
        self.macd_signal = self.config.get('indicators', {}).get('macd', {}).get('signal_period', 9)
        
        self.ema_period = self.config.get('indicators', {}).get('ema', {}).get('period', 200)
        
        self.supertrend_period = self.config.get('indicators', {}).get('supertrend', {}).get('period', 10)
        self.supertrend_multiplier = self.config.get('indicators', {}).get('supertrend', {}).get('multiplier', 3.0)
        
        logger.info("Momentum strategy initialized")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with indicators added
        """
        indicator_config = {
            'rsi': {'period': self.rsi_period},
            'macd': {
                'fast_period': self.macd_fast,
                'slow_period': self.macd_slow,
                'signal_period': self.macd_signal
            },
            'ema': {'period': self.ema_period},
            'supertrend': {
                'period': self.supertrend_period,
                'multiplier': self.supertrend_multiplier
            }
        }
        
        return TechnicalIndicators.add_all_indicators(df, indicator_config)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on strategy rules
        
        Args:
            df: DataFrame with OHLCV data and indicators
            
        Returns:
            DataFrame with 'signal' column (-1: sell, 0: hold, 1: buy)
        """
        # Ensure indicators are calculated
        if 'rsi' not in df.columns:
            df = self.calculate_indicators(df)
        
        # Initialize signal column
        df['signal'] = 0
        
        # MACD crossover detection
        df['macd_crossover'] = 0
        df.loc[
            (df['macd_line'] > df['macd_signal']) &
            (df['macd_line'].shift(1) <= df['macd_signal'].shift(1)),
            'macd_crossover'
        ] = 1  # Bullish crossover
        
        df.loc[
            (df['macd_line'] < df['macd_signal']) &
            (df['macd_line'].shift(1) >= df['macd_signal'].shift(1)),
            'macd_crossover'
        ] = -1  # Bearish crossover
        
        # Buy signals (all conditions must be true)
        buy_condition = (
            (df['rsi'] < self.rsi_oversold) &
            (df['macd_crossover'] == 1) &
            (df['close'] > df['ema_200']) &
            (df['supertrend_direction'] == 1)
        )
        
        df.loc[buy_condition, 'signal'] = 1
        
        # Sell signals (any condition can trigger)
        sell_condition = (
            (df['rsi'] > self.rsi_overbought) |
            (df['macd_crossover'] == -1)
        )
        
        df.loc[sell_condition, 'signal'] = -1
        
        logger.debug(f"Generated {(df['signal'] == 1).sum()} buy signals and {(df['signal'] == -1).sum()} sell signals")
        
        return df
    
    def get_entry_signal(self, df: pd.DataFrame, index: int = -1) -> bool:
        """
        Check if entry signal is present at given index
        
        Args:
            df: DataFrame with signals
            index: Index to check (default: -1 for latest)
            
        Returns:
            True if buy signal present
        """
        if 'signal' not in df.columns:
            df = self.generate_signals(df)
        
        return df.iloc[index]['signal'] == 1
    
    def get_exit_signal(self, df: pd.DataFrame, entry_price: float,
                       stop_loss: float, take_profit: float, index: int = -1) -> Tuple[bool, str]:
        """
        Check if exit signal is present
        
        Args:
            df: DataFrame with signals
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            index: Index to check
            
        Returns:
            Tuple of (should_exit, reason)
        """
        if 'signal' not in df.columns:
            df = self.generate_signals(df)
        
        current_price = df.iloc[index]['close']
        
        # Check stop loss
        if current_price <= stop_loss:
            return True, "stop_loss"
        
        # Check take profit
        if current_price >= take_profit:
            return True, "take_profit"
        
        # Check strategy signal
        if df.iloc[index]['signal'] == -1:
            return True, "strategy_signal"
        
        return False, ""
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000,
                 risk_per_trade: float = 0.02, risk_reward: float = 2.0) -> Dict:
        """
        Simple backtest of the strategy
        
        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital
            risk_per_trade: Risk per trade as fraction of capital
            risk_reward: Risk-reward ratio for take profit
            
        Returns:
            Dictionary with backtest results
        """
        # Generate signals
        df = self.generate_signals(df)
        
        # Initialize tracking variables
        capital = initial_capital
        position = None
        trades = []
        equity_curve = [initial_capital]
        
        for i in range(200, len(df)):  # Start after EMA 200 warmup
            current_price = df.iloc[i]['close']
            current_atr = df.iloc[i]['atr']
            
            # Check for exit if in position
            if position is not None:
                should_exit, reason = self.get_exit_signal(
                    df, position['entry_price'],
                    position['stop_loss'],
                    position['take_profit'],
                    index=i
                )
                
                if should_exit:
                    # Exit trade
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    capital += pnl
                    
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return_pct': (pnl / position['entry_value']) * 100,
                        'exit_reason': reason
                    })
                    
                    position = None
            
            # Check for entry if not in position
            elif self.get_entry_signal(df, index=i):
                # Calculate position size based on risk
                risk_amount = capital * risk_per_trade
                stop_distance = 2 * current_atr  # 2 ATR stop loss
                
                quantity = int(risk_amount / stop_distance)
                entry_value = quantity * current_price
                
                # Only enter if we have enough capital
                if entry_value <= capital * 0.95:  # Use max 95% of capital
                    position = {
                        'entry_date': df.index[i],
                        'entry_price': current_price,
                        'quantity': quantity,
                        'entry_value': entry_value,
                        'stop_loss': current_price - stop_distance,
                        'take_profit': current_price + (stop_distance * risk_reward)
                    }
            
            equity_curve.append(capital + (
                (current_price - position['entry_price']) * position['quantity']
                if position else 0
            ))
        
        # Close any open position
        if position is not None:
            final_price = df.iloc[-1]['close']
            pnl = (final_price - position['entry_price']) * position['quantity']
            capital += pnl
            
            trades.append({
                'entry_date': position['entry_date'],
                'exit_date': df.index[-1],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'return_pct': (pnl / position['entry_value']) * 100,
                'exit_reason': 'end_of_data'
            })
        
        # Calculate metrics
        trades_df = pd.DataFrame(trades)
        
        if len(trades_df) > 0:
            total_return = ((capital - initial_capital) / initial_capital) * 100
            winning_trades = trades_df[trades_df['pnl'] > 0]
            win_rate = (len(winning_trades) / len(trades_df)) * 100
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].mean()) if len(trades_df[trades_df['pnl'] < 0]) > 0 else 0
            
            results = {
                'initial_capital': initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'total_trades': len(trades_df),
                'winning_trades': len(winning_trades),
                'losing_trades': len(trades_df) - len(winning_trades),
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': avg_win / avg_loss if avg_loss > 0 else float('inf'),
                'trades': trades_df,
                'equity_curve': equity_curve
            }
        else:
            results = {
                'initial_capital': initial_capital,
                'final_capital': capital,
                'total_return': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'trades': trades_df,
                'equity_curve': equity_curve
            }
        
        logger.info(f"Backtest completed: {results['total_trades']} trades, {results['win_rate']:.2f}% win rate, {results['total_return']:.2f}% return")
        
        return results
