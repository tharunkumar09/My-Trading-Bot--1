"""
Main Trading Bot
Orchestrates strategy, risk management, and order execution
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, time
from loguru import logger
import time as time_module
import schedule

from config import Config
from src.api.upstox_client import UpstoxClient
from src.api.angel_one_client import AngelOneClient
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager
from src.order.order_manager import OrderManager, OrderType
from src.data.data_fetcher import DataFetcher


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self, api_provider: str = "upstox"):
        """
        Initialize trading bot
        
        Args:
            api_provider: API provider ("upstox" or "angel_one")
        """
        self.api_provider = api_provider
        
        # Initialize API client
        if api_provider == "upstox":
            self.api_client = UpstoxClient()
        elif api_provider == "angel_one":
            self.api_client = AngelOneClient()
            if not self.api_client.authenticate():
                raise Exception("Failed to authenticate with Angel One")
        else:
            raise ValueError(f"Unknown API provider: {api_provider}")
        
        # Initialize components
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager(self.api_client)
        self.data_fetcher = DataFetcher()
        
        # Trading state
        self.watchlist: List[str] = []
        self.is_running = False
        
        # Setup logging
        logger.add(
            Config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level=Config.LOG_LEVEL
        )
    
    def add_to_watchlist(self, symbols: List[str]):
        """
        Add symbols to watchlist
        
        Args:
            symbols: List of stock symbols
        """
        self.watchlist.extend(symbols)
        logger.info(f"Added {len(symbols)} symbols to watchlist")
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now().time()
        market_start = time.fromisoformat(Config.MARKET_START_TIME)
        market_end = time.fromisoformat(Config.MARKET_END_TIME)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if datetime.now().weekday() >= 5:  # Saturday or Sunday
            return False
        
        return market_start <= now <= market_end
    
    def fetch_live_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch live market data for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            DataFrame with recent OHLCV data
        """
        try:
            # Get instrument key (this would need to be mapped from symbol)
            # For now, using a placeholder approach
            instrument_key = self._get_instrument_key(symbol)
            
            if not instrument_key:
                logger.warning(f"Could not find instrument key for {symbol}")
                return None
            
            # Fetch recent historical data (last 200 candles for indicators)
            end_date = datetime.now()
            start_date = datetime.now() - pd.Timedelta(days=365)  # Get 1 year of data
            
            if isinstance(self.api_client, UpstoxClient):
                candles = self.api_client.get_historical_data(
                    instrument_key=instrument_key,
                    interval="day",
                    from_date=start_date.strftime("%Y-%m-%d"),
                    to_date=end_date.strftime("%Y-%m-%d")
                )
                
                if not candles:
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                
                return df
            else:
                # For Angel One, use data fetcher
                df = self.data_fetcher.fetch_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    source='yahoo'
                )
                return df
                
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {str(e)}")
            return None
    
    def _get_instrument_key(self, symbol: str) -> Optional[str]:
        """
        Get instrument key for a symbol
        This is a placeholder - in production, you'd maintain a mapping
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Instrument key or None
        """
        # This would typically involve querying the API for instrument master
        # For now, return None and let the data fetcher handle it
        return None
    
    def process_symbol(self, symbol: str):
        """
        Process a single symbol: fetch data, calculate signals, execute trades
        
        Args:
            symbol: Stock symbol
        """
        try:
            # Fetch live data
            df = self.fetch_live_data(symbol)
            
            if df is None or len(df) < 200:
                logger.warning(f"Insufficient data for {symbol}")
                return
            
            # Calculate indicators and signals
            df = self.strategy.calculate_signals(df)
            
            if len(df) == 0:
                return
            
            current_data = df.iloc[-1]
            
            # Check for entry signals
            if current_data['Signal'] == 1:
                if self.risk_manager.can_open_position():
                    entry_price = current_data['Entry_Price']
                    stop_loss = current_data['Stop_Loss']
                    
                    # Calculate position size
                    signal_strength = self.strategy.get_signal_strength(df, len(df) - 1)
                    quantity = self.risk_manager.calculate_position_size(
                        entry_price, stop_loss, signal_strength
                    )
                    
                    if quantity > 0:
                        # Place order
                        instrument_key = self._get_instrument_key(symbol)
                        if instrument_key:
                            order_id = self.order_manager.place_order(
                                symbol=symbol,
                                instrument_key=instrument_key,
                                quantity=quantity,
                                order_type=OrderType.MARKET,
                                transaction_type="BUY",
                                price=None,
                                stop_loss=stop_loss
                            )
                            
                            logger.info(
                                f"BUY signal for {symbol}: "
                                f"{quantity} shares @ {entry_price:.2f}, "
                                f"SL: {stop_loss:.2f}"
                            )
            
            # Check existing positions for exit signals
            open_positions = self.risk_manager.get_open_positions()
            for position in open_positions:
                if position['symbol'] == symbol:
                    # Get current price
                    current_price = current_data['Close']
                    highest_price = df['High'].iloc[-50:].max()  # Last 50 periods
                    
                    # Update position
                    updated_position = self.risk_manager.update_position(
                        position['id'],
                        current_price,
                        highest_price
                    )
                    
                    if updated_position and updated_position.get('should_exit'):
                        # Place exit order
                        instrument_key = self._get_instrument_key(symbol)
                        if instrument_key:
                            order_id = self.order_manager.place_order(
                                symbol=symbol,
                                instrument_key=instrument_key,
                                quantity=position['quantity'],
                                order_type=OrderType.MARKET,
                                transaction_type="SELL",
                                price=None
                            )
                            
                            logger.info(
                                f"SELL signal for {symbol}: "
                                f"{position['quantity']} shares @ {current_price:.2f}, "
                                f"Reason: {updated_position['exit_reason']}"
                            )
                            
                            # Remove position
                            self.risk_manager.remove_position(position['id'])
        
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
    
    def run_iteration(self):
        """Run one iteration of the trading bot"""
        if not self.is_market_open():
            logger.debug("Market is closed")
            return
        
        logger.info("Starting trading iteration")
        
        # Process each symbol in watchlist
        for symbol in self.watchlist:
            try:
                self.process_symbol(symbol)
                # Small delay to avoid rate limiting
                time_module.sleep(1)
            except Exception as e:
                logger.error(f"Error in iteration for {symbol}: {str(e)}")
        
        logger.info("Trading iteration completed")
    
    def start(self, interval_minutes: int = 5):
        """
        Start the trading bot
        
        Args:
            interval_minutes: Minutes between iterations
        """
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        self.is_running = True
        logger.info(f"Starting trading bot (checking every {interval_minutes} minutes)")
        
        # Schedule trading iterations
        schedule.every(interval_minutes).minutes.do(self.run_iteration)
        
        # Run until stopped
        try:
            while self.is_running:
                schedule.run_pending()
                time_module.sleep(1)
        except KeyboardInterrupt:
            logger.info("Trading bot stopped by user")
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("Trading bot stopped")
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'market_open': self.is_market_open(),
            'watchlist_size': len(self.watchlist),
            'open_positions': len(self.risk_manager.get_open_positions()),
            'total_exposure': self.risk_manager.get_total_exposure(),
            'total_unrealized_pnl': self.risk_manager.get_total_unrealized_pnl(),
            'pending_orders': len(self.order_manager.get_pending_orders())
        }
