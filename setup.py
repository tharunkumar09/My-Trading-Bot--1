"""
Setup script for the trading bot
"""

from setuptools import setup, find_packages

setup(
    name="indian-stock-trading-bot",
    version="1.0.0",
    description="Algorithmic Trading Bot for Indian Stock Markets",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "websocket-client==1.6.4",
        "pandas==2.1.4",
        "numpy==1.26.2",
        "matplotlib==3.8.2",
        "seaborn==0.13.0",
        "TA-Lib==0.4.28",
        "pandas-ta==0.3.14b0",
        "backtrader==1.9.78.123",
        "vectorbt==0.25.2",
        "yfinance==0.2.32",
        "nsepy==1.0.7",
        "upstox-python-sdk==2.0.0",
        "smartapi-python==1.3.0",
        "schedule==1.2.0",
        "python-dateutil==2.8.2",
        "pytz==2023.3",
        "loguru==0.7.2",
        "sqlalchemy==2.0.23",
        "pytest==7.4.3",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "backtest=backtest:main",
            "trade=live_trading:main",
        ],
    },
)
