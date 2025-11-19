"""
Configuration file for the trading bot.
Loads environment variables and provides centralized configuration.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()


class Config:
    """Centralized configuration class"""
    
    # Upstox API Configuration
    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
    UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
    UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8080/callback")
    UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    
    # Angel One API Configuration (Alternative)
    ANGEL_ONE_API_KEY = os.getenv("ANGEL_ONE_API_KEY", "")
    ANGEL_ONE_USERNAME = os.getenv("ANGEL_ONE_USERNAME", "")
    ANGEL_ONE_PASSWORD = os.getenv("ANGEL_ONE_PASSWORD", "")
    ANGEL_ONE_PIN = os.getenv("ANGEL_ONE_PIN", "")
    
    # Trading Configuration
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))  # 2% per trade
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "0.02"))  # 2%
    TRAILING_STOP_PERCENT = float(os.getenv("TRAILING_STOP_PERCENT", "0.01"))  # 1%
    CAPITAL = float(os.getenv("CAPITAL", "100000"))  # Starting capital
    
    # Market Configuration
    EXCHANGE = os.getenv("EXCHANGE", "NSE")
    INSTRUMENT_TYPE = os.getenv("INSTRUMENT_TYPE", "EQ")
    MARKET_START_TIME = os.getenv("MARKET_TIMING_START", "09:15")
    MARKET_END_TIME = os.getenv("MARKET_TIMING_END", "15:30")
    
    # Indicator Parameters
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    SUPERTREND_PERIOD = 10
    SUPERTREND_MULTIPLIER = 3.0
    EMA_PERIOD = 200
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")
    
    # API Rate Limits
    UPSTOX_RATE_LIMIT = 100  # requests per minute
    ANGEL_ONE_RATE_LIMIT = 200  # requests per minute
    
    # Data Configuration
    HISTORICAL_DATA_PATH = "historical_data"
    BACKTEST_RESULTS_PATH = "backtest_results"
    
    # Risk Management
    MAX_DAILY_LOSS = 0.05  # 5% max daily loss
    MAX_POSITION_SIZE = 0.20  # 20% max position size
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.UPSTOX_API_KEY and not cls.ANGEL_ONE_API_KEY:
            raise ValueError("Either UPSTOX_API_KEY or ANGEL_ONE_API_KEY must be set")
        return True
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """Get API configuration based on available credentials"""
        if cls.UPSTOX_API_KEY:
            return {
                "provider": "upstox",
                "api_key": cls.UPSTOX_API_KEY,
                "api_secret": cls.UPSTOX_API_SECRET,
                "redirect_uri": cls.UPSTOX_REDIRECT_URI,
                "access_token": cls.UPSTOX_ACCESS_TOKEN
            }
        elif cls.ANGEL_ONE_API_KEY:
            return {
                "provider": "angel_one",
                "api_key": cls.ANGEL_ONE_API_KEY,
                "username": cls.ANGEL_ONE_USERNAME,
                "password": cls.ANGEL_ONE_PASSWORD,
                "pin": cls.ANGEL_ONE_PIN
            }
        else:
            raise ValueError("No API credentials configured")
