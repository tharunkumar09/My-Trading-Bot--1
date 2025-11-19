from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from src.backtest.backtester import Backtester
from src.config import load_config
from src.data.historical_downloader import NIFTY50_SYMBOLS, load_or_download
from src.live.trading_engine import TradingEngine
from src.live.upstox_client import UpstoxClient
from src.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Algorithmic trading bot for NSE markets.")
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest", help="Run mode.")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to process.")
    parser.add_argument("--log-level", default="INFO", help="Logging verbosity.")
    parser.add_argument("--auth-code", help="Upstox auth code for live mode.")
    parser.add_argument("--instrument-keys", nargs="+", help="Instrument keys for streaming.")
    parser.add_argument("--skip-download", action="store_true", help="Use cached data only.")
    return parser.parse_args()


def run_backtest(symbols: Iterable[str], skip_download: bool = False, log_level: str = "INFO") -> None:
    cfg = load_config()
    configure_logging(level=log_level)
    if symbols is None:
        symbols = cfg.strategy.symbols or NIFTY50_SYMBOLS

    data = load_or_download(symbols, cfg) if not skip_download else {}
    if skip_download:
        for sym in symbols:
            from src.data.historical_downloader import load_cached_data

            cached = load_cached_data(sym, cfg.strategy.interval)
            if cached is not None:
                data[sym] = cached
    if not data:
        logger.error("No data available for backtest.")
        sys.exit(1)

    backtester = Backtester(cfg)
    reports = backtester.run(data)
    for symbol, report in reports.items():
        logger.info("Backtest summary for %s: %s", symbol, report.metrics)
        equity_path = cfg.backtest.equity_curve_path.parent / f"{symbol}_equity{cfg.backtest.equity_curve_path.suffix}"
        trades_path = cfg.backtest.trades_log_path.parent / f"{symbol}_trades{cfg.backtest.trades_log_path.suffix}"
        backtester.save_equity_curve(report, symbol, equity_path)
        backtester.save_trades(report, trades_path)


def run_live(
    symbols: Iterable[str],
    auth_code: str | None,
    instrument_keys: Iterable[str] | None,
    log_level: str = "INFO",
) -> None:
    cfg = load_config()
    configure_logging(level=log_level)
    client = UpstoxClient(cfg.api)
    client.authenticate(auth_code)
    client.ensure_connection()
    engine = TradingEngine(cfg, client)
    engine.run_intraday_cycle(symbols or cfg.strategy.symbols)
    if instrument_keys:
        engine.start_streaming(instrument_keys)


def main() -> None:
    args = parse_args()
    if args.mode == "backtest":
        run_backtest(args.symbols, args.skip_download, args.log_level)
    else:
        if not args.auth_code:
            raise ValueError("Auth code is required for live mode.")
        run_live(args.symbols, args.auth_code, args.instrument_keys, args.log_level)


if __name__ == "__main__":
    main()
