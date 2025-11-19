# Algorithmic Trading Bot for Indian Stock Markets

A comprehensive algorithmic trading system for Indian stock markets (NSE/BSE) with support for Upstox and Angel One APIs. Features technical analysis, risk management, backtesting, and live trading capabilities.

## Features

- **Multiple API Support**: Upstox API (preferred) and Angel One SmartAPI
- **Technical Indicators**: RSI, MACD, Supertrend, 200-Day EMA
- **Rule-Based Strategy**: Combines multiple indicators for high-probability signals
- **Risk Management**: Position sizing, stop losses, trailing stops, daily loss limits
- **Backtesting**: 20+ years of historical data support with comprehensive metrics
- **Live Trading**: Automated order placement and position management
- **Error Handling**: Robust error handling and reconnection logic
- **Logging**: Comprehensive logging system

## Project Structure

```
.
├── src/
│   ├── api/                 # API clients (Upstox, Angel One)
│   ├── indicators/          # Technical indicators
│   ├── strategy/           # Trading strategy implementation
│   ├── risk/               # Risk management
│   ├── order/              # Order management
│   ├── data/               # Data fetching and management
│   ├── backtest/           # Backtesting engine
│   └── trading_bot.py      # Main trading bot
├── deploy/                 # Deployment scripts
├── logs/                   # Log files
├── historical_data/        # Cached historical data
├── backtest_results/       # Backtest reports and charts
├── config.py              # Configuration management
├── backtest.py            # Backtesting script
├── live_trading.py        # Live trading script
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- TA-Lib system libraries (see below)
- Upstox or Angel One API credentials

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv gcc make wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

**macOS:**
```bash
brew install ta-lib
```

**Windows:**
Download TA-Lib from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

### Step 2: Setup Python Environment

```bash
# Clone the repository
git clone <repository-url>
cd indian-stock-trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure API Credentials

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**For Upstox:**
1. Register at https://upstox.com/
2. Create an app at https://account.upstox.com/developer/apps
3. Get API key, secret, and redirect URI
4. Complete OAuth flow to get access token

**For Angel One:**
1. Register at https://www.angelone.in/
2. Get API key from SmartAPI
3. Use username, password, and PIN for authentication

## Usage

### Backtesting

Test your strategy on historical data:

```bash
# Backtest a single stock
python backtest.py --symbol RELIANCE --start-date 2004-01-01 --end-date 2024-01-01

# Backtest all NIFTY 50 stocks
python backtest.py --nifty50 --start-date 2004-01-01

# Custom capital and data source
python backtest.py --symbol TCS --capital 1000000 --source yahoo
```

**Backtest Output:**
- Performance metrics (CAGR, Sharpe ratio, max drawdown, win rate)
- Equity curve charts
- Trade-by-trade analysis
- Summary CSV report

### Live Trading

Run the trading bot for live market trading:

```bash
# Basic usage
python live_trading.py --provider upstox --symbols RELIANCE TCS INFY

# Custom interval (check every 10 minutes)
python live_trading.py --provider upstox --symbols RELIANCE --interval 10

# Dry run (no actual orders)
python live_trading.py --provider upstox --symbols RELIANCE --dry-run
```

## Strategy Details

### Entry Conditions

The strategy enters LONG positions when ALL of the following conditions are met:

1. **RSI Oversold**: RSI < 30 OR RSI crosses above 70 (overbought reversal)
2. **MACD Bullish Crossover**: MACD line crosses above signal line
3. **Supertrend Uptrend**: Supertrend indicator shows uptrend (direction = 1)
4. **Price Above 200 EMA**: Price is above 200-day EMA (trend filter)

### Exit Conditions

Positions are exited when ANY of the following occurs:

1. **Stop Loss**: Price hits stop loss (2% default)
2. **Trailing Stop Loss**: Trailing stop triggered (1% default)
3. **RSI Overbought**: RSI > 70 for long positions
4. **MACD Bearish Crossover**: MACD crosses below signal line
5. **Supertrend Reversal**: Supertrend changes to downtrend
6. **Price Below EMA**: Price falls below 200-day EMA

### Risk Management

- **Position Sizing**: Based on risk per trade (2% default)
- **Maximum Positions**: Limited to 5 concurrent positions (configurable)
- **Stop Loss**: 2% below entry price
- **Trailing Stop**: 1% trailing stop after price moves favorably
- **Daily Loss Limit**: 5% maximum daily loss
- **Maximum Position Size**: 20% of capital per position

## Configuration

Edit `config.py` or set environment variables in `.env`:

```python
# Trading Configuration
RISK_PER_TRADE=0.02          # 2% risk per trade
MAX_POSITIONS=5              # Maximum concurrent positions
STOP_LOSS_PERCENT=0.02       # 2% stop loss
TRAILING_STOP_PERCENT=0.01   # 1% trailing stop
CAPITAL=100000              # Starting capital in INR

# Indicator Parameters
RSI_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9
SUPERTREND_PERIOD=10
SUPERTREND_MULTIPLIER=3.0
EMA_PERIOD=200
```

## Deployment

### Local Machine

```bash
chmod +x deploy/local_setup.sh
./deploy/local_setup.sh
```

### AWS EC2 / VPS

```bash
chmod +x deploy/aws_deploy.sh
./deploy/aws_deploy.sh
```

### Cron Job Setup

For scheduled trading during market hours:

```bash
chmod +x deploy/cron_setup.sh
./deploy/cron_setup.sh
```

### Systemd Service (Linux)

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Indian Stock Trading Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/trading-bot
Environment="PATH=/path/to/trading-bot/venv/bin"
ExecStart=/path/to/trading-bot/venv/bin/python live_trading.py --provider upstox --symbols RELIANCE TCS
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

## Monitoring

### Logs

Logs are stored in `logs/` directory:
- `trading_bot.log`: Main trading bot logs
- `backtest.log`: Backtest execution logs

### View Logs

```bash
# Real-time log monitoring
tail -f logs/trading_bot.log

# Search for errors
grep ERROR logs/trading_bot.log

# View last 100 lines
tail -n 100 logs/trading_bot.log
```

## Performance Metrics

Backtesting generates the following metrics:

- **CAGR**: Compound Annual Growth Rate
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Maximum peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of gross profit to gross loss
- **Total Return**: Overall return percentage

## Important Disclaimers

⚠️ **RISK WARNING**: Trading in stock markets involves substantial risk of loss. This software is for educational and research purposes only. Past performance does not guarantee future results.

- **No Guarantees**: The strategy may not work in all market conditions
- **Market Risk**: You may lose your entire capital
- **API Reliability**: Dependencies on third-party APIs
- **Slippage**: Actual execution prices may differ from expected
- **Commissions**: Trading costs reduce net returns

## Troubleshooting

### TA-Lib Installation Issues

If TA-Lib installation fails:
1. Ensure system libraries are installed
2. Try: `pip install --no-cache-dir TA-Lib`
3. On Windows, use pre-built wheels from: https://www.lfd.uci.edu/~gohlke/pythonlibs/

### API Authentication Errors

- Verify credentials in `.env` file
- Check API key permissions
- Ensure access token is valid (Upstox tokens expire)
- For Upstox, regenerate access token if expired

### Data Fetching Issues

- Check internet connection
- Verify symbol format (e.g., 'RELIANCE.NS' for Yahoo Finance)
- Some symbols may not have historical data
- Try alternative data source (yahoo/nsepy)

### Rate Limiting

- The bot implements rate limiting automatically
- If you hit limits, reduce check interval
- Consider upgrading API plan

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is provided as-is for educational purposes. Use at your own risk.

## Support

For issues and questions:
1. Check the logs in `logs/` directory
2. Review configuration in `config.py`
3. Verify API credentials
4. Check market hours (9:15 AM - 3:30 PM IST)

## References

- [Upstox API Documentation](https://upstox.com/developer/api-documentation)
- [Angel One SmartAPI](https://smartapi.angelone.in/)
- [NSEPy Documentation](https://nsepy.readthedocs.io/)
- [TA-Lib Documentation](https://ta-lib.org/)

---

**Built with ❤️ for Indian Stock Markets**
