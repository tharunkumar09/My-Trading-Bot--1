# Deployment Guide

This guide covers how to deploy the algorithmic trading bot on various platforms.

## Table of Contents
1. [Local Machine Setup](#local-machine-setup)
2. [Linux VPS Deployment](#linux-vps-deployment)
3. [AWS EC2 Deployment](#aws-ec2-deployment)
4. [Azure VM Deployment](#azure-vm-deployment)
5. [Scheduling with Cron](#scheduling-with-cron)
6. [Running as a Service](#running-as-a-service)
7. [Monitoring and Logging](#monitoring-and-logging)

## Local Machine Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Installation Steps

1. **Clone or navigate to the project directory:**
```bash
cd /path/to/trading-bot
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install TA-Lib (required for technical indicators):**
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib
pip install TA-Lib

# macOS
brew install ta-lib
pip install TA-Lib

# Windows - Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# Then: pip install TA_Lib-0.4.xx-cp3x-cp3x-win_amd64.whl
```

5. **Configure environment variables:**
```bash
cp config/.env.example config/.env
# Edit config/.env with your API credentials
```

6. **Test the setup:**
```bash
python run_backtest.py --symbol RELIANCE --start 2020-01-01 --end 2024-01-01
```

## Linux VPS Deployment

### Using systemd Service

1. **Create service file:**
```bash
sudo nano /etc/systemd/system/trading-bot.service
```

2. **Add the following content:**
```ini
[Unit]
Description=Algorithmic Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/trading-bot
Environment="PATH=/path/to/trading-bot/venv/bin"
ExecStart=/path/to/trading-bot/venv/bin/python /path/to/trading-bot/trading_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

3. **Enable and start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

4. **Check status:**
```bash
sudo systemctl status trading-bot
```

5. **View logs:**
```bash
sudo journalctl -u trading-bot -f
```

## AWS EC2 Deployment

### Step 1: Launch EC2 Instance

1. Launch an EC2 instance (Ubuntu 22.04 LTS recommended)
2. Security Group: Allow SSH (port 22) and any required ports
3. Choose instance type (t3.micro for testing, t3.small or larger for production)

### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install python3 python3-pip python3-venv git -y
sudo apt-get install ta-lib -y

# Clone or upload your project
git clone your-repo-url
cd trading-bot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install TA-Lib

# Configure environment
cp config/.env.example config/.env
nano config/.env  # Add your credentials
```

### Step 3: Setup systemd Service

Follow the Linux VPS deployment steps above.

### Step 4: Setup CloudWatch Logs (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure CloudWatch
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -c file:cloudwatch-config.json -s
```

## Azure VM Deployment

### Step 1: Create VM

1. Create Ubuntu VM in Azure Portal
2. Configure Network Security Group (allow SSH)
3. Connect via SSH

### Step 2: Setup (Same as AWS)

Follow AWS EC2 deployment steps 2-3.

### Step 3: Azure Monitor (Optional)

```bash
# Install Azure Monitor agent
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az extension add --name log-analytics
```

## Scheduling with Cron

For scheduled tasks (e.g., daily backtests):

1. **Edit crontab:**
```bash
crontab -e
```

2. **Add entries:**
```bash
# Run backtest daily at 6 PM
0 18 * * * cd /path/to/trading-bot && /path/to/venv/bin/python run_backtest.py --symbol RELIANCE >> logs/cron.log 2>&1

# Restart bot daily at 9 AM (before market open)
0 9 * * 1-5 systemctl restart trading-bot

# Clean old logs weekly
0 0 * * 0 find /path/to/trading-bot/logs -name "*.log" -mtime +30 -delete
```

## Running as a Background Service

### Using nohup

```bash
nohup python trading_bot.py > logs/bot.log 2>&1 &
```

### Using screen

```bash
screen -S trading-bot
python trading_bot.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r trading-bot
```

### Using tmux

```bash
tmux new -s trading-bot
python trading_bot.py
# Press Ctrl+B then D to detach
# Reattach with: tmux attach -t trading-bot
```

## Monitoring and Logging

### Log Files

- `logs/trading_bot.log` - Main application log
- `logs/errors.log` - Error log
- `logs/trades.json` - Trade history

### Monitoring Script

Create `monitor_bot.py`:

```python
import subprocess
import sys
from pathlib import Path

def check_bot_status():
    """Check if bot is running."""
    result = subprocess.run(['pgrep', '-f', 'trading_bot.py'], 
                          capture_output=True)
    return result.returncode == 0

if __name__ == "__main__":
    if not check_bot_status():
        print("Bot is not running!")
        sys.exit(1)
    else:
        print("Bot is running")
```

### Health Check Endpoint (Optional)

Add to `trading_bot.py`:

```python
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy', 'running': bot.is_running}
```

## Security Best Practices

1. **Never commit `.env` file to git**
2. **Use environment variables for sensitive data**
3. **Restrict file permissions:**
```bash
chmod 600 config/.env
chmod 700 logs/
```

4. **Use SSH keys instead of passwords**
5. **Enable firewall:**
```bash
sudo ufw allow 22/tcp
sudo ufw enable
```

6. **Regular updates:**
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

## Troubleshooting

### Bot not starting
- Check logs: `tail -f logs/trading_bot.log`
- Verify API credentials in `.env`
- Check market hours

### Connection errors
- Verify internet connectivity
- Check API endpoint status
- Review rate limiting settings

### Import errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version`

## Backup Strategy

1. **Backup configuration:**
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz config/.env logs/trades.json
```

2. **Automated backup (cron):**
```bash
0 2 * * * tar -czf /backups/trading-bot-$(date +\%Y\%m\%d).tar.gz /path/to/trading-bot/config /path/to/trading-bot/logs
```

## Performance Optimization

1. **Use SSD storage for faster I/O**
2. **Allocate sufficient RAM (minimum 2GB)**
3. **Monitor CPU usage during market hours**
4. **Use connection pooling for API calls**
5. **Implement caching for historical data**
