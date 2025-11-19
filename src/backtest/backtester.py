from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RuntimeConfig
from src.strategy.rule_based_strategy import RuleBasedStrategy
from src.utils.logger import get_logger
from src.utils.risk_manager import PositionSizer, apply_trailing_stop

logger = get_logger(__name__)

try:  # optional dependency
    import vectorbt as vbt
except ImportError:
    vbt = None


@dataclass
class BacktestReport:
    metrics: Dict[str, float]
    trades: pd.DataFrame
    equity_curve: pd.Series
    vectorbt_stats: Optional[pd.Series]


class Backtester:
    def __init__(self, cfg: RuntimeConfig) -> None:
        self.cfg = cfg
        self.strategy = RuleBasedStrategy(cfg.strategy)
        self.position_sizer = PositionSizer(cfg.risk)

    def _simulate_trades(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        df["daily_return"] = df["close"].pct_change().fillna(0.0)
        df["strategy_return"] = df["position"].shift(1).fillna(0) * df["daily_return"]
        df["cum_return"] = (1 + df["strategy_return"]).cumprod()
        df["benchmark_return"] = (1 + df["daily_return"]).cumprod()
        df["atr_stop"] = df["close"] - df["atr"] * self.cfg.risk.hard_stop_atr_multiplier * df["position"]
        df["trailing_stop"] = apply_trailing_stop(df, self.cfg.risk.trail_atr_multiplier)

        trades: List[Dict[str, float]] = []
        current_trade: Optional[Dict[str, float]] = None

        qty_series = self.position_sizer.position_size(df["atr"], self.cfg.risk.capital)

        for idx, row in df.iterrows():
            position = row["position"]
            price = row["close"]
            qty = qty_series.loc[idx]
            if current_trade is None and position != 0:
                current_trade = {
                    "symbol": symbol,
                    "entry_date": idx,
                    "entry_price": price,
                    "direction": position,
                    "size": qty,
                }
            elif current_trade is not None and np.sign(position) != np.sign(current_trade["direction"]):
                pnl = (price - current_trade["entry_price"]) * current_trade["direction"] * current_trade["size"]
                trade = {
                    **current_trade,
                    "exit_date": idx,
                    "exit_price": price,
                    "pnl": pnl,
                    "return_pct": (price / current_trade["entry_price"] - 1) * current_trade["direction"] * 100,
                }
                trades.append(trade)
                current_trade = None if position == 0 else {
                    "symbol": symbol,
                    "entry_date": idx,
                    "entry_price": price,
                    "direction": position,
                    "size": qty,
                }

        trades_df = pd.DataFrame(trades)
        return trades_df

    @staticmethod
    def _cagr(equity: pd.Series) -> float:
        years = len(equity) / 252
        if years <= 0 or equity.empty:
            return 0.0
        return (equity.iloc[-1] ** (1 / years)) - 1

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        rolling_max = equity.cummax()
        drawdown = equity / rolling_max - 1
        return drawdown.min()

    @staticmethod
    def _sharpe(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
        if returns.std() == 0:
            return 0.0
        excess = returns - risk_free_rate / 252
        return np.sqrt(252) * excess.mean() / excess.std()

    def _win_rate(self, trades: pd.DataFrame) -> float:
        if trades.empty:
            return 0.0
        return (trades["pnl"] > 0).mean()

    def _vectorbt_portfolio(self, df: pd.DataFrame) -> Optional[pd.Series]:
        if vbt is None:
            return None
        try:
            portfolio = vbt.Portfolio.from_signals(
                close=df["close"],
                entries=df["signal"] == 1,
                exits=df["signal"] == -1,
                size=1.0,
                freq="1D",
                init_cash=self.cfg.risk.capital,
            )
            return portfolio.stats()
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning("vectorbt stats failed: %s", exc)
            return None

    def run(self, data: Dict[str, pd.DataFrame]) -> Dict[str, BacktestReport]:
        reports: Dict[str, BacktestReport] = {}

        for symbol, df in data.items():
            logger.info("Running backtest for %s", symbol)
            signals = self.strategy.generate_signals(df)
            enriched = signals.data
            trades = self._simulate_trades(enriched.copy(), symbol)

            equity_curve = enriched["cum_return"]
            metrics = {
                "CAGR": self._cagr(equity_curve),
                "Max Drawdown": self._max_drawdown(equity_curve),
                "Sharpe": self._sharpe(enriched["strategy_return"]),
                "Win Rate": self._win_rate(trades),
                "Trades": len(trades),
            }

            vectorbt_stats = self._vectorbt_portfolio(enriched)

            reports[symbol] = BacktestReport(
                metrics=metrics,
                trades=trades,
                equity_curve=equity_curve,
                vectorbt_stats=vectorbt_stats,
            )

        return reports

    def save_equity_curve(self, report: BacktestReport, symbol: str, path: Path) -> None:
        plt.figure(figsize=(10, 5))
        report.equity_curve.plot(label="Strategy")
        plt.title(f"{symbol} Equity Curve")
        plt.legend()
        path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close()

    def save_trades(self, report: BacktestReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        report.trades.to_csv(path, index=False)
