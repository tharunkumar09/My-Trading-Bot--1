"""
Backtesting engine for testing trading strategies on historical data.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from utils.logger import get_logger
from strategies.multi_indicator_strategy import MultiIndicatorStrategy
from utils.risk_manager import RiskManager
from config.config import INITIAL_CAPITAL, COMMISSION

logger = get_logger(__name__)


class BacktestEngine:
    """Backtest trading strategies on historical data."""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL, commission: float = COMMISSION):
        self.initial_capital = initial_capital
        self.commission = commission
        self.strategy = MultiIndicatorStrategy()
        self.risk_manager = RiskManager(initial_capital)
        
    def run_backtest(self, data: pd.DataFrame, start_date: str = None, end_date: str = None) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
        
        Returns:
            Dict with backtest results
        """
        logger.info("Starting backtest...")
        
        # Filter data by date range if provided
        if start_date:
            data = data[data['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data['timestamp'] <= pd.to_datetime(end_date)]
        
        if len(data) < 200:  # Need enough data for indicators
            logger.error("Insufficient data for backtest")
            return {}
        
        # Generate signals
        data_with_signals = self.strategy.generate_signals(data)
        
        # Run simulation
        results = self._simulate_trading(data_with_signals)
        
        # Calculate metrics
        metrics = self._calculate_metrics(results)
        
        logger.info(f"Backtest completed. Final equity: {metrics['final_equity']:.2f}")
        logger.info(f"CAGR: {metrics['cagr']:.2f}%")
        logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
        logger.info(f"Win Rate: {metrics['win_rate']:.2f}%")
        
        return {
            'results': results,
            'metrics': metrics,
            'data': data_with_signals
        }
    
    def _simulate_trading(self, data: pd.DataFrame) -> pd.DataFrame:
        """Simulate trading based on signals."""
        equity = self.initial_capital
        position = None  # {'type': 'long'/'short', 'entry_price': float, 'quantity': int, 'entry_index': int}
        trades = []
        equity_curve = []
        
        for i in range(len(data)):
            row = data.iloc[i]
            current_price = row['close']
            
            # Check for entry signal
            if row['signal'] == 1 and position is None:  # BUY signal
                # Calculate position size
                stop_loss = self.risk_manager.calculate_stop_loss(current_price, is_long=True)
                quantity = self.risk_manager.calculate_position_size(
                    current_price, stop_loss, equity
                )
                
                if quantity > 0:
                    position = {
                        'type': 'long',
                        'entry_price': current_price,
                        'quantity': quantity,
                        'entry_index': i,
                        'stop_loss': stop_loss
                    }
                    # Deduct commission
                    equity -= (current_price * quantity * self.commission)
            
            # Check for exit signal or stop loss
            elif position is not None:
                should_exit = False
                exit_reason = None
                
                # Exit on SELL signal
                if row['signal'] == -1:
                    should_exit = True
                    exit_reason = 'signal'
                
                # Exit on stop loss
                elif current_price <= position['stop_loss']:
                    should_exit = True
                    exit_reason = 'stop_loss'
                
                if should_exit:
                    # Calculate P&L
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    pnl -= (current_price * position['quantity'] * self.commission)  # Exit commission
                    
                    # Update equity
                    equity += pnl
                    
                    # Record trade
                    trade = {
                        'entry_date': data.iloc[position['entry_index']]['timestamp'],
                        'exit_date': row['timestamp'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'return_pct': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                        'exit_reason': exit_reason
                    }
                    trades.append(trade)
                    
                    position = None
            
            # Update equity curve
            if position:
                # Mark-to-market
                current_equity = equity + (current_price - position['entry_price']) * position['quantity']
            else:
                current_equity = equity
            
            equity_curve.append({
                'timestamp': row['timestamp'],
                'equity': current_equity,
                'price': current_price
            })
        
        # Close any open position at end
        if position:
            final_price = data.iloc[-1]['close']
            pnl = (final_price - position['entry_price']) * position['quantity']
            pnl -= (final_price * position['quantity'] * self.commission)
            equity += pnl
            
            trade = {
                'entry_date': data.iloc[position['entry_index']]['timestamp'],
                'exit_date': data.iloc[-1]['timestamp'],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'return_pct': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                'exit_reason': 'end_of_data'
            }
            trades.append(trade)
            
            equity_curve[-1]['equity'] = equity
        
        # Create results DataFrame
        results_df = pd.DataFrame(equity_curve)
        results_df['trades'] = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return {
            'equity_curve': results_df,
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'final_equity': equity
        }
    
    def _calculate_metrics(self, results: Dict) -> Dict:
        """Calculate backtest performance metrics."""
        equity_curve = results['equity_curve']
        trades = results['trades']
        final_equity = results['final_equity']
        
        if equity_curve.empty:
            return {}
        
        # Calculate returns
        equity_curve['returns'] = equity_curve['equity'].pct_change()
        equity_curve['cumulative_returns'] = (1 + equity_curve['returns']).cumprod() - 1
        
        # CAGR
        days = (equity_curve['timestamp'].iloc[-1] - equity_curve['timestamp'].iloc[0]).days
        years = days / 365.25
        if years > 0:
            total_return = (final_equity / self.initial_capital) - 1
            cagr = ((final_equity / self.initial_capital) ** (1 / years) - 1) * 100
        else:
            cagr = 0
        
        # Sharpe Ratio (annualized)
        if len(equity_curve['returns'].dropna()) > 0:
            returns_std = equity_curve['returns'].std()
            returns_mean = equity_curve['returns'].mean()
            if returns_std > 0:
                sharpe_ratio = (returns_mean / returns_std) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # Max Drawdown
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
        max_drawdown = equity_curve['drawdown'].min() * 100
        
        # Win Rate
        if not trades.empty and len(trades) > 0:
            winning_trades = trades[trades['pnl'] > 0]
            win_rate = (len(winning_trades) / len(trades)) * 100
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = trades[trades['pnl'] <= 0]['pnl'].mean() if len(trades[trades['pnl'] <= 0]) > 0 else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
        
        # Total return
        total_return = ((final_equity / self.initial_capital) - 1) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'cagr': cagr,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades) if not trades.empty else 0,
            'winning_trades': len(winning_trades) if not trades.empty else 0,
            'losing_trades': len(trades[trades['pnl'] <= 0]) if not trades.empty else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }
    
    def plot_results(self, results: Dict, save_path: str = "backtesting/backtest_results.png"):
        """Plot backtest results."""
        equity_curve = results['equity_curve']
        metrics = results['metrics']
        
        if equity_curve.empty:
            logger.warning("No data to plot")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Equity curve
        axes[0].plot(equity_curve['timestamp'], equity_curve['equity'], label='Equity', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        axes[0].set_title(f'Equity Curve\nCAGR: {metrics["cagr"]:.2f}% | Sharpe: {metrics["sharpe_ratio"]:.2f} | Max DD: {metrics["max_drawdown"]:.2f}%')
        axes[0].set_ylabel('Equity (₹)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Drawdown
        if 'drawdown' in equity_curve.columns:
            axes[1].fill_between(equity_curve['timestamp'], equity_curve['drawdown'] * 100, 0, 
                                color='red', alpha=0.3, label='Drawdown')
            axes[1].set_title('Drawdown')
            axes[1].set_ylabel('Drawdown (%)')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        
        # Returns distribution
        if 'returns' in equity_curve.columns:
            returns = equity_curve['returns'].dropna()
            axes[2].hist(returns, bins=50, alpha=0.7, edgecolor='black')
            axes[2].axvline(x=0, color='r', linestyle='--')
            axes[2].set_title('Returns Distribution')
            axes[2].set_xlabel('Daily Returns')
            axes[2].set_ylabel('Frequency')
            axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Backtest results saved to {save_path}")
        plt.close()
    
    def print_summary(self, results: Dict):
        """Print backtest summary."""
        metrics = results['metrics']
        trades = results['trades']
        
        print("\n" + "="*60)
        print("BACKTEST SUMMARY")
        print("="*60)
        print(f"Initial Capital:     ₹{metrics['initial_capital']:,.2f}")
        print(f"Final Equity:        ₹{metrics['final_equity']:,.2f}")
        print(f"Total Return:         {metrics['total_return']:.2f}%")
        print(f"CAGR:                {metrics['cagr']:.2f}%")
        print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:        {metrics['max_drawdown']:.2f}%")
        print(f"Win Rate:            {metrics['win_rate']:.2f}%")
        print(f"Total Trades:        {metrics['total_trades']}")
        print(f"Winning Trades:       {metrics['winning_trades']}")
        print(f"Losing Trades:       {metrics['losing_trades']}")
        print(f"Average Win:         ₹{metrics['avg_win']:,.2f}")
        print(f"Average Loss:        ₹{metrics['avg_loss']:,.2f}")
        print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
        print("="*60 + "\n")
        
        if not trades.empty and len(trades) > 0:
            print("\nTop 5 Winning Trades:")
            print(trades.nlargest(5, 'pnl')[['entry_date', 'exit_date', 'pnl', 'return_pct']].to_string())
            
            print("\nTop 5 Losing Trades:")
            print(trades.nsmallest(5, 'pnl')[['entry_date', 'exit_date', 'pnl', 'return_pct']].to_string())
