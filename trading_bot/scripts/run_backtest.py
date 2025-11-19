#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtesting.engine import run_portfolio_backtest
from config.settings import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vectorbt backtest on downloaded data.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Tickers to backtest. Defaults to all CSVs in data/raw",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=settings.paths.root / "data" / "raw",
        help="Directory containing csv data",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=settings.paths.reports_dir,
        help="Directory for summary outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.tickers:
        tickers = args.tickers
    else:
        tickers = [p.stem for p in args.data_dir.glob("*.csv")]
    summary = run_portfolio_backtest(args.data_dir, tickers, args.report_dir)
    output_csv = args.report_dir / "backtest_summary.csv"
    summary.to_csv(output_csv, index=False)
    pd.set_option("display.max_colwidth", None)
    print(summary)
    print(f"\nSummary saved to {output_csv}")


if __name__ == "__main__":
    main()
