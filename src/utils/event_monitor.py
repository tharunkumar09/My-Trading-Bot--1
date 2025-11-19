"""
Event Monitor
Monitors market events, news, earnings, and volatility spikes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

logger = logging.getLogger(__name__)


class EventMonitor:
    """
    Monitors market events that could cause sudden shocks
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize event monitor
        
        Args:
            config: Event-driven configuration
        """
        self.config = config or {}
        
        self.enabled = self.config.get('enabled', True)
        
        # News monitoring
        self.news_config = self.config.get('news', {})
        self.news_enabled = self.news_config.get('enabled', True)
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        
        # Sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.sentiment_threshold = self.news_config.get('sentiment_threshold', 0.5)
        
        # Keywords for sentiment analysis
        self.positive_keywords = self.news_config.get('keywords', {}).get('positive', [])
        self.negative_keywords = self.news_config.get('keywords', {}).get('negative', [])
        
        # Earnings monitoring
        self.earnings_config = self.config.get('earnings', {})
        self.earnings_enabled = self.earnings_config.get('enabled', True)
        self.days_before_earnings = self.earnings_config.get('days_before', 2)
        self.days_after_earnings = self.earnings_config.get('days_after', 1)
        
        # Volatility monitoring
        self.volatility_config = self.config.get('volatility', {})
        self.volatility_enabled = self.volatility_config.get('enabled', True)
        self.volatility_threshold = self.volatility_config.get('threshold', 2.0)
        
        # Cache for API calls
        self.news_cache = {}
        self.earnings_cache = {}
        
        logger.info("Event monitor initialized")
    
    def fetch_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        Fetch recent news for a symbol
        
        Args:
            symbol: Stock symbol
            days: Number of days to look back
            
        Returns:
            List of news articles
        """
        if not self.news_enabled or not self.newsapi_key:
            return []
        
        # Check cache
        cache_key = f"{symbol}_{days}"
        if cache_key in self.news_cache:
            cache_time, cached_news = self.news_cache[cache_key]
            if datetime.now() - cache_time < timedelta(hours=1):
                return cached_news
        
        try:
            # Fetch from NewsAPI
            url = "https://newsapi.org/v2/everything"
            
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            params = {
                'q': symbol,
                'from': from_date,
                'sortBy': 'relevancy',
                'language': 'en',
                'apiKey': self.newsapi_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            # Cache results
            self.news_cache[cache_key] = (datetime.now(), articles)
            
            logger.info(f"Fetched {len(articles)} news articles for {symbol}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        try:
            scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Check for specific keywords
            text_lower = text.lower()
            keyword_boost = 0
            
            for keyword in self.positive_keywords:
                if keyword.lower() in text_lower:
                    keyword_boost += 0.1
            
            for keyword in self.negative_keywords:
                if keyword.lower() in text_lower:
                    keyword_boost -= 0.1
            
            # Adjust compound score with keyword boost
            scores['compound_adjusted'] = np.clip(scores['compound'] + keyword_boost, -1, 1)
            
            return scores
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'compound': 0, 'compound_adjusted': 0}
    
    def get_news_sentiment(self, symbol: str, days: int = 7) -> Dict:
        """
        Get aggregated news sentiment for a symbol
        
        Args:
            symbol: Stock symbol
            days: Days to look back
            
        Returns:
            Dictionary with sentiment analysis
        """
        articles = self.fetch_news(symbol, days)
        
        if not articles:
            return {
                'sentiment_score': 0,
                'sentiment_label': 'neutral',
                'article_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }
        
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            scores = self.analyze_sentiment(text)
            
            sentiment_score = scores['compound_adjusted']
            sentiments.append(sentiment_score)
            
            if sentiment_score >= self.sentiment_threshold:
                positive_count += 1
            elif sentiment_score <= -self.sentiment_threshold:
                negative_count += 1
            else:
                neutral_count += 1
        
        # Aggregate sentiment
        avg_sentiment = np.mean(sentiments)
        
        if avg_sentiment >= self.sentiment_threshold:
            sentiment_label = 'positive'
        elif avg_sentiment <= -self.sentiment_threshold:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        result = {
            'sentiment_score': avg_sentiment,
            'sentiment_label': sentiment_label,
            'article_count': len(articles),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count
        }
        
        logger.info(f"Sentiment for {symbol}: {sentiment_label} ({avg_sentiment:.2f})")
        
        return result
    
    def check_earnings_date(self, symbol: str) -> Dict:
        """
        Check if earnings announcement is near
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with earnings information
        """
        if not self.earnings_enabled:
            return {'is_near_earnings': False}
        
        # In production, integrate with a proper earnings calendar API
        # For now, this is a placeholder
        
        # Example: Check yfinance for earnings date
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(f"{symbol}.NS")
            calendar = ticker.calendar
            
            if calendar is not None and 'Earnings Date' in calendar:
                earnings_date = pd.to_datetime(calendar['Earnings Date'][0])
                days_until = (earnings_date - datetime.now()).days
                
                is_near = (
                    -self.days_after_earnings <= days_until <= self.days_before_earnings
                )
                
                return {
                    'is_near_earnings': is_near,
                    'earnings_date': earnings_date,
                    'days_until': days_until
                }
        
        except Exception as e:
            logger.debug(f"Could not fetch earnings date for {symbol}: {str(e)}")
        
        return {'is_near_earnings': False}
    
    def check_volatility_spike(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """
        Check for volatility spike
        
        Args:
            df: DataFrame with price data
            window: Window for average volatility calculation
            
        Returns:
            Dictionary with volatility information
        """
        if not self.volatility_enabled or len(df) < window:
            return {'is_volatile': False}
        
        try:
            # Calculate historical volatility
            returns = df['close'].pct_change()
            volatility = returns.rolling(window=window).std()
            
            current_vol = volatility.iloc[-1]
            avg_vol = volatility.iloc[-window:-1].mean()
            
            # Check if current volatility is above threshold
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
            is_volatile = vol_ratio > self.volatility_threshold
            
            return {
                'is_volatile': is_volatile,
                'current_volatility': current_vol,
                'average_volatility': avg_vol,
                'volatility_ratio': vol_ratio
            }
        
        except Exception as e:
            logger.error(f"Error checking volatility: {str(e)}")
            return {'is_volatile': False}
    
    def should_avoid_trading(self, symbol: str, df: pd.DataFrame = None) -> Tuple[bool, List[str]]:
        """
        Check if trading should be avoided due to events
        
        Args:
            symbol: Stock symbol
            df: Optional DataFrame with price data
            
        Returns:
            Tuple of (should_avoid, reasons)
        """
        if not self.enabled:
            return False, []
        
        reasons = []
        
        # Check news sentiment
        if self.news_enabled:
            sentiment = self.get_news_sentiment(symbol, days=3)
            if sentiment['sentiment_label'] == 'negative' and abs(sentiment['sentiment_score']) > 0.7:
                reasons.append(f"Highly negative sentiment ({sentiment['sentiment_score']:.2f})")
        
        # Check earnings
        if self.earnings_enabled:
            earnings_info = self.check_earnings_date(symbol)
            if earnings_info.get('is_near_earnings', False):
                reasons.append(f"Near earnings date ({earnings_info.get('days_until', 0)} days)")
        
        # Check volatility
        if self.volatility_enabled and df is not None:
            vol_info = self.check_volatility_spike(df)
            if vol_info.get('is_volatile', False):
                reasons.append(f"High volatility spike ({vol_info.get('volatility_ratio', 0):.2f}x)")
        
        should_avoid = len(reasons) > 0
        
        if should_avoid:
            logger.warning(f"Avoiding {symbol} due to: {', '.join(reasons)}")
        
        return should_avoid, reasons
    
    def get_opportunity_score(self, symbol: str, df: pd.DataFrame = None) -> float:
        """
        Calculate opportunity score for a symbol (0-1)
        Higher score = better opportunity
        
        Args:
            symbol: Stock symbol
            df: Optional DataFrame with price data
            
        Returns:
            Opportunity score (0-1)
        """
        if not self.enabled:
            return 0.5  # Neutral
        
        score = 0.5  # Start neutral
        
        # News sentiment contribution (±0.3)
        if self.news_enabled:
            sentiment = self.get_news_sentiment(symbol, days=7)
            sentiment_score = sentiment['sentiment_score']
            score += sentiment_score * 0.3
        
        # Volatility contribution (±0.2)
        # Moderate volatility is good, extreme is bad
        if self.volatility_enabled and df is not None:
            vol_info = self.check_volatility_spike(df)
            vol_ratio = vol_info.get('volatility_ratio', 1)
            
            if 1.2 <= vol_ratio <= 1.8:
                score += 0.2  # Good volatility for trading
            elif vol_ratio > 2.5:
                score -= 0.3  # Too volatile
        
        # Earnings contribution
        if self.earnings_enabled:
            earnings_info = self.check_earnings_date(symbol)
            if earnings_info.get('is_near_earnings', False):
                score -= 0.2  # Avoid near earnings
        
        # Clamp to 0-1
        score = np.clip(score, 0, 1)
        
        return score
