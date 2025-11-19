from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yfinance as yf

from src.config import RuntimeConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

NIFTY50_SYMBOLS: List[str] = [
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJAJFINSV",
    "BAJFINANCE",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DIVISLAB",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFC",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "IOC",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SHREECEM",
    "SUNPHARMA",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TITAN",
    "UPL",
    "ULTRACEMCO",
    "WIPRO",
]


def _to_yf_symbol(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return symbol
    return f"{symbol}.NS"


def download_symbol_data(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d",
) -> pd.DataFrame:
    logger.info("Downloading %s from %s to %s (%s)", symbol, start, end, interval)
    data = yf.download(
        tickers=_to_yf_symbol(symbol),
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if data.empty:
        logger.warning("No data returned for %s", symbol)
        return data

    data = data.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    data.index.name = "date"
    data["symbol"] = symbol
    return data


def download_nse_data(
    symbols: Iterable[str],
    start: str,
    end: str,
    interval: str = "1d",
    max_workers: int = 5,
) -> Dict[str, pd.DataFrame]:
    """Download historical bars for a collection of NSE symbols."""

    results: Dict[str, pd.DataFrame] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(download_symbol_data, symbol, start, end, interval): symbol for symbol in symbols
        }
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                df = future.result()
                if not df.empty:
                    csv_path = RAW_DIR / f"{symbol}_{interval}.csv"
                    df.to_csv(csv_path)
                    logger.info("Saved %s rows for %s -> %s", len(df), symbol, csv_path.name)
                    results[symbol] = df
            except Exception as exc:
                logger.exception("Failed to download %s: %s", symbol, exc)
    return results


def load_cached_data(symbol: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    path = RAW_DIR / f"{symbol}_{interval}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def load_or_download(symbols: Iterable[str], cfg: RuntimeConfig) -> Dict[str, pd.DataFrame]:
    start = cfg.backtest.start_date
    end = cfg.backtest.end_date
    interval = cfg.strategy.interval
    dataframes: Dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        cached = load_cached_data(symbol, interval)
        if cached is not None and not cached.empty:
            dataframes[symbol] = cached
            continue
        downloaded = download_nse_data([symbol], start, end, interval)
        if symbol in downloaded:
            dataframes[symbol] = downloaded[symbol]

    return dataframes
