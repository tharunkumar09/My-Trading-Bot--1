"""
Main Trading Bot
Orchestrates all components for automated trading
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, time as dt_time
import time
import schedule
from pathlib import Path

from src.utils.config_loader import get_config
from src.utils.logger import get_logger, log_trade
from src.utils.data_fetcher import DataFetcher
from src.utils.event_monitor import EventMonitor
from src.api.upstox_api import UpstoxAPI
from src.api.angelone_api import AngelOneAPI
from src.strategies.momentum_strategy import MomentumStrategy
from src.risk_management.risk_manager import RiskManager
from src.indicators.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot orchestrator
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize trading bot
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        log_config = self.config.get('logging', {})
        self.logger = get_logger(log_config, name='TradingBot')
        
        self.logger.info("=" * 60)
        self.logger.info("INITIALIZING TRADING BOT")
        self.logger.info("=" * 60)
        
        # Initialize components
        self._init_api()
        self._init_strategy()
        self._init_risk_manager()
        self._init_data_fetcher()
        self._init_event_monitor()
        
        # Trading state
        self.is_running = False
        self.is_market_hours = False
        self.portfolio_value = 0
        self.available_capital = 0
        
        # Get trading configuration
        self.live_config = self.config.get('live_trading', {})
        self.live_enabled = self.live_config.get('enabled', False)
        self.trading_mode = self.live_config.get('mode', 'paper')
        
        # Get market hours
        market_hours = self.live_config.get('market_hours', {})
        self.market_start = market_hours.get('start', '09:15')
        self.market_end = market_hours.get('end', '15:30')
        
        # Get trading universe
        self.universe = self.config.get('universe', {})
        self.trading_symbols = self.universe.get('stocks', [])
        
        self.logger.info(f"Trading mode: {self.trading_mode}")
        self.logger.info(f"Live trading: {'ENABLED' if self.live_enabled else 'DISABLED'}")
        self.logger.info(f"Trading universe: {len(self.trading_symbols)} stocks")
        self.logger.info("Bot initialization complete")
    
    def _init_api(self):
        """Initialize broker API"""
        api_config = self.config.get_api_config()
        provider = api_config['provider']
        
        self.logger.info(f"Initializing {provider.upper()} API...")
        
        if provider == 'upstox':
            self.api = UpstoxAPI(
                api_key=api_config['api_key'],
                api_secret=api_config['api_secret'],
                redirect_uri=api_config.get('redirect_uri')
            )
        elif provider == 'angelone':
            self.api = AngelOneAPI(
                api_key=api_config['api_key'],
                client_id=api_config['client_id'],
                password=api_config['password'],
                totp_secret=api_config.get('totp_secret')
            )
        else:
            raise ValueError(f"Unknown API provider: {provider}")
        
        self.logger.info(f"{provider.upper()} API initialized")
    
    def _init_strategy(self):
        """Initialize trading strategy"""
        strategy_config = self.config.get_strategy_config()
        self.strategy = MomentumStrategy(strategy_config)
        self.logger.info(f"Strategy initialized: {strategy_config.get('name', 'Momentum')}")
    
    def _init_risk_manager(self):
        """Initialize risk manager"""
        risk_config = self.config.get_risk_config()
        self.risk_manager = RiskManager(risk_config)
        self.logger.info("Risk manager initialized")
    
    def _init_data_fetcher(self):
        """Initialize data fetcher"""
        self.data_fetcher = DataFetcher()
        self.logger.info("Data fetcher initialized")
    
    def _init_event_monitor(self):
        """Initialize event monitor"""
        event_config = self.config.get('event_driven', {})
        self.event_monitor = EventMonitor(event_config)
        self.logger.info("Event monitor initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with broker API
        
        Returns:
            True if successful
        """
        self.logger.info("Authenticating with broker...")
        
        try:
            success = self.api.authenticate()
            
            if success:
                self.logger.info("✓ Authentication successful")
                self._update_portfolio_value()
                return True
            else:
                self.logger.error("✗ Authentication failed")
                return False
        
        except Exception as e:
            self.logger.error(f"✗ Authentication error: {str(e)}")
            return False
    
    def _update_portfolio_value(self):
        """Update portfolio value and available capital"""
        try:
            funds = self.api.get_funds()
            
            # Extract available margin/funds (API-specific)
            if isinstance(self.api, UpstoxAPI):
                self.available_capital = funds.get('equity', {}).get('available_margin', 0)
            elif isinstance(self.api, AngelOneAPI):
                self.available_capital = funds.get('availablecash', 0)
            
            # Get positions value
            positions = self.api.get_positions()
            positions_value = sum(
                pos.get('quantity', 0) * pos.get('last_price', 0)
                for pos in positions
            )
            
            self.portfolio_value = self.available_capital + positions_value
            
            self.logger.info(f"Portfolio value: ₹{self.portfolio_value:,.2f}")
            self.logger.info(f"Available capital: ₹{self.available_capital:,.2f}")
        
        except Exception as e:
            self.logger.error(f"Error updating portfolio value: {str(e)}")
    
    def _is_market_open(self) -> bool:
        """Check if market is open"""
        now = datetime.now()
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check time
        current_time = now.time()
        start_time = dt_time.fromisoformat(self.market_start)
        end_time = dt_time.fromisoformat(self.market_end)
        
        return start_time <= current_time <= end_time
    
    def scan_for_opportunities(self) -> List[Dict]:
        """
        Scan trading universe for opportunities
        
        Returns:
            List of trading opportunities
        """
        self.logger.info("Scanning for trading opportunities...")
        
        opportunities = []
        
        for symbol in self.trading_symbols:
            try:
                # Fetch recent data
                df = self.data_fetcher.fetch_historical_data_yahoo(
                    symbol,
                    start_date=(datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                
                if df.empty or len(df) < 200:
                    continue
                
                # Calculate indicators
                df = self.strategy.calculate_indicators(df)
                
                # Generate signals
                df = self.strategy.generate_signals(df)
                
                # Check for buy signal
                if self.strategy.get_entry_signal(df, index=-1):
                    # Check event-driven filters
                    should_avoid, reasons = self.event_monitor.should_avoid_trading(symbol, df)
                    
                    if not should_avoid:
                        current_price = df['close'].iloc[-1]
                        atr = df['atr'].iloc[-1]
                        
                        # Calculate stop loss and take profit
                        stop_loss = self.risk_manager.calculate_stop_loss(
                            symbol, current_price, atr
                        )
                        take_profit = self.risk_manager.calculate_take_profit(
                            current_price, stop_loss
                        )
                        
                        # Calculate position size
                        position_size = self.risk_manager.calculate_position_size(
                            symbol, current_price, stop_loss, self.portfolio_value
                        )
                        
                        if position_size > 0:
                            opportunity = {
                                'symbol': symbol,
                                'current_price': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'atr': atr,
                                'indicators': {
                                    'rsi': df['rsi'].iloc[-1],
                                    'macd': df['macd_line'].iloc[-1],
                                    'ema_200': df['ema_200'].iloc[-1]
                                }
                            }
                            
                            opportunities.append(opportunity)
                            self.logger.info(f"✓ Opportunity found: {symbol} @ ₹{current_price:.2f}")
            
            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {str(e)}")
                continue
            
            # Rate limiting
            time.sleep(0.5)
        
        self.logger.info(f"Found {len(opportunities)} opportunities")
        
        return opportunities
    
    def execute_trade(self, opportunity: Dict) -> bool:
        """
        Execute a trade
        
        Args:
            opportunity: Trading opportunity dictionary
            
        Returns:
            True if successful
        """
        symbol = opportunity['symbol']
        
        # Check if we can open position
        if not self.risk_manager.can_open_position(symbol):
            self.logger.warning(f"Cannot open position in {symbol}")
            return False
        
        try:
            # Place order
            if self.trading_mode == 'paper':
                self.logger.info(f"[PAPER] Would place order: BUY {opportunity['position_size']} {symbol} @ ₹{opportunity['current_price']:.2f}")
                order_id = f"PAPER_{datetime.now().timestamp()}"
            else:
                # Live trading
                order = self.api.place_limit_order(
                    symbol=symbol,
                    exchange='NSE',
                    transaction_type='BUY',
                    quantity=opportunity['position_size'],
                    price=opportunity['current_price'],
                    product='D'
                )
                order_id = order.get('order_id', 'unknown')
                
                self.logger.info(f"✓ Order placed: {order_id}")
            
            # Add to risk manager
            self.risk_manager.add_position(
                symbol=symbol,
                entry_price=opportunity['current_price'],
                quantity=opportunity['position_size'],
                stop_loss=opportunity['stop_loss'],
                take_profit=opportunity['take_profit'],
                direction='long'
            )
            
            # Log trade
            trade_data = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'BUY',
                'quantity': opportunity['position_size'],
                'price': opportunity['current_price'],
                'stop_loss': opportunity['stop_loss'],
                'take_profit': opportunity['take_profit'],
                'order_id': order_id,
                'mode': self.trading_mode
            }
            log_trade(trade_data)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {str(e)}")
            return False
    
    def manage_positions(self):
        """Monitor and manage open positions"""
        active_positions = self.risk_manager.active_positions.copy()
        
        if not active_positions:
            return
        
        self.logger.info(f"Managing {len(active_positions)} open positions...")
        
        for symbol, position in active_positions.items():
            try:
                # Get current price
                quote = self.api.get_quote(symbol)
                current_price = quote.get('last_price', 0)
                
                if current_price == 0:
                    continue
                
                # Check exit conditions
                should_exit, reason = self.risk_manager.check_exit_conditions(
                    symbol, current_price
                )
                
                if should_exit:
                    self.logger.info(f"Exit signal for {symbol}: {reason}")
                    
                    # Close position
                    if self.trading_mode == 'paper':
                        self.logger.info(f"[PAPER] Would close position: SELL {position['quantity']} {symbol} @ ₹{current_price:.2f}")
                    else:
                        self.api.close_position(
                            symbol=symbol,
                            exchange='NSE',
                            quantity=position['quantity'],
                            product='D'
                        )
                        self.logger.info(f"✓ Position closed: {symbol}")
                    
                    # Calculate P&L
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    pnl_pct = (pnl / (position['entry_price'] * position['quantity'])) * 100
                    
                    # Log trade
                    trade_data = {
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'action': 'SELL',
                        'quantity': position['quantity'],
                        'price': current_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': reason,
                        'mode': self.trading_mode
                    }
                    log_trade(trade_data)
                    
                    # Remove from risk manager
                    self.risk_manager.remove_position(symbol)
                    
                    self.logger.info(f"P&L: ₹{pnl:,.2f} ({pnl_pct:.2f}%)")
            
            except Exception as e:
                self.logger.error(f"Error managing position {symbol}: {str(e)}")
                continue
    
    def trading_cycle(self):
        """Execute one trading cycle"""
        try:
            self.logger.info("-" * 60)
            self.logger.info(f"Trading cycle: {datetime.now()}")
            
            # Check if market is open
            if not self._is_market_open():
                self.logger.info("Market is closed")
                return
            
            # Update portfolio
            self._update_portfolio_value()
            
            # Manage existing positions first
            self.manage_positions()
            
            # Look for new opportunities
            opportunities = self.scan_for_opportunities()
            
            # Execute top opportunities
            max_new_positions = (
                self.risk_manager.max_open_positions - 
                len(self.risk_manager.active_positions)
            )
            
            for opportunity in opportunities[:max_new_positions]:
                self.execute_trade(opportunity)
                time.sleep(1)  # Rate limiting
            
            self.logger.info("Trading cycle complete")
        
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {str(e)}")
    
    def start(self):
        """Start the trading bot"""
        self.logger.info("=" * 60)
        self.logger.info("STARTING TRADING BOT")
        self.logger.info("=" * 60)
        
        # Authenticate
        if not self.authenticate():
            self.logger.error("Failed to authenticate. Exiting.")
            return
        
        self.is_running = True
        
        # Schedule trading cycles
        schedule.every(5).minutes.do(self.trading_cycle)
        
        self.logger.info("Bot is running. Press Ctrl+C to stop.")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("Received stop signal")
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.logger.info("=" * 60)
        self.logger.info("STOPPING TRADING BOT")
        self.logger.info("=" * 60)
        
        self.is_running = False
        
        # Close all positions if configured
        # self.close_all_positions()
        
        self.logger.info("Bot stopped")


if __name__ == "__main__":
    # Run the trading bot
    bot = TradingBot()
    bot.start()
