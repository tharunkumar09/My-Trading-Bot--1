#!/bin/bash

################################################################################
# Local Deployment Script
# Deploys the trading bot on a local machine
################################################################################

set -e

echo "=================================="
echo "Trading Bot - Local Deployment"
echo "=================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ Pip upgraded${NC}"

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install TA-Lib (if not already installed)
echo -e "\n${YELLOW}Checking TA-Lib...${NC}"
if python -c "import talib" &> /dev/null; then
    echo -e "${GREEN}✓ TA-Lib already installed${NC}"
else
    echo -e "${YELLOW}Installing TA-Lib...${NC}"
    echo "Note: This may require system dependencies."
    echo "On Ubuntu/Debian: sudo apt-get install ta-lib"
    echo "On macOS: brew install ta-lib"
    pip install ta-lib-binary || echo -e "${YELLOW}⚠ TA-Lib installation may require manual setup${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p data/historical
mkdir -p data/logs
mkdir -p data/backtest_results
echo -e "${GREEN}✓ Directories created${NC}"

# Setup configuration
echo -e "\n${YELLOW}Setting up configuration...${NC}"
if [ ! -f "config/.env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        echo -e "${YELLOW}⚠ Please edit config/.env with your API credentials${NC}"
    else
        echo -e "${RED}✗ config/.env.example not found${NC}"
    fi
else
    echo -e "${GREEN}✓ Configuration file exists${NC}"
fi

# Run tests (optional)
echo -e "\n${YELLOW}Running tests...${NC}"
if [ -d "tests" ]; then
    python -m pytest tests/ -v || echo -e "${YELLOW}⚠ Some tests failed${NC}"
else
    echo -e "${YELLOW}⚠ No tests directory found${NC}"
fi

# Display status
echo -e "\n${GREEN}=================================="
echo "✓ Deployment Complete!"
echo "==================================${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Edit config/.env with your API credentials"
echo "2. Review config/config.yaml for strategy parameters"
echo "3. Run a backtest: python backtest_runner.py --symbol RELIANCE"
echo "4. Start the bot: python -m src.trading_bot"

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo "  • Activate venv: source venv/bin/activate"
echo "  • Run backtest: python backtest_runner.py --help"
echo "  • Start bot: python -m src.trading_bot"
echo "  • View logs: tail -f data/logs/trading_bot.log"

echo ""
