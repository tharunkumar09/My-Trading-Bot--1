"""
Script to run backtests on historical data.
"""
import sys
from pathlib import Path
from utils.logger import get_logger
from utils.market_data import MarketDataFetcher
from backtesting.backtest_engine import BacktestEngine
from config.config import BACKTEST_START_DATE, BACKTEST_END_DATE

logger = get_logger(__name__)


def main():
    """Run backtest on historical data."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtest on historical data')
    parser.add_argument('--symbol', type=str, default='RELIANCE', help='Stock symbol (e.g., RELIANCE)')
    parser.add_argument('--start', type=str, default=BACKTEST_START_DATE, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=BACKTEST_END_DATE, help='End date (YYYY-MM-DD)')
    parser.add_argument('--source', type=str, default='yfinance', choices=['yfinance', 'nsepy'], 
                       help='Data source')
    parser.add_argument('--capital', type=float, default=100000, help='Initial capital')
    parser.add_argument('--output', type=str, default='backtesting/backtest_results.png', 
                       help='Output file for results plot')
    
    args = parser.parse_args()
    
    logger.info(f"Starting backtest for {args.symbol}")
    logger.info(f"Period: {args.start} to {args.end}")
    logger.info(f"Initial Capital: ₹{args.capital:,.2f}")
    
    # Fetch historical data
    data_fetcher = MarketDataFetcher()
    
    logger.info("Downloading historical data...")
    data = data_fetcher.download_historical_data(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        source=args.source
    )
    
    if data is None or data.empty:
        logger.error("Failed to fetch historical data")
        sys.exit(1)
    
    logger.info(f"Downloaded {len(data)} records")
    
    # Run backtest
    engine = BacktestEngine(initial_capital=args.capital)
    results = engine.run_backtest(data, start_date=args.start, end_date=args.end)
    
    if not results:
        logger.error("Backtest failed")
        sys.exit(1)
    
    # Print summary
    engine.print_summary(results)
    
    # Plot results
    engine.plot_results(results, save_path=args.output)
    
    logger.info("Backtest completed successfully")


if __name__ == "__main__":
    main()
