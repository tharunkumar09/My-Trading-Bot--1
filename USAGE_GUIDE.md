# Trading Bot Usage Guide

A step-by-step guide to using the algorithmic trading bot.

## Table of Contents
1. [First Time Setup](#first-time-setup)
2. [Running Backtests](#running-backtests)
3. [Paper Trading](#paper-trading)
4. [Live Trading](#live-trading)
5. [Monitoring](#monitoring)
6. [Common Tasks](#common-tasks)
7. [FAQ](#faq)

---

## First Time Setup

### 1. Install Dependencies

```bash
# Clone the repository
cd trading-bot

# Run deployment script (recommended)
chmod +x deployment/deploy_local.sh
./deployment/deploy_local.sh

# Or install manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get API Credentials

**Upstox (Recommended):**
1. Go to https://account.upstox.com/developer/apps
2. Click "Create App"
3. Fill in app details:
   - Name: My Trading Bot
   - Redirect URI: https://127.0.0.1:8080
4. Copy API Key and API Secret

**Angel One:**
1. Log into Angel One
2. Go to SmartAPI section
3. Generate API key
4. Note down Client ID and Password

**NewsAPI (for event monitoring):**
1. Go to https://newsapi.org/
2. Sign up for free
3. Get API key (free tier: 1000 requests/day)

### 3. Configure Credentials

```bash
# Copy template
cp config/.env.example config/.env

# Edit with your credentials
nano config/.env
```

Add your keys:
```bash
UPSTOX_API_KEY=your_key_here
UPSTOX_API_SECRET=your_secret_here
NEWSAPI_KEY=your_newsapi_key_here
```

### 4. Review Configuration

```bash
nano config/config.yaml
```

Key settings to review:
- `api.provider`: upstox or angelone
- `risk_management.max_portfolio_risk`: 0.02 (2% per trade)
- `universe.stocks`: List of stocks to trade
- `live_trading.enabled`: false (start with backtesting)

---

## Running Backtests

### Basic Backtest

Test your strategy on historical data before risking real money.

```bash
# Activate environment
source venv/bin/activate

# Backtest a single stock (default: 20 years)
python backtest_runner.py --symbol RELIANCE

# Custom time period
python backtest_runner.py --symbol TCS --years 10

# Backtest without plots (faster)
python backtest_runner.py --symbol INFY --no-plot
```

### Expected Output

```
==================================================================
BACKTEST RESULTS: RELIANCE
==================================================================
Period: 2003-01-01 to 2023-12-31 (20.00 years)
------------------------------------------------------------------

RETURNS:
  Initial Capital:     ₹    1,000,000.00
  Final Capital:       ₹    3,456,789.00
  Total Return:        ₹    2,456,789.00 (245.68%)
  CAGR:                   6.42%

RISK METRICS:
  Sharpe Ratio:          1.23
  Sortino Ratio:         1.67
  Max Drawdown:         22.45%

TRADE STATISTICS:
  Total Trades:           198
  Winning Trades:         118
  Losing Trades:           80
  Win Rate:             59.60%
  Profit Factor:          1.89
  ...
```

### Analyze Results

**Good Strategy Indicators:**
- ✅ CAGR > 8% (beats inflation + fixed deposits)
- ✅ Sharpe Ratio > 1.0 (risk-adjusted returns)
- ✅ Max Drawdown < 30% (survivable losses)
- ✅ Win Rate > 50%
- ✅ Profit Factor > 1.5

**Red Flags:**
- ❌ CAGR < 5%
- ❌ Sharpe Ratio < 0.5
- ❌ Max Drawdown > 40%
- ❌ Profit Factor < 1.0

### Backtest Multiple Stocks

```bash
# Backtest all stocks in config
python backtest_runner.py --all

# This generates a summary CSV
# Location: data/backtest_results/summary_YYYYMMDD_HHMMSS.csv
```

---

## Paper Trading

Test your bot in real market conditions without risking money.

### 1. Set Paper Trading Mode

Edit `config/config.yaml`:
```yaml
live_trading:
  enabled: false    # Don't use real orders yet
  mode: "paper"     # Simulate orders
```

### 2. Authenticate

```bash
python -c "from src.api.upstox_api import UpstoxAPI; api = UpstoxAPI('YOUR_KEY', 'YOUR_SECRET'); print(api.get_login_url())"
```

Open the URL in browser, login, and copy the authorization code from redirect URL.

### 3. Start Paper Trading

```bash
source venv/bin/activate
python -m src.trading_bot
```

### 4. What Happens

The bot will:
1. ✅ Connect to broker API
2. ✅ Fetch real-time market data
3. ✅ Calculate indicators
4. ✅ Generate signals
5. ⚠️ **Simulate** order execution (no real orders)
6. ✅ Track paper portfolio
7. ✅ Log all actions

### 5. Monitor Paper Trading

```bash
# Watch logs in real-time
tail -f data/logs/trading_bot.log

# View trades
cat data/logs/trades.csv

# Check last 50 log entries
tail -50 data/logs/trading_bot.log
```

**Expected Behavior:**
```
2024-11-19 09:30:15 | INFO | Trading cycle started
2024-11-19 09:30:16 | INFO | Scanning for opportunities...
2024-11-19 09:30:45 | INFO | Opportunity found: RELIANCE @ ₹2,345.50
2024-11-19 09:30:46 | INFO | [PAPER] Would place order: BUY 85 RELIANCE @ ₹2,345.50
2024-11-19 09:30:46 | INFO | Position added: RELIANCE
```

### 6. Run for at Least 1-2 Weeks

- Monitor daily performance
- Check if strategy behaves as expected
- Verify risk management works
- Ensure no errors occur

---

## Live Trading

⚠️ **WARNING**: Live trading involves real money. Only proceed after thorough paper trading.

### Pre-Flight Checklist

Before enabling live trading:

- [ ] Backtested strategy (>1000 trades)
- [ ] Paper traded for 2+ weeks
- [ ] Reviewed and understood all settings
- [ ] Set up alerts (email/Telegram)
- [ ] Tested with small capital first
- [ ] Have emergency stop plan
- [ ] Understand tax implications
- [ ] Comfortable with potential losses

### 1. Enable Live Trading

Edit `config/config.yaml`:
```yaml
live_trading:
  enabled: true     # Enable live trading
  mode: "live"      # Use real orders
```

### 2. Set Conservative Parameters

For first live run:
```yaml
risk_management:
  max_portfolio_risk: 0.01      # 1% per trade (conservative)
  max_position_size: 0.05       # 5% per position
  max_open_positions: 2         # Max 2 positions

universe:
  stocks:
    - "RELIANCE"                # Start with 1-2 liquid stocks
    - "TCS"
```

### 3. Start with Small Capital

- Start with ₹50,000 - ₹1,00,000
- Don't risk more than you can afford to lose
- Treat first month as live testing

### 4. Start the Bot

```bash
source venv/bin/activate
python -m src.trading_bot
```

### 5. Monitor Closely

**First Day:**
- Check every 30 minutes
- Verify orders are placed correctly
- Ensure stop losses are working

**First Week:**
- Check 2-3 times daily
- Review end-of-day logs
- Monitor P&L

**First Month:**
- Daily check-ins
- Weekly performance review
- Adjust parameters if needed

---

## Monitoring

### Real-Time Monitoring

```bash
# Live logs
tail -f data/logs/trading_bot.log

# Today's trades only
cat data/logs/trades.csv | grep $(date +%Y-%m-%d)

# Error logs
tail -f data/logs/trading_bot_error.log
```

### Performance Metrics

```bash
# Generate performance report
python -c "
import pandas as pd
trades = pd.read_csv('data/logs/trades.csv')
print(f'Total Trades: {len(trades)}')
print(f'Total P&L: ₹{trades[\"pnl\"].sum():,.2f}')
print(f'Win Rate: {(trades[\"pnl\"] > 0).sum() / len(trades) * 100:.2f}%')
"
```

### Alerts

**Email Alerts:**
Edit `config/.env`:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

**Telegram Alerts:**
1. Create a bot: https://t.me/BotFather
2. Get bot token
3. Get your chat ID: https://t.me/userinfobot
4. Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Common Tasks

### Stop the Bot

```bash
# If running in foreground
Ctrl + C

# If running as service
sudo systemctl stop trading-bot

# Kill all instances
pkill -f "python -m src.trading_bot"
```

### Restart the Bot

```bash
# Foreground
python -m src.trading_bot

# As service
sudo systemctl restart trading-bot
```

### Close All Positions Manually

```python
# Run Python script
python -c "
from src.api.upstox_api import UpstoxAPI
from config.config_loader import get_config

config = get_config()
api_config = config.get_api_config()
api = UpstoxAPI(api_config['api_key'], api_config['api_secret'])
api.authenticate()  # Follow auth flow

positions = api.get_positions()
for pos in positions:
    if pos['quantity'] != 0:
        api.close_position(pos['symbol'], 'NSE', pos['quantity'])
        print(f'Closed {pos[\"symbol\"]}')
"
```

### Update Configuration

```bash
# Edit config
nano config/config.yaml

# Restart bot for changes to take effect
sudo systemctl restart trading-bot
```

### View Performance Dashboard

```bash
# Generate HTML report (if implemented)
python -c "
from src.utils.dashboard import generate_dashboard
generate_dashboard('data/logs/trades.csv', 'dashboard.html')
"

# Open in browser
xdg-open dashboard.html
```

### Backup Data

```bash
# Create backup
tar -czf backup_$(date +%Y%m%d).tar.gz config/ data/

# Restore from backup
tar -xzf backup_20241119.tar.gz
```

---

## FAQ

### Q: How much capital do I need?

**A**: Minimum ₹50,000 for meaningful diversification. Ideal: ₹2-5 lakhs.

### Q: What returns can I expect?

**A**: Historical backtests show 8-12% CAGR. No guarantees. Expect 15-25% drawdowns.

### Q: Should I run the bot 24/7?

**A**: Bot only trades during market hours (9:15 AM - 3:30 PM). Can run 24/7 but will idle outside market hours.

### Q: What if the bot stops working?

**A**: 
1. Check logs: `tail -50 data/logs/trading_bot_error.log`
2. Manually close positions if needed
3. Restart bot
4. If persists, disable live trading and debug

### Q: How often should I update the strategy?

**A**: Review monthly. Don't over-optimize. Good strategies work for years.

### Q: What are the costs?

**A**:
- Brokerage: ₹20 per order (Upstox/Zerodha)
- STT: 0.1% on sell side
- Slippage: 0.05-0.1% per trade
- **Total cost**: ~0.2-0.3% per round trip

### Q: Is this legal?

**A**: Yes. Algorithmic trading is legal in India. No SEBI approval needed for personal use.

### Q: What about taxes?

**A**:
- **STCG** (< 1 year): 15% on profits
- **LTCG** (> 1 year): 10% on profits > ₹1 lakh
- Maintain detailed trade logs for tax filing

### Q: Can I customize the strategy?

**A**: Yes! Edit `src/strategies/momentum_strategy.py`. Test thoroughly before deploying.

### Q: What if I lose money?

**A**: 
- Normal. Every strategy has losses.
- Stick to risk management (max 2% per trade)
- Don't revenge trade
- Review strategy if consistent losses > 1 month

### Q: Should I use margin/leverage?

**A**: No. Start with cash (delivery). Leverage amplifies losses.

---

## Support

**Need help?**
- Check logs first
- Review configuration
- Search closed GitHub issues
- Open new issue with:
  - Error message
  - Log snippets
  - Configuration (remove sensitive data)

---

**Happy Trading! 📈**

Remember: The best strategy is the one you can stick to. Start small, learn continuously, and never risk more than you can afford to lose.
