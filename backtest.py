"""
Backtesting Script
Run backtests on historical data and generate performance reports
"""

import argparse
from datetime import datetime, timedelta
from loguru import logger
import os

from config import Config
from src.data.data_fetcher import DataFetcher
from src.backtest.backtest_engine import BacktestEngine


def main():
    parser = argparse.ArgumentParser(description='Backtest trading strategy')
    parser.add_argument('--symbol', type=str, help='Stock symbol to backtest', default='RELIANCE')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)', 
                       default=(datetime.now() - timedelta(days=365*20)).strftime('%Y-%m-%d'))
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)',
                       default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--source', type=str, choices=['yahoo', 'nsepy'], default='yahoo',
                       help='Data source')
    parser.add_argument('--capital', type=float, default=Config.CAPITAL,
                       help='Initial capital')
    parser.add_argument('--nifty50', action='store_true',
                       help='Backtest on all NIFTY 50 stocks')
    
    args = parser.parse_args()
    
    # Setup logging
    logger.add("logs/backtest.log", rotation="1 day", retention="7 days")
    
    # Create results directory
    results_dir = Config.BACKTEST_RESULTS_PATH
    os.makedirs(results_dir, exist_ok=True)
    
    # Initialize components
    data_fetcher = DataFetcher()
    backtest_engine = BacktestEngine(initial_capital=args.capital)
    
    symbols_to_test = []
    
    if args.nifty50:
        logger.info("Fetching NIFTY 50 stocks...")
        symbols_to_test = data_fetcher.fetch_nifty50_stocks()
    else:
        symbols_to_test = [args.symbol]
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    logger.info(f"Starting backtest from {start_date.date()} to {end_date.date()}")
    logger.info(f"Testing {len(symbols_to_test)} symbols")
    
    all_results = []
    
    for symbol in symbols_to_test:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Backtesting {symbol}")
            logger.info(f"{'='*60}")
            
            # Fetch historical data
            df = data_fetcher.fetch_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                source=args.source
            )
            
            if df.empty:
                logger.warning(f"No data available for {symbol}")
                continue
            
            # Prepare data
            df = data_fetcher.prepare_data_for_backtest(df)
            
            if len(df) < 200:
                logger.warning(f"Insufficient data for {symbol} ({len(df)} records)")
                continue
            
            # Run backtest
            results = backtest_engine.run_backtest(df, symbol)
            
            # Generate report
            report = backtest_engine.generate_report(results, symbol, results_dir)
            logger.info(report)
            
            # Plot results
            backtest_engine.plot_results(results, symbol, results_dir)
            
            all_results.append({
                'symbol': symbol,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {str(e)}")
            continue
    
    # Generate summary report
    if all_results:
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY REPORT")
        logger.info(f"{'='*60}")
        
        summary_data = []
        for item in all_results:
            r = item['results']
            summary_data.append({
                'Symbol': item['symbol'],
                'Total Return (%)': r['total_return'],
                'CAGR (%)': r['cagr'],
                'Sharpe Ratio': r['sharpe_ratio'],
                'Max Drawdown (%)': r['max_drawdown'],
                'Win Rate (%)': r['win_rate'],
                'Total Trades': r['total_trades']
            })
        
        import pandas as pd
        summary_df = pd.DataFrame(summary_data)
        
        logger.info("\n" + summary_df.to_string(index=False))
        
        # Save summary
        summary_file = os.path.join(results_dir, 'backtest_summary.csv')
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"\nSummary saved to {summary_file}")
        
        # Calculate aggregate metrics
        avg_return = summary_df['Total Return (%)'].mean()
        avg_cagr = summary_df['CAGR (%)'].mean()
        avg_sharpe = summary_df['Sharpe Ratio'].mean()
        avg_drawdown = summary_df['Max Drawdown (%)'].mean()
        avg_win_rate = summary_df['Win Rate (%)'].mean()
        total_trades = summary_df['Total Trades'].sum()
        
        logger.info(f"\nAggregate Metrics:")
        logger.info(f"  Average Return: {avg_return:.2f}%")
        logger.info(f"  Average CAGR: {avg_cagr:.2f}%")
        logger.info(f"  Average Sharpe Ratio: {avg_sharpe:.2f}")
        logger.info(f"  Average Max Drawdown: {avg_drawdown:.2f}%")
        logger.info(f"  Average Win Rate: {avg_win_rate:.2f}%")
        logger.info(f"  Total Trades: {total_trades}")


if __name__ == "__main__":
    main()
