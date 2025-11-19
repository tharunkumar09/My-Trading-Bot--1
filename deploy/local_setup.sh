#!/bin/bash
# Local deployment setup script

set -e

echo "Setting up Indian Stock Trading Bot locally..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Note: TA-Lib requires system libraries
echo "Note: TA-Lib requires system libraries. Install with:"
echo "  Ubuntu/Debian: sudo apt-get install ta-lib"
echo "  macOS: brew install ta-lib"
echo "  Then: pip install TA-Lib"

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p historical_data
mkdir -p backtest_results
mkdir -p data

# Copy environment file
if [ ! -f .env ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env file with your API credentials"
fi

echo "Setup complete!"
echo "Next steps:"
echo "1. Edit .env file with your API credentials"
echo "2. Run backtest: python backtest.py --symbol RELIANCE"
echo "3. Run live trading: python live_trading.py --symbols RELIANCE TCS"
