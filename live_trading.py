"""
Live Trading Bot Script
Run the trading bot for live market trading
"""

import argparse
from loguru import logger
import os

from config import Config
from src.trading_bot import TradingBot


def main():
    parser = argparse.ArgumentParser(description='Run live trading bot')
    parser.add_argument('--provider', type=str, choices=['upstox', 'angel_one'],
                       default='upstox', help='API provider')
    parser.add_argument('--symbols', type=str, nargs='+',
                       help='Stock symbols to trade', default=['RELIANCE', 'TCS', 'INFY'])
    parser.add_argument('--interval', type=int, default=5,
                       help='Minutes between trading iterations')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no actual orders)')
    
    args = parser.parse_args()
    
    # Setup logging
    os.makedirs('logs', exist_ok=True)
    logger.add(Config.LOG_FILE, rotation="1 day", retention="30 days", level=Config.LOG_LEVEL)
    
    logger.info("="*60)
    logger.info("STARTING LIVE TRADING BOT")
    logger.info("="*60)
    logger.info(f"API Provider: {args.provider}")
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Check Interval: {args.interval} minutes")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("="*60)
    
    try:
        # Initialize trading bot
        bot = TradingBot(api_provider=args.provider)
        
        # Add symbols to watchlist
        bot.add_to_watchlist(args.symbols)
        
        # Get initial status
        status = bot.get_status()
        logger.info(f"Initial Status: {status}")
        
        if args.dry_run:
            logger.warning("DRY RUN MODE: No actual orders will be placed")
        
        # Start bot
        logger.info("Starting trading bot...")
        bot.start(interval_minutes=args.interval)
        
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user")
    except Exception as e:
        logger.error(f"Error running trading bot: {str(e)}")
        raise


if __name__ == "__main__":
    main()
