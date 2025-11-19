from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import talib
import vectorbt as vbt

from trading.indicators import IndicatorEngine
from trading.strategy import StrategyParameters


def _load_price_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df.set_index(date_col, inplace=True)
    df = df.rename(
        columns={
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Adj Close": "Adj Close",
            "Volume": "Volume",
        }
    )
    return df[["Open", "High", "Low", "Close", "Volume"]]


def _compute_signals(
    prices: pd.DataFrame,
    params: StrategyParameters,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    enriched = IndicatorEngine().enrich(prices)
    atr = talib.ATR(enriched["High"], enriched["Low"], enriched["Close"], timeperiod=params.atr_period)
    long_entries = (
        (enriched["trend_filter"] > 0)
        & (enriched["Close"] > enriched["supertrend"])
        & (enriched["rsi"] <= params.rsi_buy_level)
        & (enriched["macd"].shift(1) <= enriched["macd_signal"].shift(1))
        & (enriched["macd"] > enriched["macd_signal"])
    )
    long_exits = (enriched["Close"] < enriched["supertrend"]) | (enriched["rsi"] >= params.rsi_sell_level)

    short_entries = (
        (enriched["trend_filter"] < 0)
        & (enriched["Close"] < enriched["supertrend"])
        & (enriched["rsi"] >= params.rsi_sell_level)
        & (enriched["macd"].shift(1) >= enriched["macd_signal"].shift(1))
        & (enriched["macd"] < enriched["macd_signal"])
    )
    short_exits = (enriched["Close"] > enriched["supertrend"]) | (enriched["rsi"] <= params.rsi_buy_level)

    sl_pct = (params.stop_atr_multiple * atr) / enriched["Close"]
    tp_pct = params.target_rr * sl_pct

    return enriched["Close"], long_entries, long_exits, short_entries, short_exits, sl_pct, tp_pct


def backtest_single(
    ticker: str,
    data_path: Path,
    params: StrategyParameters,
    fee_bps: float = 5,
) -> Tuple[Dict[str, float], pd.Series]:
    prices = _load_price_file(data_path)
    close, long_entries, long_exits, short_entries, short_exits, sl_pct, tp_pct = _compute_signals(prices, params)

    if close.empty:
        raise ValueError(f"No price data found for {ticker}")

    portfolio = vbt.Portfolio.from_signals(
        close,
        entries=long_entries,
        exits=long_exits,
        short_entries=short_entries,
        short_exits=short_exits,
        init_cash=1_000_000,
        slippage=fee_bps / 10000,
        fees=fee_bps / 10000,
        sl_stop=sl_pct.to_numpy(),
        tp_stop=tp_pct.to_numpy(),
        size=1.0,
        direction="both",
    )

    equity = portfolio.value()
    metrics = _compute_metrics(equity, portfolio)
    metrics["ticker"] = ticker
    return metrics, equity


def _compute_metrics(equity: pd.Series, portfolio: vbt.Portfolio) -> Dict[str, float]:
    daily_returns = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    drawdown = (equity / equity.cummax()) - 1
    max_drawdown = drawdown.min()
    sharpe = (
        np.sqrt(252) * daily_returns.mean() / daily_returns.std()
        if daily_returns.std() != 0
        else 0.0
    )
    win_rate = float(portfolio.trades.win_rate())
    return {
        "CAGR": cagr,
        "Max Drawdown": max_drawdown,
        "Sharpe": sharpe,
        "Total Return": total_return,
        "Win Rate": win_rate,
    }


def run_portfolio_backtest(
    data_dir: Path,
    tickers: Iterable[str],
    report_dir: Path,
) -> pd.DataFrame:
    params = StrategyParameters()
    results: List[Dict[str, float]] = []
    equity_curves: Dict[str, pd.Series] = {}

    for ticker in tickers:
        path = data_dir / f"{ticker}.csv"
        if not path.exists():
            continue
        metrics, equity = backtest_single(ticker, path, params)
        results.append(metrics)
        equity_curves[ticker] = equity / equity.iloc[0]

    summary_df = pd.DataFrame(results)
    if summary_df.empty:
        raise RuntimeError("No backtest results generated. Did you download the data?")

    _plot_equity_curves(equity_curves, report_dir)
    return summary_df


def _plot_equity_curves(equity_curves: Dict[str, pd.Series], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 6))
    for ticker, eq in equity_curves.items():
        plt.plot(eq.index, eq.values, label=ticker)
    plt.legend()
    plt.title("Strategy Equity Curves (Normalized)")
    plt.xlabel("Date")
    plt.ylabel("Equity (normalized)")
    plt.tight_layout()
    output_path = report_dir / "equity_curve.png"
    plt.savefig(output_path)
    plt.close()
