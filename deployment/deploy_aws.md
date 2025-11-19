# AWS Deployment Guide

## Deploying Trading Bot on AWS EC2

This guide will help you deploy the trading bot on an AWS EC2 instance.

### Prerequisites

- AWS Account
- AWS CLI installed and configured
- SSH key pair for EC2 access

### Step 1: Launch EC2 Instance

1. **Log in to AWS Console** and navigate to EC2

2. **Launch a new instance:**
   - **AMI:** Ubuntu Server 22.04 LTS
   - **Instance Type:** t3.small (minimum) or t3.medium (recommended)
   - **Storage:** 20 GB SSD
   - **Security Group:** Allow SSH (port 22) from your IP

3. **Create/Select Key Pair** for SSH access

### Step 2: Connect to Instance

```bash
# Replace with your key and instance details
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-instance-ip
```

### Step 3: Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies for TA-Lib
sudo apt-get install -y build-essential wget
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ~

# Install Git
sudo apt-get install -y git
```

### Step 4: Clone and Setup Trading Bot

```bash
# Clone repository (or upload your code)
git clone <your-repo-url> trading-bot
cd trading-bot

# Or upload via SCP:
# scp -i your-key.pem -r /local/path/to/trading-bot ubuntu@your-instance-ip:~

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure the Bot

```bash
# Setup environment variables
cp config/.env.example config/.env
nano config/.env  # Edit with your API credentials

# Review configuration
nano config/config.yaml
```

### Step 6: Setup Systemd Service

Create a systemd service file to run the bot automatically:

```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Add the following content:

```ini
[Unit]
Description=Algorithmic Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trading-bot
Environment="PATH=/home/ubuntu/trading-bot/venv/bin"
ExecStart=/home/ubuntu/trading-bot/venv/bin/python -m src.trading_bot
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/trading-bot/data/logs/trading_bot.log
StandardError=append:/home/ubuntu/trading-bot/data/logs/trading_bot_error.log

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable trading-bot

# Start the service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
journalctl -u trading-bot -f
```

### Step 7: Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/trading-bot
```

Add:

```
/home/ubuntu/trading-bot/data/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload trading-bot > /dev/null 2>&1 || true
    endscript
}
```

### Step 8: Setup Monitoring (Optional)

Install and configure CloudWatch agent:

```bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure CloudWatch agent to monitor logs
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### Step 9: Security Hardening

```bash
# Setup firewall
sudo ufw allow OpenSSH
sudo ufw enable

# Install fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Restrict file permissions
chmod 600 config/.env
chmod 700 data/
```

### Step 10: Backup Configuration

Create automated backups using cron:

```bash
crontab -e
```

Add:

```bash
# Daily backup at 2 AM
0 2 * * * tar -czf ~/backups/trading-bot-$(date +\%Y\%m\%d).tar.gz ~/trading-bot/config ~/trading-bot/data/logs
```

### Managing the Bot

```bash
# Start the bot
sudo systemctl start trading-bot

# Stop the bot
sudo systemctl stop trading-bot

# Restart the bot
sudo systemctl restart trading-bot

# View logs
tail -f data/logs/trading_bot.log

# View systemd logs
journalctl -u trading-bot -f

# Check status
sudo systemctl status trading-bot
```

### Cost Optimization

1. **Use Reserved Instances** for long-term deployment
2. **Setup Auto-Stop/Start** during non-market hours
3. **Use Spot Instances** for backtesting (not for live trading)
4. **Monitor CloudWatch** metrics to optimize instance size

### Troubleshooting

**Bot won't start:**
```bash
# Check logs
journalctl -u trading-bot -n 50
tail -100 data/logs/trading_bot_error.log

# Test manually
source venv/bin/activate
python -m src.trading_bot
```

**Permission issues:**
```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu ~/trading-bot
chmod +x ~/trading-bot/venv/bin/*
```

**Memory issues:**
```bash
# Check memory usage
free -h
htop

# Consider upgrading to a larger instance type
```

### Auto-Start/Stop Script (Cost Saving)

Create a Lambda function to start/stop EC2 during market hours:

```python
import boto3
from datetime import datetime
import pytz

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-1')
    instance_id = 'your-instance-id'
    
    # IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    
    # Market hours: 9:00 AM - 4:00 PM IST
    if 9 <= current_time.hour < 16 and current_time.weekday() < 5:
        # Start instance
        ec2.start_instances(InstanceIds=[instance_id])
    else:
        # Stop instance
        ec2.stop_instances(InstanceIds=[instance_id])
    
    return {'statusCode': 200}
```

Schedule this Lambda to run every hour using CloudWatch Events.

### Monitoring Dashboard

Use CloudWatch to monitor:
- CPU utilization
- Memory usage
- Disk I/O
- Network traffic
- Custom metrics (trades, P&L)

### Backup Strategy

1. **Automated S3 Backups:**
   ```bash
   aws s3 sync ~/trading-bot/data/logs s3://your-bucket/logs/
   aws s3 sync ~/trading-bot/config s3://your-bucket/config/
   ```

2. **EBS Snapshots:**
   - Create daily snapshots of your EBS volume
   - Retain 7 days of snapshots

---

## Alternative: AWS Lightsail (Simpler Option)

For a simpler deployment, use AWS Lightsail:

1. Create a Lightsail instance (Ubuntu, $5-$10/month)
2. Follow the same setup steps as EC2
3. Use Lightsail's built-in monitoring and snapshots

---

## Support

For issues or questions, refer to:
- AWS Documentation: https://docs.aws.amazon.com/
- Trading Bot README: /workspace/README.md
