#!/bin/bash

# Quick Start Script for Trading Bot
# This script helps set up the trading bot quickly

set -e

echo "=========================================="
echo "Trading Bot Quick Start"
echo "=========================================="

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 not found. Please install Python 3.8+"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for TA-Lib
echo "Checking TA-Lib installation..."
python3 -c "import talib" 2>/dev/null || {
    echo "WARNING: TA-Lib not installed"
    echo "Please install TA-Lib:"
    echo "  Ubuntu/Debian: sudo apt-get install ta-lib && pip install TA-Lib"
    echo "  macOS: brew install ta-lib && pip install TA-Lib"
    echo "  Windows: Download from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib"
}

# Create necessary directories
echo "Creating directories..."
mkdir -p data logs backtesting

# Setup environment file
if [ ! -f "config/.env" ]; then
    echo "Creating .env file from template..."
    cp config/.env.example config/.env
    echo "Please edit config/.env with your API credentials"
else
    echo ".env file already exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/.env with your API credentials"
echo "2. Download historical data:"
echo "   python download_data.py --symbol RELIANCE --start 2020-01-01 --end 2024-01-01"
echo "3. Run backtest:"
echo "   python run_backtest.py --symbol RELIANCE --start 2020-01-01 --end 2024-01-01"
echo "4. Start trading bot:"
echo "   python trading_bot.py"
echo ""
echo "For more information, see README.md"
