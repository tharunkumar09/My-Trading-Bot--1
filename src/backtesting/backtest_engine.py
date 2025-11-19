"""
Backtesting Engine
Comprehensive backtesting system with performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine for strategy evaluation
    """
    
    def __init__(self, initial_capital: float = 1000000, commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as fraction)
            slippage: Slippage per trade (as fraction)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        self.positions = []
        
        logger.info(f"Backtest engine initialized with capital: ₹{initial_capital:,.2f}")
    
    def run_backtest(self, data: pd.DataFrame, signals: pd.DataFrame,
                    stop_loss_pct: float = 0.02, take_profit_pct: float = 0.04,
                    max_positions: int = 1) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV data
            signals: DataFrame with trading signals
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            max_positions: Maximum concurrent positions
            
        Returns:
            Dictionary with backtest results
        """
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [capital]
        daily_returns = []
        
        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            current_signal = signals['signal'].iloc[i] if i < len(signals) else 0
            
            # Update equity curve
            if position:
                position_value = position['quantity'] * current_price
                total_equity = capital + position_value - (position['quantity'] * position['entry_price'])
            else:
                total_equity = capital
            
            equity_curve.append(total_equity)
            
            # Calculate daily return
            if len(equity_curve) > 1:
                daily_return = (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2]
                daily_returns.append(daily_return)
            
            # Check exit conditions for open position
            if position:
                should_exit = False
                exit_reason = ""
                
                # Check stop loss
                if current_price <= position['stop_loss']:
                    should_exit = True
                    exit_reason = "stop_loss"
                    exit_price = position['stop_loss']
                
                # Check take profit
                elif current_price >= position['take_profit']:
                    should_exit = True
                    exit_reason = "take_profit"
                    exit_price = position['take_profit']
                
                # Check strategy signal
                elif current_signal == -1:
                    should_exit = True
                    exit_reason = "signal"
                    exit_price = current_price * (1 - self.slippage)
                
                # Execute exit
                if should_exit:
                    # Calculate P&L
                    exit_price_adj = exit_price * (1 - self.commission)
                    pnl = (exit_price_adj - position['entry_price']) * position['quantity']
                    capital += pnl + (position['quantity'] * position['entry_price'])
                    
                    # Record trade
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return_pct': (pnl / position['entry_value']) * 100,
                        'exit_reason': exit_reason,
                        'days_held': (current_date - position['entry_date']).days
                    })
                    
                    position = None
            
            # Check entry conditions
            elif current_signal == 1 and not position:
                # Calculate position size (for simplicity, use 95% of capital)
                position_value = capital * 0.95
                quantity = int(position_value / current_price)
                
                if quantity > 0:
                    entry_price = current_price * (1 + self.slippage + self.commission)
                    entry_value = quantity * entry_price
                    
                    # Calculate stop loss and take profit
                    stop_loss = current_price * (1 - stop_loss_pct)
                    take_profit = current_price * (1 + take_profit_pct)
                    
                    position = {
                        'entry_date': current_date,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'entry_value': entry_value,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
                    
                    capital -= entry_value
        
        # Close any open position at end
        if position:
            final_price = data['close'].iloc[-1] * (1 - self.commission - self.slippage)
            pnl = (final_price - position['entry_price']) * position['quantity']
            capital += pnl + (position['quantity'] * position['entry_price'])
            
            trades.append({
                'entry_date': position['entry_date'],
                'exit_date': data.index[-1],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'return_pct': (pnl / position['entry_value']) * 100,
                'exit_reason': 'end_of_data',
                'days_held': (data.index[-1] - position['entry_date']).days
            })
        
        # Calculate performance metrics
        results = self._calculate_metrics(
            trades, equity_curve, daily_returns, data.index[0], data.index[-1]
        )
        
        self.trades = trades
        self.equity_curve = equity_curve
        
        logger.info(f"Backtest completed: {results['total_trades']} trades, {results['total_return_pct']:.2f}% return")
        
        return results
    
    def _calculate_metrics(self, trades: List[Dict], equity_curve: List[float],
                          daily_returns: List[float], start_date, end_date) -> Dict:
        """
        Calculate performance metrics
        
        Args:
            trades: List of trade dictionaries
            equity_curve: List of equity values
            daily_returns: List of daily returns
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dictionary with performance metrics
        """
        if len(trades) == 0:
            return {
                'initial_capital': self.initial_capital,
                'final_capital': self.initial_capital,
                'total_return_pct': 0,
                'cagr': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown_pct': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'avg_trade_pnl': 0,
                'avg_trade_return_pct': 0,
                'avg_days_held': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }
        
        trades_df = pd.DataFrame(trades)
        final_capital = equity_curve[-1]
        
        # Basic returns
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # CAGR
        years = (end_date - start_date).days / 365.25
        cagr = (((final_capital / self.initial_capital) ** (1 / years)) - 1) * 100 if years > 0 else 0
        
        # Sharpe Ratio (assuming risk-free rate of 6%)
        if len(daily_returns) > 0:
            daily_rf_rate = 0.06 / 252
            excess_returns = np.array(daily_returns) - daily_rf_rate
            sharpe_ratio = np.sqrt(252) * (np.mean(excess_returns) / np.std(excess_returns)) if np.std(excess_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sortino Ratio
        if len(daily_returns) > 0:
            negative_returns = [r for r in daily_returns if r < 0]
            downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 0
            sortino_ratio = np.sqrt(252) * (np.mean(excess_returns) / downside_std) if downside_std > 0 else 0
        else:
            sortino_ratio = 0
        
        # Maximum Drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown_pct = abs(drawdown.min()) * 100
        
        # Trade statistics
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        total_trades = len(trades_df)
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0
        profit_factor = (winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else float('inf')
        
        avg_trade_pnl = trades_df['pnl'].mean()
        avg_trade_return_pct = trades_df['return_pct'].mean()
        avg_days_held = trades_df['days_held'].mean()
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for pnl in trades_df['pnl']:
            if pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'cagr': cagr,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': total_trades,
            'winning_trades': num_wins,
            'losing_trades': num_losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_trade_pnl': avg_trade_pnl,
            'avg_trade_return_pct': avg_trade_return_pct,
            'avg_days_held': avg_days_held,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'start_date': start_date,
            'end_date': end_date,
            'years': years
        }
    
    def plot_results(self, save_path: str = None):
        """
        Plot backtest results
        
        Args:
            save_path: Path to save figure (optional)
        """
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('Backtest Results', fontsize=16, fontweight='bold')
        
        # 1. Equity Curve
        axes[0, 0].plot(self.equity_curve, linewidth=2)
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Portfolio Value (₹)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        axes[0, 0].legend()
        
        # 2. Drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = ((equity_array - running_max) / running_max) * 100
        
        axes[0, 1].fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color='red')
        axes[0, 1].plot(drawdown, color='red', linewidth=1)
        axes[0, 1].set_title('Drawdown (%)')
        axes[0, 1].set_xlabel('Time')
        axes[0, 1].set_ylabel('Drawdown (%)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Trade P&L Distribution
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            axes[1, 0].hist(trades_df['pnl'], bins=30, alpha=0.7, edgecolor='black')
            axes[1, 0].axvline(x=0, color='r', linestyle='--')
            axes[1, 0].set_title('Trade P&L Distribution')
            axes[1, 0].set_xlabel('P&L (₹)')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Cumulative P&L
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            cumulative_pnl = trades_df['pnl'].cumsum()
            axes[1, 1].plot(cumulative_pnl, linewidth=2, color='green')
            axes[1, 1].set_title('Cumulative P&L')
            axes[1, 1].set_xlabel('Trade Number')
            axes[1, 1].set_ylabel('Cumulative P&L (₹)')
            axes[1, 1].grid(True, alpha=0.3)
        
        # 5. Win/Loss Distribution
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            wins = len(trades_df[trades_df['pnl'] > 0])
            losses = len(trades_df[trades_df['pnl'] <= 0])
            axes[2, 0].bar(['Wins', 'Losses'], [wins, losses], color=['green', 'red'], alpha=0.7)
            axes[2, 0].set_title('Win/Loss Distribution')
            axes[2, 0].set_ylabel('Number of Trades')
            axes[2, 0].grid(True, alpha=0.3, axis='y')
        
        # 6. Monthly Returns Heatmap (if enough data)
        if self.trades:
            axes[2, 1].text(0.5, 0.5, 'Trade Statistics', 
                          ha='center', va='center', fontsize=12, fontweight='bold')
            axes[2, 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plot saved to {save_path}")
        
        plt.show()
    
    def export_results(self, results: Dict, output_dir: str):
        """
        Export backtest results to files
        
        Args:
            results: Results dictionary
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Export metrics to text file
        metrics_file = output_path / 'backtest_metrics.txt'
        with open(metrics_file, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("BACKTEST RESULTS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Period: {results['start_date']} to {results['end_date']}\n")
            f.write(f"Duration: {results['years']:.2f} years\n\n")
            
            f.write("RETURNS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Initial Capital: ₹{results['initial_capital']:,.2f}\n")
            f.write(f"Final Capital: ₹{results['final_capital']:,.2f}\n")
            f.write(f"Total Return: ₹{results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)\n")
            f.write(f"CAGR: {results['cagr']:.2f}%\n\n")
            
            f.write("RISK METRICS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}\n")
            f.write(f"Sortino Ratio: {results['sortino_ratio']:.2f}\n")
            f.write(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%\n\n")
            
            f.write("TRADE STATISTICS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total Trades: {results['total_trades']}\n")
            f.write(f"Winning Trades: {results['winning_trades']}\n")
            f.write(f"Losing Trades: {results['losing_trades']}\n")
            f.write(f"Win Rate: {results['win_rate']:.2f}%\n")
            f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
            f.write(f"Average Win: ₹{results['avg_win']:,.2f}\n")
            f.write(f"Average Loss: ₹{results['avg_loss']:,.2f}\n")
            f.write(f"Average Trade P&L: ₹{results['avg_trade_pnl']:,.2f}\n")
            f.write(f"Average Trade Return: {results['avg_trade_return_pct']:.2f}%\n")
            f.write(f"Average Days Held: {results['avg_days_held']:.1f}\n")
            f.write(f"Max Consecutive Wins: {results['max_consecutive_wins']}\n")
            f.write(f"Max Consecutive Losses: {results['max_consecutive_losses']}\n")
        
        logger.info(f"Metrics exported to {metrics_file}")
        
        # Export trades to CSV
        if self.trades:
            trades_file = output_path / 'trades.csv'
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(trades_file, index=False)
            logger.info(f"Trades exported to {trades_file}")
        
        # Export equity curve
        equity_file = output_path / 'equity_curve.csv'
        equity_df = pd.DataFrame({'equity': self.equity_curve})
        equity_df.to_csv(equity_file, index=False)
        logger.info(f"Equity curve exported to {equity_file}")
