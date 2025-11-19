#!/bin/bash
# AWS EC2 deployment script

set -e

echo "Deploying Indian Stock Trading Bot to AWS EC2..."

# Update system
sudo yum update -y

# Install Python 3.8+
sudo yum install -y python3 python3-pip git

# Install TA-Lib dependencies
sudo yum install -y gcc make wget
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ~

# Clone or copy project
# git clone <your-repo-url> trading-bot
# cd trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p logs historical_data backtest_results data

# Setup systemd service
sudo tee /etc/systemd/system/trading-bot.service > /dev/null <<EOF
[Unit]
Description=Indian Stock Trading Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/trading-bot
Environment="PATH=/home/ec2-user/trading-bot/venv/bin"
ExecStart=/home/ec2-user/trading-bot/venv/bin/python live_trading.py --provider upstox --symbols RELIANCE TCS INFY
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

echo "Deployment complete!"
echo "Check status: sudo systemctl status trading-bot"
echo "View logs: sudo journalctl -u trading-bot -f"
