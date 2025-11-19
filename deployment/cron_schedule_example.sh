#!/bin/bash

################################################################################
# Cron Job Examples for Trading Bot
# Add these to your crontab with: crontab -e
################################################################################

# Run bot during market hours (Monday-Friday, 9:15 AM - 3:30 PM IST)
# Start bot at 9:00 AM
0 9 * * 1-5 cd /home/ubuntu/trading-bot && /home/ubuntu/trading-bot/venv/bin/python -m src.trading_bot >> data/logs/cron.log 2>&1

# Stop bot at 4:00 PM
0 16 * * 1-5 pkill -f "python -m src.trading_bot"

# Daily backtest at 8:00 PM
0 20 * * * cd /home/ubuntu/trading-bot && /home/ubuntu/trading-bot/venv/bin/python backtest_runner.py --symbol RELIANCE >> data/logs/backtest_cron.log 2>&1

# Weekly comprehensive backtest on Sunday at 10:00 AM
0 10 * * 0 cd /home/ubuntu/trading-bot && /home/ubuntu/trading-bot/venv/bin/python backtest_runner.py --all >> data/logs/backtest_weekly.log 2>&1

# Daily log rotation at 11:59 PM
59 23 * * * find /home/ubuntu/trading-bot/data/logs -name "*.log" -mtime +7 -delete

# Daily backup at 1:00 AM
0 1 * * * tar -czf /home/ubuntu/backups/trading-bot-$(date +\%Y\%m\%d).tar.gz /home/ubuntu/trading-bot/config /home/ubuntu/trading-bot/data

# Clean old backups (keep last 14 days)
0 2 * * * find /home/ubuntu/backups -name "trading-bot-*.tar.gz" -mtime +14 -delete

# Monitor bot health every hour
0 * * * * pgrep -f "python -m src.trading_bot" > /dev/null || (echo "Bot is down" | mail -s "Trading Bot Alert" your-email@example.com)

# Sync logs to S3 every 6 hours (if using AWS)
0 */6 * * * aws s3 sync /home/ubuntu/trading-bot/data/logs s3://your-bucket/logs/

# Check disk space daily at 7:00 AM
0 7 * * * df -h /home/ubuntu/trading-bot | mail -s "Disk Space Report" your-email@example.com

################################################################################
# Alternative: Using systemd timers (more modern approach)
################################################################################

# Create timer files in /etc/systemd/system/

# Example: trading-bot-start.timer
#[Unit]
#Description=Start Trading Bot
#
#[Timer]
#OnCalendar=Mon-Fri *-*-* 09:00:00
#Persistent=true
#
#[Install]
#WantedBy=timers.target

# Enable with: sudo systemctl enable trading-bot-start.timer
