#!/bin/bash
# Cron job setup for scheduled trading

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up cron jobs for trading bot..."

# Create cron job file
CRON_FILE="/tmp/trading_bot_cron"

# Market hours: 9:15 AM to 3:30 PM IST (check every 5 minutes during market hours)
cat > "$CRON_FILE" <<EOF
# Trading bot - Run every 5 minutes during market hours (9:15 AM - 3:30 PM IST)
*/5 9-15 * * 1-5 cd $PROJECT_DIR && source venv/bin/activate && python live_trading.py --provider upstox --symbols RELIANCE TCS INFY >> logs/cron.log 2>&1

# Daily backtest at 6 PM
0 18 * * 1-5 cd $PROJECT_DIR && source venv/bin/activate && python backtest.py --symbol RELIANCE --start-date $(date -d '20 years ago' +%Y-%m-%d) >> logs/backtest_cron.log 2>&1
EOF

# Install cron job
crontab "$CRON_FILE"

echo "Cron jobs installed successfully!"
echo "View cron jobs: crontab -l"
echo "Remove cron jobs: crontab -r"
