from __future__ import annotations

import time

import talib

from config.settings import get_settings
from trading.auth import UpstoxAuthenticator
from trading.data_feed import MarketDataClient
from trading.execution import OrderExecutor
from trading.indicators import IndicatorEngine
from trading.logger import setup_logging
from trading.portfolio import PortfolioManager
from trading.risk import RiskConfig, RiskManager
from trading.strategy import ConfluenceStrategy, StrategyParameters


def run_live_trading() -> None:
    settings = get_settings()
    logger = setup_logging(settings.paths.log_dir)

    authenticator = UpstoxAuthenticator(settings.upstox, logger)
    client = authenticator.get_client()

    data_client = MarketDataClient(client, logger)
    indicator_engine = IndicatorEngine()
    strategy = ConfluenceStrategy(StrategyParameters(), logger)

    risk_config = RiskConfig(
        capital=settings.trading.base_capital,
        risk_per_trade=settings.trading.max_risk_per_trade,
        max_positions=settings.trading.max_positions,
        trailing_multiplier=settings.trading.trailing_multiplier,
    )
    risk_manager = RiskManager(risk_config, logger)
    executor = OrderExecutor(client, logger, settings.paths.log_dir / "trade_log.csv")
    portfolio = PortfolioManager(logger)

    symbol = settings.trading.trade_symbol
    interval = settings.trading.interval

    logger.info("Starting live trading loop for %s (%s).", symbol, interval)

    while True:
        try:
            ohlc = data_client.get_ohlc(symbol, interval, lookback_days=400)
            enriched = indicator_engine.enrich(ohlc)
            signal = strategy.generate_signal(enriched)

            if signal and risk_manager.can_enter_new_position() and not portfolio.get_position(symbol):
                qty = risk_manager.calculate_position_size(signal.entry_price, signal.stop_loss)
                if qty > 0:
                    executor.place_order(
                        symbol=symbol,
                        side=signal.side,
                        quantity=qty,
                        order_type="MARKET",
                        stop_loss=signal.stop_loss,
                    )
                    risk_manager.register_fill()
                    portfolio.add_position(
                        symbol=symbol,
                        qty=qty,
                        entry_price=signal.entry_price,
                        side=signal.side,
                        stop_loss=signal.stop_loss,
                        target=signal.target,
                    )
                else:
                    logger.warning("Calculated quantity was zero; skipping order.")

            manage_open_positions(enriched, portfolio, executor, risk_manager)

        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested.")
            break
        except Exception as exc:
            logger.exception("Error in trading loop: %s", exc)
            client = authenticator.refresh_client()
            data_client.client = client
            executor.client = client
            time.sleep(5)

        time.sleep(60)


def manage_open_positions(enriched, portfolio, executor, risk_manager):
    latest_price = enriched["Close"].iloc[-1]
    atr = talib.ATR(enriched["High"], enriched["Low"], enriched["Close"], timeperiod=14).iloc[-1]
    for symbol, position in list(portfolio.positions.items()):
        if position.side == "BUY":
            new_stop = risk_manager.trailing_stop("BUY", position.entry_price, atr, latest_price)
            if new_stop > position.stop_loss:
                portfolio.update_stop(symbol, new_stop)
            if latest_price <= position.stop_loss or latest_price >= position.target:
                executor.place_order(symbol, "SELL", position.qty, order_type="MARKET")
                portfolio.remove_position(symbol)
                risk_manager.register_exit()
        else:
            new_stop = risk_manager.trailing_stop("SELL", position.entry_price, atr, latest_price)
            if new_stop < position.stop_loss:
                portfolio.update_stop(symbol, new_stop)
            if latest_price >= position.stop_loss or latest_price <= position.target:
                executor.place_order(symbol, "BUY", position.qty, order_type="MARKET")
                portfolio.remove_position(symbol)
                risk_manager.register_exit()


if __name__ == "__main__":
    run_live_trading()
