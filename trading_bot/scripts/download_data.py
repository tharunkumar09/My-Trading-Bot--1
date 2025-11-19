#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

DEFAULT_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "ITC.NS",
    "SBIN.NS",
    "ASIANPAINT.NS",
    "HINDUNILVR.NS",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download 20+ years of historical NSE data from Yahoo Finance."
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="List of NSE tickers suffixed with .NS",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
        help="Directory to store CSV files",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=(datetime.utcnow() - timedelta(days=365 * 21)).strftime("%Y-%m-%d"),
        help="Start date YYYY-MM-DD",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=datetime.utcnow().strftime("%Y-%m-%d"),
        help="End date YYYY-MM-DD",
    )
    return parser.parse_args()


def download_data(tickers: list[str], output: Path, start: str, end: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for ticker in tickers:
        print(f"Downloading {ticker} ...")
        data = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
        if data.empty:
            print(f"Warning: {ticker} returned no data.")
            continue
        data.to_csv(output / f"{ticker}.csv")


def main():
    args = parse_args()
    download_data(args.tickers, args.output, args.start, args.end)
    print("Download complete.")


if __name__ == "__main__":
    main()
