## Overview

Algorithmic trading stack for Indian equities built around the Upstox API (Angel One SmartAPI can reuse the same abstractions). The bot combines RSI(14), MACD(12,26,9), Supertrend(10,3), and a 200-period EMA trend filter inside a confluence-based strategy with ATR shock protection, position sizing, and automated risk controls. The repository also covers 20-year historical data ingestion (Yahoo Finance NSE tickers), vectorbt backtesting, deployment recipes, and automation guidance.


## Folder Structure

```
trading_bot/
├── backtesting/
│   └── engine.py
├── config/
│   └── settings.py
├── data/
│   └── raw/                  # historical CSVs downloaded via scripts/download_data.py
├── logs/
│   └── (runtime logs + trade_log.csv)
├── reports/
│   └── (equity_curve.png, backtest_summary.csv)
├── scripts/
│   ├── download_data.py      # 20+ year NSE data via yfinance
│   └── run_backtest.py       # vectorbt backtest runner
├── trading/
│   ├── __init__.py
│   ├── auth.py               # Upstox authentication lifecycle
│   ├── data_feed.py          # live + fallback data handlers
│   ├── execution.py          # order placement & trade logging
│   ├── indicators.py         # RSI, MACD, Supertrend, EMA, ATR
│   ├── logger.py
│   ├── portfolio.py          # open-position tracking
│   ├── risk.py               # position sizing, trailing SL
│   ├── strategy.py           # rule-based confluence strategy
│   └── utils.py
├── main.py                   # live trading entrypoint
├── requirements.txt
└── README.md
```


## Prerequisites & Installation

1. **System packages**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-dev python3-venv build-essential libssl-dev libffi-dev
   sudo apt-get install -y ta-lib || { \
       wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
       tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib && \
       ./configure --prefix=/usr && make && sudo make install; }
   ```
2. **Python dependencies**
   ```bash
   cd trading_bot
   python3 -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```


## Environment Variables (`.env`)

```
UPSTOX_API_KEY=your_key
UPSTOX_API_SECRET=your_secret
UPSTOX_REDIRECT_URI=https://your.app/callback
UPSTOX_ACCESS_TOKEN=optional_cached_token
BASE_CAPITAL=1000000
MAX_RISK_PER_TRADE=0.01
MAX_CONCURRENT_POSITIONS=5
SLIPPAGE_BPS=0.5
ATR_MULTIPLIER=2.0
TRAILING_MULTIPLIER=1.5
DEFAULT_SYMBOL=RELIANCE.NS
TRADE_INTERVAL=15minute
```

`config/settings.py` loads these values automatically.


## Workflow

### 1. Download ≥20 years of NSE data
```bash
source .venv/bin/activate
python scripts/download_data.py --tickers RELIANCE.NS TCS.NS INFY.NS
```

### 2. Backtest with vectorbt
```bash
python scripts/run_backtest.py --tickers RELIANCE.NS TCS.NS INFY.NS
# Outputs reports/backtest_summary.csv + reports/equity_curve.png
```

Each row reports CAGR, max drawdown, Sharpe, win rate, and total return. Adjust parameters inside `StrategyParameters` to re-calibrate.

### 3. Live trading
1. Run `python -m trading.auth` flow (or call `UpstoxAuthenticator.build_login_url`) to fetch a fresh authorization code.
2. Store the resulting access token in `.env`.
3. Execute the bot:
   ```bash
   python main.py
   ```
Logs stream to `logs/trading_bot.log`, while broker fills append to `logs/trade_log.csv`.


## Scheduling & Automation

- **Cron (minute-bar monitoring):**
  ```
  * * * * * cd /path/to/trading_bot && /usr/bin/env bash -c 'source .venv/bin/activate && python main.py >> logs/cron.log 2>&1'
  ```
  Pair with `supercronic` or `systemd` for failure restarts.

- **systemd service (recommended for Linux/VPS):**
  ```
  [Unit]
  Description=Upstox Algo Bot
  After=network.target

  [Service]
  WorkingDirectory=/path/to/trading_bot
  Environment="PATH=/path/to/trading_bot/.venv/bin"
  ExecStart=/path/to/trading_bot/.venv/bin/python main.py
  Restart=always
  RestartSec=15

  [Install]
  WantedBy=multi-user.target
  ```
  `sudo systemctl enable --now upstox-bot`.

- **Container orchestration:** Wrap `main.py` and scripts inside a Docker image and use AWS ECS / Azure Container Apps for scheduled or always-on execution.


## Deployment Playbooks

- **Local workstation:** keep `.env` outside version control, use `tmux`/`screen` for session persistence, and point logs to encrypted storage.
- **AWS:** 
  - Use EC2 (Graviton or c7g) or AWS Batch for backtesting. 
  - Store `.env` in AWS Secrets Manager, grant via IAM role, and stream logs to CloudWatch.
  - For fully managed scheduling, combine EventBridge → ECS Fargate to run `scripts/run_backtest.py` nightly.
- **Azure:** 
  - Deploy containerized bot to Azure Container Instances or Azure Kubernetes Service with Managed Identity for Key Vault secrets.
  - Persist data on Azure Files and push reports to Blob Storage / Power BI.
- **Always-on VPS:** 
  - Harden SSH, keep OS patched, install fail2ban, and monitor via Prometheus node exporter.


## Risk Management, Shocks & Resilience

- **Position sizing:** `RiskManager.calculate_position_size` caps each trade to `base_capital * max_risk_per_trade`.
- **Volatility brakes:** ATR-based stop placement plus `shock_threshold` skip logic prevents trades when single-bar range exceeds 4% (tunable for earnings gaps, policy shocks, or war headlines).
- **Trailing stops:** `RiskManager.trailing_stop` and `manage_open_positions` adjust SL in real time as trades move in your favor.
- **Circuit-breaker hooks:** Enrich `strategy.py` with NSE market status API and India VIX feeds to pause trading on limit-down days.
- **Rate limit handling:** Wrapped API calls via `trading.utils.retryable` for exponential backoff (tenacity), plus `MarketDataClient` fallback to Yahoo if Upstox data blips.
- **News/policy overlays:** Extend `ConfluenceStrategy` with an external event feed (e.g., Reuters, Bloomberg, stock-specific earnings calendar) to tighten thresholds or reduce position size when major events are upcoming.


## Key Scripts & Usage

- `scripts/download_data.py`: CLI to download per-ticker CSVs (defaults to 10 NIFTY50 components). Use nightly cron to keep datasets updated.
- `scripts/run_backtest.py`: Aggregates KPI metrics and saves normalized equity curves. Integrate with CI/CD to detect performance drift.
- `main.py`: Production trading loop with reconnect logic, continuous logging, and stateful position management.


## Prompt Enhancements & Reliable References

To make the trading bot brief more actionable and shock-aware, explicitly cite authoritative sources and stress requirements such as:

1. **Exchange compliance:** Reference SEBI algorithmic trading circulars (e.g., *SEBI/HO/MRD2/DCAP/P/CIR/2021/13*, Jan 14 2021) to mandate kill-switches, audit logs, and risk-check checkpoints.
2. **Broker specs:** Link Upstox API documentation (https://upstox.com/developer/api-documentation) or Angel One SmartAPI docs to lock down authentication scopes, order limits, and streaming payload schemas.
3. **Data quality:** Cite NSE Bhavcopy archives and Yahoo Finance historical endpoints for reproducible backtests, insisting on ≥20y of split-adjusted data with survivorship-bias awareness.
4. **Volatility regimes:** Require integration with India VIX (NSE) or RBI policy calendars (https://rbi.org.in) so the strategy can de-risk ahead of macro shocks, tariffs, or bailouts.
5. **Event-driven overlays:** Ask for earnings calendars (e.g., CMIE Prowess, NSE corporate filings) and geopolitical risk feeds to dynamically widen stops, cut leverage, or temporarily disable entries.

Embedding these references in the specification guides implementers toward verifiable data sources, regulatory compliance, and robust behavior under sudden regime shifts (tariffs, wars, bailouts, etc.).
