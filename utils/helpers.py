"""
Helper utility functions
"""

from datetime import datetime, time
from typing import Optional
from loguru import logger


def is_market_hours() -> bool:
    """Check if current time is within market hours"""
    now = datetime.now().time()
    market_start = time(9, 15)  # 9:15 AM
    market_end = time(15, 30)   # 3:30 PM
    
    # Check if weekday (Monday=0, Sunday=6)
    if datetime.now().weekday() >= 5:
        return False
    
    return market_start <= now <= market_end


def format_currency(amount: float) -> str:
    """Format amount as Indian currency"""
    return f"₹{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage"""
    return f"{value:.{decimals}f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def validate_symbol(symbol: str) -> bool:
    """Validate stock symbol format"""
    if not symbol or len(symbol) < 2:
        return False
    # Basic validation - can be enhanced
    return symbol.isalnum() or '.' in symbol


def get_instrument_key_mapping() -> dict:
    """
    Get mapping of symbols to instrument keys
    This is a placeholder - in production, fetch from API master contract
    """
    # Example mapping (would be fetched from API)
    return {
        'RELIANCE': 'NSE_EQ|INE467B01029',
        'TCS': 'NSE_EQ|INE467B01029',
        'INFY': 'NSE_EQ|INE009A01021',
        # Add more mappings as needed
    }
