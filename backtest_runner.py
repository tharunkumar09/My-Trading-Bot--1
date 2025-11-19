"""
Backtest Runner
Script to run backtests on historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path
import argparse

from src.utils.config_loader import get_config
from src.utils.data_fetcher import DataFetcher
from src.utils.logger import get_logger
from src.strategies.momentum_strategy import MomentumStrategy
from src.backtesting.backtest_engine import BacktestEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest(symbol: str, years: int = 20, plot: bool = True, export: bool = True):
    """
    Run backtest for a single symbol
    
    Args:
        symbol: Stock symbol
        years: Years of historical data
        plot: Whether to plot results
        export: Whether to export results
    """
    logger.info("=" * 70)
    logger.info(f"BACKTESTING: {symbol}")
    logger.info("=" * 70)
    
    # Load configuration
    config = get_config()
    backtest_config = config.get_backtest_config()
    strategy_config = config.get_strategy_config()
    
    # Fetch historical data
    logger.info(f"Fetching {years} years of data for {symbol}...")
    fetcher = DataFetcher()
    
    start_date = backtest_config.get('start_date', '2003-01-01')
    end_date = backtest_config.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    df = fetcher.fetch_historical_data_yahoo(symbol, start_date, end_date)
    
    if df.empty:
        logger.error(f"No data available for {symbol}")
        return None
    
    logger.info(f"Loaded {len(df)} rows from {df.index[0]} to {df.index[-1]}")
    
    # Initialize strategy
    strategy = MomentumStrategy(strategy_config)
    
    # Generate signals
    logger.info("Calculating indicators and generating signals...")
    df = strategy.generate_signals(df)
    
    # Initialize backtest engine
    initial_capital = backtest_config.get('initial_capital', 1000000)
    commission = backtest_config.get('commission', 0.001)
    slippage = backtest_config.get('slippage', 0.0005)
    
    engine = BacktestEngine(initial_capital, commission, slippage)
    
    # Run backtest
    logger.info("Running backtest...")
    results = engine.run_backtest(df, df)
    
    # Print results
    print("\n" + "=" * 70)
    print(f"BACKTEST RESULTS: {symbol}")
    print("=" * 70)
    print(f"Period: {results['start_date']} to {results['end_date']} ({results['years']:.2f} years)")
    print("-" * 70)
    print("\nRETURNS:")
    print(f"  Initial Capital:     ₹{results['initial_capital']:>15,.2f}")
    print(f"  Final Capital:       ₹{results['final_capital']:>15,.2f}")
    print(f"  Total Return:        ₹{results['total_return']:>15,.2f} ({results['total_return_pct']:>6.2f}%)")
    print(f"  CAGR:                 {results['cagr']:>6.2f}%")
    print("\nRISK METRICS:")
    print(f"  Sharpe Ratio:         {results['sharpe_ratio']:>6.2f}")
    print(f"  Sortino Ratio:        {results['sortino_ratio']:>6.2f}")
    print(f"  Max Drawdown:         {results['max_drawdown_pct']:>6.2f}%")
    print("\nTRADE STATISTICS:")
    print(f"  Total Trades:         {results['total_trades']:>6}")
    print(f"  Winning Trades:       {results['winning_trades']:>6}")
    print(f"  Losing Trades:        {results['losing_trades']:>6}")
    print(f"  Win Rate:             {results['win_rate']:>6.2f}%")
    print(f"  Profit Factor:        {results['profit_factor']:>6.2f}")
    print(f"  Avg Win:             ₹{results['avg_win']:>15,.2f}")
    print(f"  Avg Loss:            ₹{results['avg_loss']:>15,.2f}")
    print(f"  Avg Trade P&L:       ₹{results['avg_trade_pnl']:>15,.2f}")
    print(f"  Avg Trade Return:     {results['avg_trade_return_pct']:>6.2f}%")
    print(f"  Avg Days Held:        {results['avg_days_held']:>6.1f}")
    print(f"  Max Consecutive Wins: {results['max_consecutive_wins']:>6}")
    print(f"  Max Consecutive Loss: {results['max_consecutive_losses']:>6}")
    print("=" * 70 + "\n")
    
    # Export results
    if export:
        output_dir = f"data/backtest_results/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        engine.export_results(results, output_dir)
        logger.info(f"Results exported to {output_dir}")
    
    # Plot results
    if plot:
        plot_path = f"data/backtest_results/{symbol}_backtest.png" if export else None
        engine.plot_results(save_path=plot_path)
    
    return results


def run_multiple_backtests(symbols: list, years: int = 20):
    """
    Run backtests for multiple symbols
    
    Args:
        symbols: List of stock symbols
        years: Years of historical data
    """
    all_results = []
    
    for symbol in symbols:
        try:
            results = run_backtest(symbol, years, plot=False, export=False)
            if results:
                results['symbol'] = symbol
                all_results.append(results)
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {str(e)}")
            continue
    
    # Create summary
    if all_results:
        summary_df = pd.DataFrame(all_results)
        
        print("\n" + "=" * 100)
        print("BACKTEST SUMMARY - ALL STOCKS")
        print("=" * 100)
        
        print(f"\n{'Symbol':<15} {'CAGR %':<10} {'Sharpe':<10} {'MaxDD %':<10} {'Win %':<10} {'Trades':<10} {'Return %':<10}")
        print("-" * 100)
        
        for _, row in summary_df.iterrows():
            print(f"{row['symbol']:<15} {row['cagr']:<10.2f} {row['sharpe_ratio']:<10.2f} "
                  f"{row['max_drawdown_pct']:<10.2f} {row['win_rate']:<10.2f} "
                  f"{row['total_trades']:<10} {row['total_return_pct']:<10.2f}")
        
        print("-" * 100)
        print(f"{'AVERAGE':<15} {summary_df['cagr'].mean():<10.2f} {summary_df['sharpe_ratio'].mean():<10.2f} "
              f"{summary_df['max_drawdown_pct'].mean():<10.2f} {summary_df['win_rate'].mean():<10.2f} "
              f"{summary_df['total_trades'].mean():<10.0f} {summary_df['total_return_pct'].mean():<10.2f}")
        print("=" * 100 + "\n")
        
        # Export summary
        output_file = f"data/backtest_results/summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(output_file, index=False)
        logger.info(f"Summary exported to {output_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run backtests on historical data')
    parser.add_argument('--symbol', type=str, help='Stock symbol to backtest')
    parser.add_argument('--years', type=int, default=20, help='Years of historical data')
    parser.add_argument('--all', action='store_true', help='Backtest all stocks in config')
    parser.add_argument('--no-plot', action='store_true', help='Disable plotting')
    parser.add_argument('--no-export', action='store_true', help='Disable exporting')
    
    args = parser.parse_args()
    
    if args.all:
        # Backtest all stocks
        config = get_config()
        symbols = config.get('universe', {}).get('stocks', [])
        logger.info(f"Backtesting {len(symbols)} stocks...")
        run_multiple_backtests(symbols[:10], args.years)  # Limit to first 10 for demo
    
    elif args.symbol:
        # Backtest single symbol
        run_backtest(
            args.symbol,
            args.years,
            plot=not args.no_plot,
            export=not args.no_export
        )
    
    else:
        # Default: backtest RELIANCE
        logger.info("No symbol specified, backtesting RELIANCE...")
        run_backtest('RELIANCE', args.years, plot=not args.no_plot, export=not args.no_export)


if __name__ == "__main__":
    main()
