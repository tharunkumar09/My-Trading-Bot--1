# Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies

```bash
# Install TA-Lib (system library)
# Ubuntu/Debian:
sudo apt-get install ta-lib

# macOS:
brew install ta-lib

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Configure API

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your API credentials
nano .env
```

### Step 3: Run Your First Backtest

```bash
python backtest.py --symbol RELIANCE --start-date 2020-01-01
```

### Step 4: Run Live Trading (Dry Run First!)

```bash
# Dry run (no actual orders)
python live_trading.py --provider upstox --symbols RELIANCE --dry-run

# Live trading (when ready)
python live_trading.py --provider upstox --symbols RELIANCE TCS
```

## Common Commands

### Backtesting
```bash
# Single stock
python backtest.py --symbol RELIANCE

# NIFTY 50 stocks
python backtest.py --nifty50

# Custom date range
python backtest.py --symbol TCS --start-date 2010-01-01 --end-date 2024-01-01
```

### Live Trading
```bash
# Basic
python live_trading.py --provider upstox --symbols RELIANCE

# Custom interval
python live_trading.py --provider upstox --symbols RELIANCE --interval 10

# Multiple symbols
python live_trading.py --provider upstox --symbols RELIANCE TCS INFY HDFCBANK
```

## File Structure Overview

```
├── src/                    # Source code
│   ├── api/               # API clients
│   ├── indicators/        # Technical indicators
│   ├── strategy/          # Trading strategy
│   ├── risk/              # Risk management
│   ├── order/             # Order management
│   ├── data/              # Data fetching
│   └── backtest/          # Backtesting
├── logs/                  # Log files
├── historical_data/       # Cached data
├── backtest_results/      # Backtest reports
├── config.py             # Configuration
├── backtest.py           # Backtest script
└── live_trading.py       # Live trading script
```

## Next Steps

1. **Backtest First**: Always backtest before live trading
2. **Start Small**: Use small capital initially
3. **Monitor Logs**: Check `logs/trading_bot.log` regularly
4. **Review Results**: Analyze backtest results in `backtest_results/`
5. **Adjust Strategy**: Modify parameters in `config.py` based on results

## Troubleshooting

**TA-Lib won't install?**
- Make sure system library is installed first
- Try: `pip install --no-cache-dir TA-Lib`

**API authentication fails?**
- Check `.env` file has correct credentials
- Verify API key permissions
- For Upstox, regenerate access token if expired

**No data fetched?**
- Check internet connection
- Verify symbol format (e.g., 'RELIANCE.NS' for Yahoo)
- Try alternative data source: `--source nsepy`

## Important Notes

⚠️ **Always test with small amounts first!**
⚠️ **Backtest thoroughly before live trading!**
⚠️ **Monitor your bot regularly!**
⚠️ **Set appropriate risk limits!**

## Getting Help

1. Check logs: `tail -f logs/trading_bot.log`
2. Review README.md for detailed documentation
3. Check MARKET_SHOCKS.md for advanced features
4. Verify configuration in config.py

Happy Trading! 📈
