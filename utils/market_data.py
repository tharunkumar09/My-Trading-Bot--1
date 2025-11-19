"""
Market data fetching module for live and historical data.
"""
import pandas as pd
import numpy as np
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from utils.logger import get_logger
from config.config import API_PROVIDER, REQUEST_DELAY
import requests

logger = get_logger(__name__)


class MarketDataFetcher:
    """Fetch market data from various sources."""
    
    def __init__(self, auth_handler=None):
        self.auth_handler = auth_handler
        self.session = None
        if auth_handler:
            self.session = auth_handler.get_session()
    
    def fetch_live_data_upstox(self, symbol: str, interval: str = "1minute") -> Optional[pd.DataFrame]:
        """Fetch live market data from Upstox."""
        try:
            from upstox_client.api.market_quote_api import MarketQuoteApi
            from upstox_client.rest import ApiException
            
            if not self.session:
                logger.error("Upstox session not available")
                return None
            
            api_instance = MarketQuoteApi(self.session)
            
            # Get market quote
            response = api_instance.get_market_quote(symbol=symbol)
            
            if response:
                # Convert to DataFrame
                data = {
                    'timestamp': [datetime.now()],
                    'open': [response.data.get('ohlc', {}).get('open', 0))],
                    'high': [response.data.get('ohlc', {}).get('high', 0))],
                    'low': [response.data.get('ohlc', {}).get('low', 0))],
                    'close': [response.data.get('ltp', 0))],
                    'volume': [response.data.get('volume', 0))],
                }
                return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error fetching live data from Upstox: {e}")
            return None
    
    def fetch_live_data_angel_one(self, symbol: str, exchange: str = "NSE") -> Optional[pd.DataFrame]:
        """Fetch live market data from Angel One."""
        try:
            if not self.session:
                logger.error("Angel One session not available")
                return None
            
            # Get market quote
            response = self.session.quote({"exchange": exchange, "tradingsymbol": symbol})
            
            if response and response.get('status'):
                data = response.get('data', {})
                ltp = data.get('ltp', 0)
                ohlc = data.get('ohlc', {})
                
                df_data = {
                    'timestamp': [datetime.now()],
                    'open': [ohlc.get('open', ltp))],
                    'high': [ohlc.get('high', ltp))],
                    'low': [ohlc.get('low', ltp))],
                    'close': [ltp],
                    'volume': [data.get('volume', 0))],
                }
                return pd.DataFrame(df_data)
            
        except Exception as e:
            logger.error(f"Error fetching live data from Angel One: {e}")
            return None
    
    def fetch_historical_data_yfinance(self, symbol: str, period: str = "20y", interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Fetch historical data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE.NS" for NSE)
            period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, 20y, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            import yfinance as yf
            
            logger.info(f"Fetching historical data for {symbol} from Yahoo Finance...")
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            
            # Rename columns to standard format
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in data: {df.columns}")
                return None
            
            # Reset index to make date a column
            df.reset_index(inplace=True)
            if 'date' in df.columns:
                df.rename(columns={'date': 'timestamp'}, inplace=True)
            
            logger.info(f"Fetched {len(df)} records for {symbol}")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except ImportError:
            logger.error("yfinance not installed. Install with: pip install yfinance")
            return None
        except Exception as e:
            logger.error(f"Error fetching historical data from Yahoo Finance: {e}")
            return None
    
    def fetch_historical_data_nsepy(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from NSE using nsepy.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            start_date: Start date
            end_date: End date
        """
        try:
            from nsepy import get_history
            from datetime import date
            
            logger.info(f"Fetching historical data for {symbol} from NSE...")
            
            df = get_history(
                symbol=symbol,
                start=date(start_date.year, start_date.month, start_date.day),
                end=date(end_date.year, end_date.month, end_date.day)
            )
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            
            # Reset index
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'timestamp'}, inplace=True)
            
            # Standardize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            logger.info(f"Fetched {len(df)} records for {symbol}")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except ImportError:
            logger.error("nsepy not installed. Install with: pip install nsepy")
            return None
        except Exception as e:
            logger.error(f"Error fetching historical data from NSE: {e}")
            return None
    
    def fetch_live_data(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """Fetch live data based on configured API provider."""
        time.sleep(REQUEST_DELAY)  # Rate limiting
        
        if API_PROVIDER.lower() == "upstox":
            return self.fetch_live_data_upstox(symbol, **kwargs)
        elif API_PROVIDER.lower() == "angel_one":
            return self.fetch_live_data_angel_one(symbol, **kwargs)
        else:
            logger.error(f"Unknown API provider: {API_PROVIDER}")
            return None
    
    def download_historical_data(self, symbol: str, start_date: str, end_date: str, 
                                  source: str = "yfinance") -> Optional[pd.DataFrame]:
        """
        Download historical data from specified source.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source ("yfinance" or "nsepy")
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if source == "yfinance":
            # For NSE stocks, add .NS suffix
            if not symbol.endswith('.NS'):
                symbol = f"{symbol}.NS"
            return self.fetch_historical_data_yfinance(symbol, period="max")
        elif source == "nsepy":
            return self.fetch_historical_data_nsepy(symbol, start, end)
        else:
            logger.error(f"Unknown data source: {source}")
            return None
