"""
Logging Configuration
Sets up structured logging for the trading bot
"""

import logging
import sys
from pathlib import Path
from loguru import logger as loguru_logger
from datetime import datetime


class TradingLogger:
    """
    Custom logger for trading bot
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize logger
        
        Args:
            config: Logging configuration
        """
        self.config = config or {}
        
        # Log configuration
        self.log_level = self.config.get('level', 'INFO')
        self.log_to_file = self.config.get('log_to_file', True)
        self.log_file = self.config.get('log_file', 'data/logs/trading_bot.log')
        self.max_file_size = self.config.get('max_file_size', '10MB')
        self.backup_count = self.config.get('backup_count', 5)
        
        # Trade log
        self.trade_log = self.config.get('trade_log', 'data/logs/trades.csv')
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Remove default logger
        loguru_logger.remove()
        
        # Add console logger
        loguru_logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=self.log_level,
            colorize=True
        )
        
        # Add file logger
        if self.log_to_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            loguru_logger.add(
                self.log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
                level=self.log_level,
                rotation=self.max_file_size,
                retention=self.backup_count,
                compression="zip"
            )
        
        # Setup standard logging to use loguru
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level if it exists
                try:
                    level = loguru_logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                # Find caller from where originated the logged message
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        
        # Intercept standard logging
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    def log_trade(self, trade_data: dict):
        """
        Log trade to CSV file
        
        Args:
            trade_data: Dictionary with trade information
        """
        import csv
        
        trade_log_path = Path(self.trade_log)
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists to write header
        file_exists = trade_log_path.exists()
        
        with open(trade_log_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trade_data.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(trade_data)
        
        loguru_logger.info(f"Trade logged: {trade_data}")
    
    def get_logger(self, name: str = None):
        """
        Get logger instance
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name:
            return loguru_logger.bind(name=name)
        return loguru_logger


# Global logger instance
_logger_instance = None


def get_logger(config: dict = None, name: str = None):
    """
    Get global logger instance
    
    Args:
        config: Optional logging configuration
        name: Optional logger name
        
    Returns:
        Logger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = TradingLogger(config)
    
    return _logger_instance.get_logger(name)


def log_trade(trade_data: dict):
    """
    Log trade data
    
    Args:
        trade_data: Trade information
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = TradingLogger()
    
    _logger_instance.log_trade(trade_data)
