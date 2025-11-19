"""
Main trading bot that orchestrates all components.
"""
import time
import schedule
from datetime import datetime, time as dt_time
from typing import Optional
from utils.logger import get_logger
from utils.auth import get_auth_handler
from utils.market_data import MarketDataFetcher
from utils.order_manager import OrderManager
from utils.risk_manager import RiskManager
from utils.market_shock_detector import MarketShockDetector
from utils.trade_logger import TradeLogger
from strategies.multi_indicator_strategy import MultiIndicatorStrategy
from config.config import (
    TRADING_SYMBOL, EXCHANGE, MAX_POSITION_SIZE, INITIAL_CAPITAL,
    MARKET_OPEN, MARKET_CLOSE
)

logger = get_logger(__name__)


class TradingBot:
    """Main trading bot class."""
    
    def __init__(self):
        # Initialize components
        self.auth_handler = get_auth_handler()
        if not self.auth_handler:
            raise Exception("Failed to initialize authentication")
        
        self.market_data = MarketDataFetcher(self.auth_handler)
        self.order_manager = OrderManager(self.auth_handler)
        self.risk_manager = RiskManager(INITIAL_CAPITAL)
        self.shock_detector = MarketShockDetector()
        self.trade_logger = TradeLogger()
        self.strategy = MultiIndicatorStrategy()
        
        self.symbol = TRADING_SYMBOL
        self.is_running = False
        self.data_buffer = []  # Store recent market data
        
        logger.info("Trading bot initialized")
    
    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now().time()
        market_open = dt_time.fromisoformat(MARKET_OPEN)
        market_close = dt_time.fromisoformat(MARKET_CLOSE)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if datetime.now().weekday() >= 5:  # Saturday or Sunday
            return False
        
        return market_open <= now <= market_close
    
    def fetch_and_update_data(self) -> bool:
        """Fetch latest market data and update buffer."""
        try:
            data = self.market_data.fetch_live_data(self.symbol)
            
            if data is not None and not data.empty:
                self.data_buffer.append(data.iloc[0])
                
                # Keep only last 100 data points
                if len(self.data_buffer) > 100:
                    self.data_buffer = self.data_buffer[-100:]
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return False
    
    def get_current_dataframe(self):
        """Convert data buffer to DataFrame."""
        if not self.data_buffer:
            return None
        
        import pandas as pd
        df = pd.DataFrame(self.data_buffer)
        return df
    
    def check_and_manage_positions(self):
        """Check open positions and manage stop losses."""
        try:
            positions = self.order_manager.get_positions()
            
            for position in positions:
                symbol = position.get('symbol') or position.get('tradingsymbol')
                current_price = position.get('ltp') or position.get('last_price', 0)
                
                if symbol and current_price > 0:
                    # Update risk manager
                    self.risk_manager.update_position(symbol, current_price)
                    
                    # Check stop loss
                    if self.risk_manager.check_stop_loss(symbol, current_price):
                        logger.warning(f"Stop loss triggered for {symbol}")
                        self.exit_position(symbol, "stop_loss")
            
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
    
    def enter_position(self, signal: dict) -> bool:
        """Enter a new position based on signal."""
        try:
            if not signal or signal.get('signal') != 'BUY':
                return False
            
            current_price = signal.get('price', 0)
            if current_price == 0:
                return False
            
            # Check risk limits
            if not self.risk_manager.check_daily_loss_limit():
                logger.warning("Daily loss limit reached, not entering new position")
                return False
            
            # Calculate position size
            stop_loss = self.risk_manager.calculate_stop_loss(current_price, is_long=True)
            quantity = self.risk_manager.calculate_position_size(
                current_price, stop_loss, self.risk_manager.current_capital
            )
            
            if quantity <= 0:
                logger.warning("Position size is zero, not entering trade")
                return False
            
            # Place order
            order_result = self.order_manager.place_order(
                symbol=self.symbol,
                transaction_type="BUY",
                quantity=quantity,
                order_type="MARKET"
            )
            
            if order_result and order_result.get('status') == 'SUCCESS':
                order_id = order_result.get('order_id')
                
                # Update risk manager
                self.risk_manager.add_position(
                    self.symbol, current_price, quantity, stop_loss, is_long=True
                )
                
                # Log trade
                self.trade_logger.log_position_open(
                    self.symbol, current_price, quantity, stop_loss, order_id
                )
                
                logger.info(f"Position entered: {quantity} shares @ {current_price}")
                return True
            else:
                logger.error(f"Failed to place order: {order_result}")
                return False
                
        except Exception as e:
            logger.error(f"Error entering position: {e}")
            return False
    
    def exit_position(self, symbol: str, reason: str = "signal") -> bool:
        """Exit an existing position."""
        try:
            position = self.risk_manager.get_position(symbol)
            if not position:
                return False
            
            # Get current price
            data = self.get_current_dataframe()
            if data is None or data.empty:
                logger.warning("No current data available for exit")
                return False
            
            current_price = data['close'].iloc[-1]
            quantity = position['quantity']
            
            # Place sell order
            order_result = self.order_manager.place_order(
                symbol=symbol,
                transaction_type="SELL",
                quantity=quantity,
                order_type="MARKET"
            )
            
            if order_result and order_result.get('status') == 'SUCCESS':
                order_id = order_result.get('order_id')
                
                # Calculate P&L
                pnl = (current_price - position['entry_price']) * quantity
                self.risk_manager.update_daily_pnl(pnl)
                self.risk_manager.current_capital += pnl
                
                # Remove position
                self.risk_manager.remove_position(symbol)
                
                # Log trade
                self.trade_logger.log_position_close(
                    symbol, current_price, quantity, pnl, reason, order_id
                )
                
                logger.info(f"Position exited: {quantity} shares @ {current_price}, P&L: {pnl:.2f}")
                return True
            else:
                logger.error(f"Failed to exit position: {order_result}")
                return False
                
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            return False
    
    def run_trading_cycle(self):
        """Execute one trading cycle."""
        if not self.is_market_open():
            logger.debug("Market is closed")
            return
        
        try:
            # Fetch latest data
            if not self.fetch_and_update_data():
                logger.warning("Failed to fetch market data")
                return
            
            data = self.get_current_dataframe()
            if data is None or len(data) < 2:
                logger.warning("Insufficient data for trading")
                return
            
            # Detect market shocks
            shocks = self.shock_detector.detect_all_shocks(data)
            
            # Check if we should reduce risk or exit positions
            if self.shock_detector.should_exit_positions(shocks):
                logger.warning("Extreme market conditions detected, exiting all positions")
                positions = self.order_manager.get_positions()
                for pos in positions:
                    symbol = pos.get('symbol') or pos.get('tradingsymbol')
                    if symbol:
                        self.exit_position(symbol, "market_shock")
                return
            
            # Get current position
            current_position = None
            positions = self.order_manager.get_positions()
            if positions:
                for pos in positions:
                    symbol = pos.get('symbol') or pos.get('tradingsymbol')
                    if symbol == self.symbol:
                        current_position = self.risk_manager.get_position(symbol)
                        break
            
            # Get trading signal
            signal = self.strategy.get_current_signal(data)
            
            # Check if we should enter trade
            if signal and not current_position:
                # Apply adaptive risk based on shocks
                risk_multiplier = self.shock_detector.get_adaptive_risk_multiplier(shocks)
                if risk_multiplier < 1.0:
                    logger.info(f"Reducing position size due to market shocks (multiplier: {risk_multiplier})")
                    # Adjust position size (this would need to be implemented in risk_manager)
                
                if self.strategy.should_enter_trade(signal, current_position):
                    self.enter_position(signal)
            
            # Check if we should exit trade
            elif current_position and signal:
                if self.strategy.should_exit_trade(signal, current_position):
                    self.exit_position(self.symbol, "signal")
            
            # Manage existing positions (trailing stops, etc.)
            self.check_and_manage_positions()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def start(self):
        """Start the trading bot."""
        logger.info("Starting trading bot...")
        self.is_running = True
        
        # Schedule trading cycles (every minute during market hours)
        schedule.every(1).minutes.do(self.run_trading_cycle)
        
        # Run scheduled tasks
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")
        self.is_running = False
        
        # Print performance summary
        summary = self.trade_logger.get_performance_summary()
        if summary:
            logger.info("Performance Summary:")
            for key, value in summary.items():
                logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
