# Algorithmic Trading Bot for Indian Stock Markets

A comprehensive algorithmic trading bot for Indian stock markets (NSE/BSE) with support for Upstox and Angel One APIs. Features multi-indicator strategy, backtesting, risk management, and market shock detection.

## Features

- ✅ **Multi-API Support**: Upstox and Angel One SmartAPI
- ✅ **Technical Indicators**: RSI, MACD, Supertrend, 200-Day EMA
- ✅ **Advanced Strategy**: Rule-based combination of multiple indicators
- ✅ **Backtesting Engine**: 20+ years of historical data support
- ✅ **Risk Management**: Position sizing, stop losses, trailing stops
- ✅ **Market Shock Detection**: Adaptive risk management for unpredictable events
- ✅ **Trade Logging**: Complete trade history and performance tracking
- ✅ **Production Ready**: Error handling, reconnection logic, logging

## Project Structure

```
.
├── config/                 # Configuration files
│   ├── config.py          # Main configuration
│   └── .env.example       # Environment variables template
├── utils/                  # Utility modules
│   ├── auth.py            # API authentication
│   ├── market_data.py     # Market data fetching
│   ├── indicators.py      # Technical indicators
│   ├── order_manager.py   # Order placement and management
│   ├── risk_manager.py    # Risk and position management
│   ├── market_shock_detector.py  # Market shock detection
│   ├── trade_logger.py    # Trade logging
│   └── logger.py          # Logging utility
├── strategies/            # Trading strategies
│   └── multi_indicator_strategy.py  # Main strategy
├── backtesting/           # Backtesting engine
│   └── backtest_engine.py # Backtest implementation
├── data/                  # Historical data storage
├── logs/                  # Log files
├── trading_bot.py         # Main trading bot
├── run_backtest.py        # Backtest runner script
├── download_data.py       # Data download script
├── requirements.txt       # Python dependencies
├── DEPLOYMENT.md          # Deployment guide
└── MARKET_SHOCKS.md       # Market shock handling guide
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install TA-Lib (required for indicators)
# Ubuntu/Debian:
sudo apt-get install ta-lib
pip install TA-Lib

# macOS:
brew install ta-lib
pip install TA-Lib

# Windows: Download from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
```

### 2. Configuration

```bash
# Copy environment template
cp config/.env.example config/.env

# Edit config/.env with your API credentials
nano config/.env
```

Required configuration:
- `API_PROVIDER`: "upstox" or "angel_one"
- API credentials (API key, secret, access token)
- Trading symbol
- Risk management parameters

### 3. Download Historical Data

```bash
# Download 20 years of data for backtesting
python download_data.py --symbol RELIANCE --start 2004-01-01 --end 2024-12-31 --source yfinance
```

### 4. Run Backtest

```bash
# Run backtest on historical data
python run_backtest.py --symbol RELIANCE --start 2020-01-01 --end 2024-01-01

# With custom parameters
python run_backtest.py \
    --symbol RELIANCE \
    --start 2020-01-01 \
    --end 2024-01-01 \
    --capital 100000 \
    --output backtesting/results.png
```

### 5. Start Trading Bot

```bash
# Run the trading bot (paper trading recommended first)
python trading_bot.py
```

## Strategy Overview

The bot uses a multi-indicator strategy combining:

1. **RSI (14)**: Identifies overbought/oversold conditions
   - Buy: RSI < 30 (oversold)
   - Sell: RSI > 70 (overbought)

2. **MACD (12, 26, 9)**: Detects trend changes
   - Buy: MACD crosses above signal line
   - Sell: MACD crosses below signal line

3. **Supertrend (10, 3)**: Trend following indicator
   - Buy: Price above Supertrend
   - Sell: Price below Supertrend

4. **200-Day EMA**: Long-term trend filter
   - Buy: Price above 200 EMA (uptrend)
   - Sell: Price below 200 EMA (downtrend)

**Entry Conditions (All must be true):**
- RSI oversold (< 30)
- MACD bullish crossover
- Price above Supertrend
- Price above 200 EMA

**Exit Conditions:**
- RSI overbought (> 70)
- MACD bearish crossover
- Price below Supertrend
- Price below 200 EMA
- Stop loss triggered
- Trailing stop triggered

## Risk Management

### Position Sizing
- Maximum 2% portfolio risk per trade
- Position size calculated based on stop loss distance
- Maximum position size limit (configurable)

### Stop Losses
- Initial stop loss: 2% from entry (configurable)
- Trailing stop: Activates after favorable move
- Trailing stop distance: 1% (configurable)

### Daily Limits
- Maximum daily loss limit
- Automatic trading halt if limit reached
- Resets daily at market open

## Market Shock Detection

The bot includes advanced market shock detection to handle:
- Earnings announcements
- Policy changes
- Geopolitical events
- Sector-specific news
- Sudden volatility spikes

**Features:**
- Price shock detection (>5% moves)
- Volume spike detection (3x average)
- Volatility monitoring
- Gap detection (overnight moves)
- Adaptive risk reduction
- Emergency position exit

See [MARKET_SHOCKS.md](MARKET_SHOCKS.md) for detailed documentation.

## Backtesting Results

The backtesting engine provides comprehensive metrics:

- **CAGR**: Compound Annual Growth Rate
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Maximum peak-to-trough decline
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Ratio of gross profit to gross loss
- **Equity Curve**: Visual representation of performance

Example output:
```
BACKTEST SUMMARY
============================================================
Initial Capital:     ₹100,000.00
Final Equity:        ₹150,000.00
Total Return:        50.00%
CAGR:                12.50%
Sharpe Ratio:        1.85
Max Drawdown:        -15.20%
Win Rate:            58.50%
Total Trades:        245
Winning Trades:       143
Losing Trades:       102
Average Win:         ₹2,450.00
Average Loss:        ₹-1,200.00
Profit Factor:       2.04
============================================================
```

## Deployment

### Local Machine
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Linux VPS
```bash
# Create systemd service
sudo nano /etc/systemd/system/trading-bot.service

# Enable and start
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

### AWS EC2 / Azure VM
Full deployment guide in [DEPLOYMENT.md](DEPLOYMENT.md).

### Scheduling
```bash
# Add to crontab
crontab -e

# Run backtest daily at 6 PM
0 18 * * * cd /path/to/trading-bot && python run_backtest.py --symbol RELIANCE
```

## Configuration Options

Key configuration parameters in `config/config.py`:

### Trading Parameters
- `RSI_PERIOD`: RSI calculation period (default: 14)
- `RSI_OVERSOLD`: Oversold threshold (default: 30)
- `RSI_OVERBOUGHT`: Overbought threshold (default: 70)
- `MACD_FAST`: MACD fast period (default: 12)
- `MACD_SLOW`: MACD slow period (default: 26)
- `SUPERTREND_PERIOD`: Supertrend period (default: 10)
- `EMA_PERIOD`: EMA period (default: 200)

### Risk Management
- `MAX_POSITION_SIZE`: Maximum capital per trade
- `MAX_PORTFOLIO_RISK`: Maximum portfolio risk per trade (default: 2%)
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage (default: 2%)
- `TRAILING_STOP_PERCENTAGE`: Trailing stop percentage (default: 1%)
- `MAX_DAILY_LOSS`: Maximum daily loss limit

### Market Shock Detection
- `VOLATILITY_THRESHOLD`: Volatility threshold (default: 5%)
- `VOLUME_SPIKE_MULTIPLIER`: Volume spike multiplier (default: 3.0)
- `SHOCK_DETECTION_WINDOW`: Detection window in minutes (default: 5)

## Logging

Logs are stored in the `logs/` directory:
- `trading_bot.log`: Main application log
- `errors.log`: Error log
- `trades.json`: Trade history (JSON format)

## API Setup

### Upstox API

1. Register at [Upstox](https://upstox.com/)
2. Create API application
3. Get API key and secret
4. Authorize application (one-time)
5. Get access token
6. Add credentials to `.env`

### Angel One SmartAPI

1. Register at [Angel One](https://www.angelone.in/)
2. Enable SmartAPI
3. Get API key and client ID
4. Set up TOTP for 2FA
5. Add credentials to `.env`

## Important Disclaimers

⚠️ **WARNING**: This software is for educational and research purposes only.

- **Not Financial Advice**: This bot is not a recommendation to buy or sell securities
- **No Guarantees**: Past performance does not guarantee future results
- **Risk of Loss**: Trading involves substantial risk of loss
- **Paper Trading First**: Always test with paper trading before live trading
- **Market Conditions**: Strategies may not work in all market conditions
- **Regulatory Compliance**: Ensure compliance with local regulations

## Best Practices

1. **Start Small**: Begin with small position sizes
2. **Paper Trade First**: Test thoroughly before live trading
3. **Monitor Closely**: Regularly check bot performance
4. **Set Limits**: Use daily loss limits and position size limits
5. **Regular Backtesting**: Backtest on different time periods
6. **Market Awareness**: Stay informed about market conditions
7. **Continuous Improvement**: Refine strategy based on results

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**TA-Lib Installation:**
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib
pip install TA-Lib

# If still failing, try:
pip install --upgrade pip
pip install TA-Lib --no-cache-dir
```

**API Connection Errors:**
- Verify API credentials in `.env`
- Check internet connectivity
- Review API rate limits
- Check API status page

**Data Download Issues:**
- Try different data source (yfinance vs nsepy)
- Check symbol format (e.g., "RELIANCE.NS" for yfinance)
- Verify date ranges are valid

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational purposes. Use at your own risk.

## Support

For issues and questions:
- Check existing issues on GitHub
- Review documentation in `DEPLOYMENT.md` and `MARKET_SHOCKS.md`
- Ensure all dependencies are installed correctly

## Acknowledgments

- Technical indicators: TA-Lib, pandas-ta
- Data sources: Yahoo Finance, NSE
- APIs: Upstox, Angel One SmartAPI

---

**Remember**: Trading involves risk. Never trade with money you cannot afford to lose. Always test thoroughly before live trading.
