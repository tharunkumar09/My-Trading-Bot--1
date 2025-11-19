"""
Example: Running live trading bot
"""

from src.trading_bot import TradingBot
from config import Config
from loguru import logger

def main():
    # Initialize bot
    bot = TradingBot(api_provider="upstox")
    
    # Add symbols to watchlist
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    bot.add_to_watchlist(symbols)
    
    # Get initial status
    status = bot.get_status()
    logger.info(f"Bot Status: {status}")
    
    # Start bot (checks every 5 minutes)
    try:
        logger.info("Starting trading bot...")
        bot.start(interval_minutes=5)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        bot.stop()

if __name__ == "__main__":
    main()
