"""
Configuration file for the trading bot.
Store sensitive credentials in .env file (not committed to git).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_PROVIDER = os.getenv("API_PROVIDER", "upstox")  # "upstox" or "angel_one"

# Upstox API Configuration
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:3000")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")

# Angel One API Configuration
ANGEL_ONE_API_KEY = os.getenv("ANGEL_ONE_API_KEY", "")
ANGEL_ONE_CLIENT_ID = os.getenv("ANGEL_ONE_CLIENT_ID", "")
ANGEL_ONE_PIN = os.getenv("ANGEL_ONE_PIN", "")
ANGEL_ONE_TOTP_SECRET = os.getenv("ANGEL_ONE_TOTP_SECRET", "")

# Trading Configuration
TRADING_SYMBOL = os.getenv("TRADING_SYMBOL", "NSE_EQ|INE467B01029")  # Example: Reliance
EXCHANGE = os.getenv("EXCHANGE", "NSE_EQ")
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "INTRADAY")  # INTRADAY, DELIVERY, MARGIN

# Risk Management
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "10000"))  # Max capital per trade
MAX_PORTFOLIO_RISK = float(os.getenv("MAX_PORTFOLIO_RISK", "0.02"))  # 2% of portfolio
STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE", "0.02"))  # 2% stop loss
TRAILING_STOP_PERCENTAGE = float(os.getenv("TRAILING_STOP_PERCENTAGE", "0.01"))  # 1% trailing stop
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "5000"))  # Max daily loss limit

# Strategy Parameters
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))

MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

SUPERTREND_PERIOD = int(os.getenv("SUPERTREND_PERIOD", "10"))
SUPERTREND_MULTIPLIER = float(os.getenv("SUPERTREND_MULTIPLIER", "3.0"))

EMA_PERIOD = int(os.getenv("EMA_PERIOD", "200"))

# Market Shock Detection
VOLATILITY_THRESHOLD = float(os.getenv("VOLATILITY_THRESHOLD", "0.05"))  # 5% intraday move
VOLUME_SPIKE_MULTIPLIER = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "3.0"))  # 3x average volume
SHOCK_DETECTION_WINDOW = int(os.getenv("SHOCK_DETECTION_WINDOW", "5"))  # 5-minute window

# Backtesting Configuration
BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE", "2004-01-01")
BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE", "2024-12-31")
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))
COMMISSION = float(os.getenv("COMMISSION", "0.001"))  # 0.1% commission

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")

# Market Hours (IST)
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"

# Rate Limiting
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))  # requests per minute
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.1"))  # seconds between requests
