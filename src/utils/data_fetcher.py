"""
Data Fetcher
Fetches historical and live data from various sources
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import yfinance as yf
from nsepython import *
import time

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches market data from various sources
    """
    
    def __init__(self):
        """Initialize data fetcher"""
        self.cache = {}
        logger.info("Data fetcher initialized")
    
    def get_nse_symbol(self, symbol: str) -> str:
        """
        Convert symbol to NSE format for Yahoo Finance
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            
        Returns:
            Yahoo Finance symbol (e.g., 'RELIANCE.NS')
        """
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            return f"{symbol}.NS"
        return symbol
    
    def fetch_historical_data_yahoo(self, symbol: str, start_date: str,
                                   end_date: str = None, interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            interval: Data interval (1d, 1wk, 1mo, etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            yf_symbol = self.get_nse_symbol(symbol)
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching data for {yf_symbol} from {start_date} to {end_date}")
            
            # Download data
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                logger.warning(f"No data found for {yf_symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df.columns = [col.lower() for col in df.columns]
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)
            
            logger.info(f"Fetched {len(df)} rows for {yf_symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_nifty50_constituents(self) -> List[str]:
        """
        Fetch NIFTY 50 constituent stocks
        
        Returns:
            List of stock symbols
        """
        try:
            # NIFTY 50 constituents (as of 2024)
            nifty50_stocks = [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
                'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
                'LT', 'ASIANPAINT', 'MARUTI', 'AXISBANK', 'WIPRO',
                'TITAN', 'ULTRACEMCO', 'NESTLEIND', 'BAJFINANCE', 'HCLTECH',
                'SUNPHARMA', 'ONGC', 'NTPC', 'POWERGRID', 'M&M',
                'TATAMOTORS', 'TECHM', 'DIVISLAB', 'ADANIPORTS', 'HINDALCO',
                'TATASTEEL', 'BAJAJFINSV', 'COALINDIA', 'INDUSINDBK', 'DRREDDY',
                'TATACONSUM', 'CIPLA', 'APOLLOHOSP', 'GRASIM', 'EICHERMOT',
                'JSWSTEEL', 'BRITANNIA', 'SBILIFE', 'HEROMOTOCO', 'BPCL',
                'UPL', 'LTIM', 'ADANIENT', 'BAJAJ-AUTO', 'TATACONSUM'
            ]
            
            logger.info(f"Loaded {len(nifty50_stocks)} NIFTY 50 stocks")
            return nifty50_stocks
            
        except Exception as e:
            logger.error(f"Error fetching NIFTY 50 constituents: {str(e)}")
            return []
    
    def fetch_nifty100_constituents(self) -> List[str]:
        """
        Fetch NIFTY 100 constituent stocks
        
        Returns:
            List of stock symbols
        """
        # Get NIFTY 50 first
        nifty100_stocks = self.fetch_nifty50_constituents()
        
        # Add NIFTY Next 50 stocks
        next50_stocks = [
            'ACC', 'ADANIGREEN', 'AMBUJACEM', 'BANDHANBNK', 'BERGEPAINT',
            'BIOCON', 'BOSCHLTD', 'CHOLAFIN', 'COLPAL', 'CONCOR',
            'DLF', 'DABUR', 'DMART', 'GODREJCP', 'HAVELLS',
            'HDFCAMC', 'HDFCLIFE', 'ICICIPRULI', 'INDUSTOWER', 'JINDALSTEL',
            'LUPIN', 'MARICO', 'MCDOWELL-N', 'MUTHOOTFIN', 'NMDC',
            'PAGEIND', 'PETRONET', 'PGHH', 'PIIND', 'PNB',
            'SAIL', 'SBICARD', 'SHREECEM', 'SIEMENS', 'SRF',
            'TORNTPHARM', 'TRENT', 'VEDL', 'VOLTAS', 'ZOMATO',
            'AUROPHARMA', 'BAJAJHLDNG', 'BANKBARODA', 'CANBK', 'GODREJPROP',
            'HINDZINC', 'ICICIGI', 'INDIGO', 'IOC', 'IRCTC'
        ]
        
        nifty100_stocks.extend(next50_stocks)
        
        logger.info(f"Loaded {len(nifty100_stocks)} NIFTY 100 stocks")
        return nifty100_stocks
    
    def fetch_multiple_stocks(self, symbols: List[str], start_date: str,
                             end_date: str = None, interval: str = '1d') -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple stocks
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            interval: Data interval
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        
        for i, symbol in enumerate(symbols):
            logger.info(f"Fetching {symbol} ({i+1}/{len(symbols)})")
            
            df = self.fetch_historical_data_yahoo(symbol, start_date, end_date, interval)
            
            if not df.empty:
                data[symbol] = df
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"Successfully fetched data for {len(data)}/{len(symbols)} stocks")
        
        return data
    
    def filter_stocks_by_criteria(self, symbols: List[str], min_price: float = 0,
                                 max_price: float = float('inf'),
                                 min_volume: int = 0) -> List[str]:
        """
        Filter stocks based on criteria
        
        Args:
            symbols: List of stock symbols
            min_price: Minimum price
            max_price: Maximum price
            min_volume: Minimum daily volume
            
        Returns:
            Filtered list of symbols
        """
        filtered_symbols = []
        
        for symbol in symbols:
            try:
                yf_symbol = self.get_nse_symbol(symbol)
                ticker = yf.Ticker(yf_symbol)
                
                # Get current data
                hist = ticker.history(period='5d')
                
                if hist.empty:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                avg_volume = hist['Volume'].mean()
                
                # Apply filters
                if (min_price <= current_price <= max_price and 
                    avg_volume >= min_volume):
                    filtered_symbols.append(symbol)
                
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error filtering {symbol}: {str(e)}")
                continue
        
        logger.info(f"Filtered to {len(filtered_symbols)}/{len(symbols)} stocks")
        
        return filtered_symbols
    
    def get_nifty_index_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Fetch NIFTY 50 index data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with index data
        """
        return self.fetch_historical_data_yahoo('^NSEI', start_date, end_date)
    
    def export_to_csv(self, data: Dict[str, pd.DataFrame], output_dir: str):
        """
        Export data to CSV files
        
        Args:
            data: Dictionary of symbol -> DataFrame
            output_dir: Output directory path
        """
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        for symbol, df in data.items():
            filepath = os.path.join(output_dir, f"{symbol}.csv")
            df.to_csv(filepath)
            logger.info(f"Exported {symbol} to {filepath}")
        
        logger.info(f"Exported {len(data)} files to {output_dir}")
    
    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """
        Load data from CSV file
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with data
        """
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"Loaded data from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Error loading {filepath}: {str(e)}")
            return pd.DataFrame()
    
    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe
        
        Args:
            df: DataFrame with OHLCV data
            timeframe: Target timeframe ('1D', '1W', '1M', etc.)
            
        Returns:
            Resampled DataFrame
        """
        resampled = df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        resampled = resampled.dropna()
        
        logger.info(f"Resampled data to {timeframe} timeframe")
        
        return resampled


# Convenience function for quick data fetching
def get_stock_data(symbol: str, years: int = 20) -> pd.DataFrame:
    """
    Quick function to get stock data
    
    Args:
        symbol: Stock symbol
        years: Number of years of historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    fetcher = DataFetcher()
    start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')
    return fetcher.fetch_historical_data_yahoo(symbol, start_date)
