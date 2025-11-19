"""
Backtesting Engine
Tests trading strategy on historical data and generates performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
import matplotlib.pyplot as plt
import seaborn as sns
import os

from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager
from config import Config


class BacktestEngine:
    """Backtesting engine for trading strategies"""
    
    def __init__(
        self,
        initial_capital: float = None,
        commission: float = 0.001,  # 0.1% commission
        slippage: float = 0.0005  # 0.05% slippage
    ):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as fraction)
            slippage: Slippage per trade (as fraction)
        """
        self.initial_capital = initial_capital or Config.CAPITAL
        self.commission = commission
        self.slippage = slippage
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager(self.initial_capital)
        
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
        
    def run_backtest(
        self,
        df: pd.DataFrame,
        symbol: str = "STOCK"
    ) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data and indicators
            symbol: Stock symbol
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest for {symbol} with {len(df)} data points")
        
        # Reset state
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.dates = [df.index[0]]
        
        capital = self.initial_capital
        position = None
        
        # Calculate signals
        df = self.strategy.calculate_signals(df)
        
        for i in range(len(df)):
            current_date = df.index[i]
            current_data = df.iloc[i]
            
            # Update existing position
            if position:
                should_exit, exit_reason, exit_price = self.strategy.check_exit_conditions(
                    df, position['entry_price'], position['entry_index'], i
                )
                
                if should_exit:
                    # Close position
                    exit_price_with_slippage = exit_price * (1 - self.slippage) if position['type'] == 'LONG' else exit_price * (1 + self.slippage)
                    
                    if position['type'] == 'LONG':
                        pnl = (exit_price_with_slippage - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - exit_price_with_slippage) * position['quantity']
                    
                    # Apply commission
                    commission_cost = (position['entry_price'] + exit_price_with_slippage) * position['quantity'] * self.commission
                    pnl -= commission_cost
                    
                    capital += pnl
                    
                    # Record trade
                    trade = {
                        'symbol': symbol,
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price_with_slippage,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return_pct': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                        'exit_reason': exit_reason,
                        'holding_period': (current_date - position['entry_date']).days
                    }
                    self.trades.append(trade)
                    
                    logger.debug(
                        f"Exit: {symbol} @ {exit_price_with_slippage:.2f}, "
                        f"PnL: {pnl:.2f}, Reason: {exit_reason}"
                    )
                    
                    position = None
            
            # Check for new entry signal
            if not position and current_data['Signal'] == 1:
                entry_price = current_data['Entry_Price']
                stop_loss = current_data['Stop_Loss']
                
                # Calculate position size
                signal_strength = self.strategy.get_signal_strength(df, i)
                quantity = self.risk_manager.calculate_position_size(
                    entry_price, stop_loss, signal_strength
                )
                
                if quantity > 0:
                    # Apply slippage
                    entry_price_with_slippage = entry_price * (1 + self.slippage)
                    
                    # Check if we have enough capital
                    position_value = entry_price_with_slippage * quantity
                    if position_value <= capital:
                        position = {
                            'symbol': symbol,
                            'entry_date': current_date,
                            'entry_price': entry_price_with_slippage,
                            'stop_loss': stop_loss,
                            'quantity': quantity,
                            'type': 'LONG',
                            'entry_index': i
                        }
                        
                        capital -= position_value
                        
                        logger.debug(
                            f"Entry: {symbol} @ {entry_price_with_slippage:.2f}, "
                            f"Qty: {quantity}, Capital: {capital:.2f}"
                        )
            
            # Update equity curve
            if position:
                current_price = current_data['Close']
                position_value = current_price * position['quantity']
                total_equity = capital + position_value
            else:
                total_equity = capital
            
            self.equity_curve.append(total_equity)
            self.dates.append(current_date)
        
        # Close any open position at the end
        if position:
            final_price = df.iloc[-1]['Close']
            final_price_with_slippage = final_price * (1 - self.slippage)
            
            pnl = (final_price_with_slippage - position['entry_price']) * position['quantity']
            commission_cost = (position['entry_price'] + final_price_with_slippage) * position['quantity'] * self.commission
            pnl -= commission_cost
            
            capital += pnl
            
            trade = {
                'symbol': symbol,
                'entry_date': position['entry_date'],
                'exit_date': df.index[-1],
                'entry_price': position['entry_price'],
                'exit_price': final_price_with_slippage,
                'quantity': position['quantity'],
                'pnl': pnl,
                'return_pct': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                'exit_reason': 'End of Data',
                'holding_period': (df.index[-1] - position['entry_date']).days
            }
            self.trades.append(trade)
        
        # Calculate performance metrics
        results = self._calculate_metrics(capital, df.index[0], df.index[-1])
        
        logger.info(f"Backtest completed: {len(self.trades)} trades, Final Capital: {capital:.2f}")
        
        return results
    
    def _calculate_metrics(
        self,
        final_capital: float,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Calculate performance metrics
        
        Args:
            final_capital: Final capital after backtest
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'cagr': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_return': 0,
                'final_capital': final_capital
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Returns
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        # CAGR
        years = (end_date - start_date).days / 365.25
        if years > 0:
            cagr = (((final_capital / self.initial_capital) ** (1 / years)) - 1) * 100
        else:
            cagr = 0
        
        # Sharpe Ratio (assuming risk-free rate of 6%)
        risk_free_rate = 0.06
        equity_series = pd.Series(self.equity_curve)
        returns = equity_series.pct_change().dropna()
        
        if len(returns) > 0 and returns.std() > 0:
            excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
            sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Max Drawdown
        equity_series = pd.Series(self.equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100
        
        # Average trade metrics
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if total_trades > winning_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'cagr': cagr,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_capital': final_capital,
            'initial_capital': self.initial_capital,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'start_date': start_date,
            'end_date': end_date,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'dates': self.dates
        }
        
        return results
    
    def plot_results(
        self,
        results: Dict,
        symbol: str = "STOCK",
        save_path: str = None
    ):
        """
        Plot backtest results
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            save_path: Path to save plots
        """
        if save_path:
            os.makedirs(save_path, exist_ok=True)
        
        # Create figure with subplots
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Equity Curve
        axes[0].plot(results['dates'], results['equity_curve'], label='Equity Curve', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        axes[0].set_title(f'Equity Curve - {symbol}', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Date')
        axes[0].set_ylabel('Capital (INR)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Drawdown
        equity_series = pd.Series(results['equity_curve'])
        running_max = equity_series.expanding().max()
        drawdown = ((equity_series - running_max) / running_max) * 100
        
        axes[1].fill_between(results['dates'], drawdown, 0, alpha=0.3, color='red', label='Drawdown')
        axes[1].set_title('Drawdown', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Date')
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Trade P&L Distribution
        if results['total_trades'] > 0:
            trades_df = pd.DataFrame(results['trades'])
            axes[2].bar(range(len(trades_df)), trades_df['pnl'], 
                       color=['green' if x > 0 else 'red' for x in trades_df['pnl']])
            axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[2].set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
            axes[2].set_xlabel('Trade Number')
            axes[2].set_ylabel('P&L (INR)')
            axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(os.path.join(save_path, f'{symbol}_backtest_results.png'), dpi=300, bbox_inches='tight')
            logger.info(f"Plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_report(
        self,
        results: Dict,
        symbol: str = "STOCK",
        save_path: str = None
    ) -> str:
        """
        Generate text report of backtest results
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            save_path: Path to save report
            
        Returns:
            Report as string
        """
        report = f"""
{'='*60}
BACKTEST REPORT: {symbol}
{'='*60}

PERIOD: {results['start_date'].date()} to {results['end_date'].date()}

CAPITAL METRICS:
  Initial Capital:     INR {results['initial_capital']:,.2f}
  Final Capital:       INR {results['final_capital']:,.2f}
  Total Return:        {results['total_return']:.2f}%
  CAGR:                {results['cagr']:.2f}%

RISK METRICS:
  Max Drawdown:        {results['max_drawdown']:.2f}%
  Sharpe Ratio:        {results['sharpe_ratio']:.2f}

TRADE STATISTICS:
  Total Trades:        {results['total_trades']}
  Winning Trades:      {results['winning_trades']}
  Losing Trades:       {results['losing_trades']}
  Win Rate:            {results['win_rate']:.2f}%
  Average Win:         INR {results['avg_win']:,.2f}
  Average Loss:        INR {results['avg_loss']:,.2f}
  Profit Factor:       {results['profit_factor']:.2f}

{'='*60}
"""
        
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            report_file = os.path.join(save_path, f'{symbol}_backtest_report.txt')
            with open(report_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {report_file}")
        
        return report
