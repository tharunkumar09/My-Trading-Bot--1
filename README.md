# NSE Algorithmic Trading Bot (Upstox)

End-to-end Python framework to research, backtest, and deploy a high-probability rule-based trading system for Indian equities (NSE). The stack covers 20 years of historical testing, TA-Lib indicators (RSI, MACD, Supertrend, EMA-200), vectorbt analytics, risk management, and a production-ready Upstox client for live execution.

## Folder Structure

```
.
├── main.py
├── requirements.txt
├── src
│   ├── backtest
│   │   ├── __init__.py
│   │   └── backtester.py
│   ├── config.py
│   ├── data
│   │   ├── __init__.py
│   │   └── historical_downloader.py
│   ├── indicators
│   │   ├── __init__.py
│   │   └── technicals.py
│   ├── live
│   │   ├── __init__.py
│   │   ├── trading_engine.py
│   │   └── upstox_client.py
│   ├── strategy
│   │   ├── __init__.py
│   │   └── rule_based_strategy.py
│   └── utils
│       ├── __init__.py
│       ├── logger.py
│       └── risk_manager.py
├── data
│   ├── processed/
│   └── raw/
├── logs/
├── assets/
└── notebooks/, scripts/, assets/
```

## Setup

1. **Prerequisites**
   - Python 3.11+
   - TA-Lib binaries installed on the host (see [TA-Lib install guide](https://mrjbq7.github.io/ta-lib/install.html)).
   - Upstox developer account + API keys.

2. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment variables (`.env`)**
   ```
   UPSTOX_API_KEY=xxxx
   UPSTOX_API_SECRET=xxxx
   UPSTOX_REDIRECT_URI=https://example.com/callback
   UPSTOX_CLIENT_CODE=AA0000
   UPSTOX_TOTP_SECRET=optional
   RISK_CAPITAL=1000000
   BACKTEST_START=2005-01-01
   BACKTEST_END=2025-01-01
   ```

## Historical Data & Backtesting (20 Years)

Download NSE equities via Yahoo Finance, compute indicators with TA-Lib, and backtest using vectorbt + custom metrics:

```bash
python main.py --mode backtest --symbols RELIANCE TCS INFY
```

Outputs:
- `assets/{symbol}_equity.png` – equity curve (strategy vs benchmark)
- `logs/{symbol}_trades.csv` – trade log (entry/exit, P&L, win rate)
- Console metrics: CAGR, max drawdown, Sharpe, win rate, trade count, vectorbt stats (if installed)

## Live Trading with Upstox

```bash
python main.py --mode live --symbols RELIANCE TCS --auth-code <upstox_auth_code> --instrument-keys NSE_EQ-RELIANCE-EQ
```

Features:
- OAuth2 authentication, refresh handling, heartbeat, websocket tick stream
- Market/limit/stop-loss orders with ATR-based position sizing
- Live trade logging to `logs/live_trades.jsonl`
- Shock filters + volatility regime detection before any order is sent

## Risk Management & Best Practices
- ATR-based position sizing (fixed 1% capital risk/trade by default)
- Hard and trailing stop levels (ATR multipliers configurable)
- Liquidity filter (20-day average volume threshold)
- API rate-limit retries (tenacity backoff) + heartbeat verification
- Trade logging for audits and reconciliation

## Automation (Cron / Systemd)

Sample cron entry to run every 15 minutes on trading days:
```
*/15 9-15 * * 1-5 cd /workspace && /workspace/.venv/bin/python main.py --mode live --symbols RELIANCE TCS --auth-code $UPSTOX_CODE >> logs/cron.log 2>&1
```

For a resilient always-on service, prefer systemd:
```
[Unit]
Description=NSE Algo Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/workspace
EnvironmentFile=/workspace/.env
ExecStart=/workspace/.venv/bin/python main.py --mode live --symbols RELIANCE TCS --auth-code ${UPSTOX_AUTH}
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Deployment Guidance

- **Local workstation**: run inside virtualenv/conda; keep `.env` encrypted (e.g., `sops`, `age`), rotate tokens daily.
- **AWS / Azure cloud**:
  - Use EC2 or Azure VM with Ubuntu 22.04, attach IAM role for parameter store/Key Vault.
  - Install TA-Lib, Dockerize the app, run via ECS/EKS or Azure Container Apps with auto-restart.
  - Enable CloudWatch (AWS) or Azure Monitor logs + metrics for latency, order errors, P&L.
- **Always-on VPS (DigitalOcean/Linode)**:
  - Harden SSH, run behind firewall, monitor process via `systemd` or `supervisord`.
  - Add `fail2ban`, configure automatic OS updates, and keep redundancy (secondary VPS) for failover.

## Handling Market Shocks & Efficiency Improvements

1. **Event-aware filtering** – integrate NSE corporate action feeds and economic calendars (e.g., [NSE Market Data & Announcements](https://www.nseindia.com/market-data)) to avoid trades during scheduled shocks (earnings, policy updates).
2. **Regulatory-aligned risk controls** – follow SEBI’s risk management practices (see [SEBI circulars](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3)) for stress scenarios: tighten leverage, drop open orders, and cap exposure to impacted sectors.
3. **Volatility-driven throttling** – if intraday realized volatility > 2× 90-day average (proxied via India VIX feed), automatically reduce position sizes or pause new entries.
4. **News/NLP hooks** – connect to reliable news APIs (Reuters, Bloomberg, PIB India) to score sentiment changes and only allow trades when news score is neutral/positive; bail out if major tariff/war/government-policy keywords surface.
5. **Liquidity shock safeguards** – require bid-ask depth thresholds using Upstox market quotes before sending large orders; slice orders (iceberg) when NSE best-5 depth is shallow.
6. **Disaster recovery** – implement hot-standby VPS + database replication so that failover occurs within seconds during outages, ensuring orders can be cancelled or hedged quickly.

## Improving This Prompt

To make the request even more actionable and resilient, consider adding:

- **Source-backed data requirements**: cite NSE historical data API specs or Yahoo Finance documentation, ensuring reproducibility.
- **Stress scenarios referencing credible research**: e.g., RBI Financial Stability Reports, IMF Global Financial Stability Report sections on emerging markets, or BIS volatility studies to calibrate shock thresholds.
- **Clear performance benchmarks**: specify desired minimum CAGR, Sharpe, and maximum tolerable drawdown to align with professional risk mandates.
- **Compliance checkpoints**: request explicit logging of SEBI-mandated order/trade IDs and audit trails, referencing SEBI’s algo guidelines.
- **Disaster drills**: require simulated tests for earnings shocks, tariff announcements, or geopolitical events using historical windows (e.g., 2008 crisis, 2013 taper tantrum, 2020 pandemic).

These additions—grounded in NSE/SEBI/RBI primary sources—will produce a more robust, regulator-ready algo spec that can both manage and capitalize on extreme market shifts.

> ⚠️ **Disclaimer**: This project is for educational purposes. Historical backtests do not guarantee future performance. Always comply with SEBI/NSE regulations and thoroughly test on paper-trading environments before risking capital.
