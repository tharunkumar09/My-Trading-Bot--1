"""
Trading package exposing high-level components required by the algorithmic strategy.
"""

from .auth import UpstoxAuthenticator
from .data_feed import MarketDataClient
from .execution import OrderExecutor
from .indicators import IndicatorEngine
from .portfolio import PortfolioManager
from .risk import RiskManager
from .strategy import ConfluenceStrategy, StrategyParameters

__all__ = [
    "UpstoxAuthenticator",
    "MarketDataClient",
    "OrderExecutor",
    "IndicatorEngine",
    "PortfolioManager",
    "RiskManager",
    "ConfluenceStrategy",
    "StrategyParameters",
]
