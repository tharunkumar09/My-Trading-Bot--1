"""
Script to download historical data for backtesting.
"""
import sys
from pathlib import Path
from utils.logger import get_logger
from utils.market_data import MarketDataFetcher
from config.config import BACKTEST_START_DATE, BACKTEST_END_DATE

logger = get_logger(__name__)


def main():
    """Download historical data."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download historical market data')
    parser.add_argument('--symbol', type=str, required=True, help='Stock symbol (e.g., RELIANCE)')
    parser.add_argument('--start', type=str, default=BACKTEST_START_DATE, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=BACKTEST_END_DATE, help='End date (YYYY-MM-DD)')
    parser.add_argument('--source', type=str, default='yfinance', choices=['yfinance', 'nsepy'], 
                       help='Data source')
    parser.add_argument('--output', type=str, default=None, 
                       help='Output CSV file (default: data/{symbol}_historical.csv)')
    
    args = parser.parse_args()
    
    # Determine output file
    if args.output is None:
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        args.output = output_dir / f"{args.symbol}_historical.csv"
    
    logger.info(f"Downloading historical data for {args.symbol}")
    logger.info(f"Period: {args.start} to {args.end}")
    logger.info(f"Source: {args.source}")
    
    # Fetch data
    data_fetcher = MarketDataFetcher()
    data = data_fetcher.download_historical_data(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        source=args.source
    )
    
    if data is None or data.empty:
        logger.error("Failed to download data")
        sys.exit(1)
    
    # Save to CSV
    data.to_csv(args.output, index=False)
    logger.info(f"Data saved to {args.output}")
    logger.info(f"Total records: {len(data)}")
    logger.info(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")


if __name__ == "__main__":
    main()
