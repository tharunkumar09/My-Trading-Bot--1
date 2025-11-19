# Handling Market Shocks and Unpredictable Events

## Overview

This document addresses how to improve the trading bot to handle sudden market shocks, unpredictable events, and capitalize on opportunities arising from:
- Earnings announcements
- Tariffs and trade wars
- Geopolitical events (wars, conflicts)
- Government policies and regulations
- Sector bailouts
- New developments and innovations
- Black swan events

## Current Limitations

The current strategy is purely technical analysis-based and may not adapt well to:
1. **Fundamental Shocks**: Earnings surprises, management changes
2. **Macro Events**: Policy changes, economic data releases
3. **Sentiment Shifts**: News-driven volatility
4. **Liquidity Crises**: Flash crashes, circuit breakers
5. **Sector Rotation**: Policy-driven sector movements

## Recommended Improvements

### 1. News and Sentiment Analysis

**Integration Points:**
- News APIs (NewsAPI, Alpha Vantage News)
- Social media sentiment (Twitter, Reddit)
- Economic calendar integration
- Earnings calendar tracking

**Implementation:**
```python
# Add to requirements.txt
newsapi-python==0.2.7
tweepy==4.14.0
vaderSentiment==3.3.2
```

**Strategy Modifications:**
- Reduce position sizes before major announcements
- Exit positions on negative news
- Enter positions on positive sentiment shifts
- Filter trades based on news sentiment score

### 2. Volatility-Based Position Sizing

**Concept:**
- Use VIX or India VIX (VIX) to adjust position sizes
- Reduce exposure during high volatility periods
- Increase exposure during low volatility periods

**Implementation:**
```python
def calculate_volatility_adjusted_size(base_size, current_volatility, avg_volatility):
    volatility_ratio = current_volatility / avg_volatility
    if volatility_ratio > 1.5:  # High volatility
        return base_size * 0.5  # Reduce size by 50%
    elif volatility_ratio < 0.7:  # Low volatility
        return base_size * 1.2  # Increase size by 20%
    return base_size
```

### 3. Circuit Breaker Detection

**Implementation:**
- Monitor for circuit breakers (upper/lower limits)
- Halt trading when circuit breakers are hit
- Implement gap detection (overnight gaps > 5%)

```python
def check_circuit_breaker(current_price, previous_close):
    change_pct = abs((current_price - previous_close) / previous_close) * 100
    if change_pct >= 10:  # Upper circuit
        return "UPPER_CIRCUIT"
    elif change_pct <= -10:  # Lower circuit
        return "LOWER_CIRCUIT"
    return "NORMAL"
```

### 4. Earnings Calendar Integration

**Data Sources:**
- NSE earnings calendar
- Company investor relations pages
- Financial data APIs

**Strategy:**
- Avoid new positions 2 days before earnings
- Exit positions before earnings if uncertain
- Use earnings surprise data for entry signals
- Post-earnings momentum trading

### 5. Sector Rotation Detection

**Indicators:**
- Relative strength of sectors vs NIFTY
- Policy announcements affecting sectors
- Government spending patterns

**Implementation:**
```python
def detect_sector_rotation(sector_performance, nifty_performance):
    relative_strength = sector_performance / nifty_performance
    if relative_strength > 1.1:  # Sector outperforming
        return "BULLISH"
    elif relative_strength < 0.9:  # Sector underperforming
        return "BEARISH"
    return "NEUTRAL"
```

### 6. Macro Economic Indicators

**Key Indicators:**
- GDP growth rates
- Inflation (CPI, WPI)
- Interest rates (Repo rate)
- Currency movements (USD/INR)
- Crude oil prices
- FII/DII flows

**Integration:**
- Adjust strategy based on macro environment
- Reduce exposure during economic uncertainty
- Increase exposure during favorable macro conditions

### 7. Dynamic Stop Loss Adjustment

**Volatility-Based Stops:**
- Wider stops during high volatility
- Tighter stops during low volatility
- ATR-based stop loss (2x ATR)

**Event-Based Stops:**
- Tighter stops before major events
- Wider stops during earnings season
- Trailing stops during trending markets

### 8. Liquidity Monitoring

**Metrics:**
- Average daily volume
- Bid-ask spread
- Order book depth

**Strategy:**
- Avoid low liquidity stocks
- Reduce position sizes in illiquid stocks
- Exit positions if liquidity dries up

### 9. Multi-Timeframe Analysis

**Implementation:**
- Check higher timeframes (weekly, monthly) for trend
- Use daily signals for entries
- Confirm with multiple timeframes

### 10. Regime Detection

**Market Regimes:**
- Bull market
- Bear market
- Sideways/consolidation
- High volatility
- Low volatility

**Strategy Adaptation:**
- Different strategies for different regimes
- Reduce trading in unfavorable regimes
- Increase exposure in favorable regimes

## Enhanced Prompt for Market Shock Handling

Here's an improved version of the original prompt that addresses market shocks:

```
You are an expert algorithmic trading system designer specializing in Indian stock markets.

Build a complete algorithmic trading bot with the following ENHANCED requirements:

CORE REQUIREMENTS (same as before):
1. Use Python with Upstox API (preferred) or Angel One SmartAPI
2. Include authentication, live data, order placement, position management, logging
3. Technical indicators: RSI (14), MACD (12, 26, 9), Supertrend (10, 3), 200-Day EMA
4. Backtest on 20+ years of historical data
5. Risk management: position sizing, stop losses, trailing SL

ENHANCED REQUIREMENTS FOR MARKET SHOCKS:

6. NEWS & SENTIMENT INTEGRATION:
   - Integrate NewsAPI or similar for real-time news
   - Implement sentiment analysis (VADER or transformer-based)
   - Track earnings calendar and economic events
   - Adjust position sizes based on news sentiment (-50% on negative news, +20% on positive)
   - Exit positions on major negative news events

7. VOLATILITY MANAGEMENT:
   - Integrate India VIX data
   - Implement ATR-based position sizing
   - Reduce exposure when VIX > 20 (high volatility)
   - Use volatility-adjusted stop losses (2x ATR for stops)

8. CIRCUIT BREAKER & GAP DETECTION:
   - Detect upper/lower circuit breakers (10% limit)
   - Halt trading when circuits are hit
   - Detect overnight gaps > 5%
   - Implement gap-fill strategies

9. MACRO ECONOMIC INTEGRATION:
   - Track RBI repo rate changes
   - Monitor FII/DII flows
   - Track USD/INR movements
   - Integrate GDP, inflation data
   - Adjust strategy based on macro environment

10. SECTOR ROTATION DETECTION:
    - Calculate relative strength of sectors vs NIFTY
    - Identify policy-driven sector movements
    - Implement sector momentum strategies
    - Capitalize on government policy announcements

11. EARNINGS CALENDAR INTEGRATION:
    - Avoid new positions 2 days before earnings
    - Exit uncertain positions before earnings
    - Use earnings surprise data for entries
    - Post-earnings momentum trading

12. REGIME DETECTION:
    - Identify market regimes (bull/bear/sideways)
    - Adapt strategy parameters per regime
    - Reduce trading in unfavorable regimes
    - Use different indicators for different regimes

13. LIQUIDITY MONITORING:
    - Track average daily volume
    - Monitor bid-ask spreads
    - Avoid low liquidity stocks (< 1L volume)
    - Exit if liquidity dries up

14. MULTI-TIMEFRAME CONFIRMATION:
    - Check weekly/monthly trends
    - Confirm daily signals with higher timeframes
    - Use multiple timeframe alignment for entries

15. EMERGENCY PROTOCOLS:
    - Implement "panic exit" on sudden drops > 5%
    - Circuit breaker detection and halt
    - Maximum drawdown limits (stop trading at -10% daily)
    - Automatic position reduction on high volatility

DATA SOURCES TO INTEGRATE:
- NewsAPI (newsapi.org) for news
- Alpha Vantage for economic data
- NSE website for earnings calendar
- India VIX data from NSE
- FII/DII data from SEBI
- RBI website for policy rates

BACKTESTING ENHANCEMENTS:
- Include news events in backtest (mark dates of major events)
- Test strategy during different market regimes
- Stress test with historical crashes (2008, 2020)
- Test with different volatility environments
- Include transaction costs and slippage

RISK MANAGEMENT ENHANCEMENTS:
- Dynamic position sizing based on volatility
- Event-based stop loss adjustments
- Maximum daily loss limits
- Sector concentration limits
- Correlation-based position limits

OUTPUT REQUIREMENTS:
- All previous outputs PLUS:
- News sentiment dashboard
- Volatility-adjusted position sizes
- Event calendar integration
- Regime detection indicators
- Macro economic overlay
- Emergency protocol logs

DEPLOYMENT:
- Same as before, but add:
- News API key configuration
- Economic data API keys
- Real-time monitoring dashboard
- Alert system for major events
```

## Implementation Priority

**Phase 1 (Critical):**
1. Volatility-based position sizing
2. Circuit breaker detection
3. Dynamic stop loss (ATR-based)
4. Maximum daily loss limits

**Phase 2 (Important):**
5. News sentiment integration
6. Earnings calendar
7. Liquidity monitoring
8. Multi-timeframe confirmation

**Phase 3 (Advanced):**
9. Sector rotation detection
10. Macro economic integration
11. Regime detection
12. Advanced sentiment analysis

## Example: Earnings Announcement Handler

```python
class EarningsHandler:
    def __init__(self):
        self.earnings_calendar = {}
        self.load_earnings_calendar()
    
    def should_avoid_trade(self, symbol, current_date):
        """Check if we should avoid trading before earnings"""
        if symbol in self.earnings_calendar:
            earnings_date = self.earnings_calendar[symbol]
            days_before = (earnings_date - current_date).days
            if 0 <= days_before <= 2:
                return True, f"Earnings in {days_before} days"
        return False, ""
    
    def post_earnings_signal(self, symbol, earnings_data):
        """Generate signal based on earnings results"""
        surprise = earnings_data.get('surprise', 0)
        if surprise > 0.05:  # 5% positive surprise
            return "BUY"
        elif surprise < -0.05:  # 5% negative surprise
            return "SELL"
        return "HOLD"
```

## Resources

1. **News APIs:**
   - NewsAPI: https://newsapi.org/
   - Alpha Vantage News: https://www.alphavantage.co/documentation/#news-sentiment

2. **Economic Data:**
   - RBI Database: https://www.rbi.org.in/scripts/Statistics.aspx
   - NSE Data: https://www.nseindia.com/
   - SEBI Data: https://www.sebi.gov.in/

3. **Sentiment Analysis:**
   - VADER Sentiment: https://github.com/cjhutto/vaderSentiment
   - Transformers (Hugging Face): https://huggingface.co/

4. **Volatility Data:**
   - India VIX: Available on NSE website
   - Historical VIX data: NSE historical data

## Conclusion

By integrating these enhancements, the trading bot can:
- **Adapt** to changing market conditions
- **Protect** capital during volatile periods
- **Capitalize** on opportunities from news and events
- **Reduce** risk during uncertain times
- **Improve** overall risk-adjusted returns

Remember: No strategy is perfect, but a robust system that adapts to market conditions is more likely to succeed long-term.
