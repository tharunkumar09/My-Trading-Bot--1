# Handling Market Shocks and Unpredictable Events

This document explains how the trading bot handles sudden market events, earnings announcements, policy changes, and other unpredictable situations.

## Overview

Market shocks are sudden, unexpected events that cause significant price movements. Examples include:
- Earnings announcements (positive or negative)
- Government policy changes (tariffs, regulations)
- Geopolitical events (wars, conflicts)
- Sector-specific news (bailouts, mergers)
- Economic data releases
- Natural disasters affecting businesses

## Detection Mechanisms

### 1. Price Shock Detection

The bot monitors for sudden price movements within a short time window:

```python
# Detects >5% price change within 5 minutes
price_shock = detector.detect_price_shock(data, window=5)
```

**Triggers:**
- Price moves >5% in 5 minutes
- Direction (up/down) is tracked
- Magnitude is recorded

### 2. Volume Shock Detection

Unusual trading volume often precedes or accompanies major events:

```python
# Detects 3x average volume
volume_shock = detector.detect_volume_shock(data, window=20)
```

**Triggers:**
- Volume >3x average (configurable)
- Indicates institutional activity or news-driven trading

### 3. Volatility Shock Detection

Sudden increases in volatility indicate uncertainty:

```python
# Detects volatility >5% (configurable)
volatility_shock = detector.detect_volatility_shock(data, window=20)
```

**Triggers:**
- Rolling volatility exceeds threshold
- Indicates market uncertainty

### 4. Gap Detection

Overnight gaps often result from after-hours news:

```python
# Detects >2% gap between close and open
gap = detector.detect_gap(previous_close, current_open)
```

**Triggers:**
- Gap >2% between sessions
- Common after earnings or major announcements

## Adaptive Risk Management

### Risk Multiplier System

When shocks are detected, the bot automatically reduces position sizes:

```python
risk_multiplier = shock_detector.get_adaptive_risk_multiplier(shocks)
# Returns 0.2 to 1.0 based on shock severity
```

**Multiplier Calculation:**
- No shocks: 1.0 (normal risk)
- Price shock: ×0.7
- Volume shock: ×0.8
- Volatility shock: ×0.6
- Gap: ×0.5
- Multiple shocks: Combined reduction
- Minimum: 0.2 (20% of normal position size)

### Position Size Reduction

```python
if shock_detector.should_reduce_position_size(shocks):
    # Reduce position size by risk multiplier
    adjusted_size = base_position_size * risk_multiplier
```

**Triggers for Reduction:**
- 2+ simultaneous shocks
- Extreme price shock (>10%)
- Extreme volatility (>8%)

### Emergency Exit

In extreme conditions, the bot exits all positions:

```python
if shock_detector.should_exit_positions(shocks):
    # Exit all open positions immediately
    exit_all_positions()
```

**Exit Conditions:**
- Price shock >15%
- Volatility >10%
- Gap >5%

## Strategy Modifications During Shocks

### 1. Indicator Filtering

During high volatility, some indicators become less reliable:

```python
# During shocks, require stronger signals
if shocks_detected:
    signal_strength_threshold = 0.7  # vs normal 0.5
    rsi_threshold = 25  # vs normal 30 (stricter)
```

### 2. Trend Filter Enhancement

The 200-day EMA filter becomes more important during shocks:

```python
# Only trade with trend during uncertainty
if shocks_detected and price < ema_200:
    # Skip all buy signals
    return None
```

### 3. Stop Loss Tightening

Stop losses are tightened during volatile periods:

```python
if volatility_shock:
    stop_loss_percentage = 0.015  # 1.5% vs normal 2%
```

## Event-Specific Handling

### Earnings Announcements

**Detection:**
- Volume spike before/after announcement
- Price gap on announcement day
- Increased volatility

**Response:**
- Reduce position size 1 day before
- Tighten stop losses
- Consider exiting before announcement

### Policy Changes

**Detection:**
- Sector-wide price movements
- Volume spikes across related stocks
- News sentiment analysis (if integrated)

**Response:**
- Exit affected sector positions
- Reduce overall portfolio risk
- Wait for clarity before re-entering

### Geopolitical Events

**Detection:**
- Market-wide volatility increase
- Correlation spikes between assets
- Flight to safety (gold, bonds)

**Response:**
- Reduce all position sizes
- Increase cash allocation
- Consider defensive positions

## Implementation in Code

### Main Trading Loop

```python
def run_trading_cycle(self):
    # Fetch data
    data = self.fetch_market_data()
    
    # Detect shocks
    shocks = self.shock_detector.detect_all_shocks(data)
    
    # Adaptive risk
    if self.shock_detector.should_exit_positions(shocks):
        exit_all_positions()
        return
    
    # Reduce position sizes
    risk_multiplier = self.shock_detector.get_adaptive_risk_multiplier(shocks)
    
    # Generate signals with adjusted parameters
    signal = self.strategy.get_signal(data, risk_multiplier=risk_multiplier)
    
    # Trade with reduced size
    if signal:
        position_size = base_size * risk_multiplier
        enter_position(signal, size=position_size)
```

## Configuration

Adjust shock detection parameters in `config/config.py`:

```python
VOLATILITY_THRESHOLD = 0.05  # 5% volatility threshold
VOLUME_SPIKE_MULTIPLIER = 3.0  # 3x average volume
SHOCK_DETECTION_WINDOW = 5  # 5-minute window
```

## Monitoring and Alerts

### Log Shocks

All detected shocks are logged:

```python
logger.warning(f"Price shock detected: {magnitude*100:.2f}% {direction}")
```

### Alert System (Future Enhancement)

Consider integrating:
- Email alerts for extreme shocks
- SMS notifications
- Telegram bot notifications
- Dashboard visualization

## Best Practices

1. **Conservative Approach:**
   - When in doubt, reduce position size
   - Better to miss opportunities than lose capital

2. **Multiple Confirmations:**
   - Require multiple indicators before trading during shocks
   - Wait for volatility to subside

3. **Cash Management:**
   - Maintain cash reserves during uncertain times
   - Don't be fully invested during high volatility

4. **Sector Diversification:**
   - Spread risk across sectors
   - Avoid concentration in shock-prone sectors

5. **Regular Review:**
   - Review shock detection logs weekly
   - Adjust thresholds based on market conditions
   - Learn from false positives/negatives

## Limitations

1. **Reactive, Not Predictive:**
   - Bot reacts to shocks after they occur
   - Cannot predict future events

2. **False Positives:**
   - Normal volatility may trigger alerts
   - Requires human judgment

3. **Data Lag:**
   - Real-time data may have delays
   - Some shocks detected too late

4. **Market-Specific:**
   - Parameters tuned for Indian markets
   - May need adjustment for other markets

## Future Enhancements

1. **News Integration:**
   - Integrate news APIs (NewsAPI, Alpha Vantage News)
   - Sentiment analysis
   - Event calendar integration

2. **Machine Learning:**
   - Train models to predict volatility
   - Classify shock types
   - Optimize response strategies

3. **Correlation Analysis:**
   - Monitor sector correlations
   - Detect contagion effects
   - Cross-asset analysis

4. **Regime Detection:**
   - Identify market regimes (bull/bear/sideways)
   - Adjust strategy per regime
   - Historical regime analysis

## Example Scenarios

### Scenario 1: Earnings Surprise

**Event:** Company reports earnings 20% above expectations

**Detection:**
- Volume spike: 5x average
- Price gap: +8% at open
- Volatility: 7%

**Response:**
- Risk multiplier: 0.35 (multiple shocks)
- Position size: 35% of normal
- Stop loss: 1.5% (tighter)
- Action: Wait for volatility to settle before entering

### Scenario 2: Policy Announcement

**Event:** Government announces new sector regulations

**Detection:**
- Sector-wide price drop: -12%
- Volume spike: 4x average
- Volatility: 9%

**Response:**
- Emergency exit: All positions closed
- Risk multiplier: 0.2 (minimum)
- Action: Stay out until clarity emerges

### Scenario 3: Normal Volatility

**Event:** Regular market movement

**Detection:**
- No significant shocks
- Normal volume
- Low volatility

**Response:**
- Risk multiplier: 1.0 (normal)
- Standard position sizes
- Normal trading continues

## Conclusion

The market shock detection system provides multiple layers of protection:

1. **Detection:** Identifies unusual market conditions
2. **Adaptation:** Adjusts risk and position sizes
3. **Protection:** Exits positions in extreme conditions
4. **Recovery:** Returns to normal trading when conditions stabilize

This system helps protect capital during unpredictable events while allowing the bot to capitalize on opportunities when conditions normalize.
