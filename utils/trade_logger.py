"""
Trade logging module for recording all trades and performance.
"""
import pandas as pd
import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class TradeLogger:
    """Log and track all trades."""
    
    def __init__(self, log_file: str = "logs/trades.json"):
        self.log_file = log_file
        self.trades = []
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        self._load_trades()
    
    def _load_trades(self):
        """Load existing trades from file."""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    self.trades = json.load(f)
                logger.info(f"Loaded {len(self.trades)} existing trades")
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            self.trades = []
    
    def _save_trades(self):
        """Save trades to file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
    
    def log_trade(self, trade_data: Dict):
        """
        Log a trade.
        
        Args:
            trade_data: Dict with trade information
        """
        trade = {
            'timestamp': datetime.now().isoformat(),
            **trade_data
        }
        self.trades.append(trade)
        self._save_trades()
        logger.info(f"Trade logged: {trade_data.get('action', 'UNKNOWN')} - {trade_data.get('symbol', 'N/A')}")
    
    def log_order(self, order_data: Dict):
        """Log an order placement."""
        self.log_trade({
            'type': 'order',
            **order_data
        })
    
    def log_position_open(self, symbol: str, entry_price: float, quantity: int,
                         stop_loss: float, order_id: str = None):
        """Log position opening."""
        self.log_trade({
            'type': 'position_open',
            'action': 'BUY',
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'order_id': order_id
        })
    
    def log_position_close(self, symbol: str, exit_price: float, quantity: int,
                          pnl: float, exit_reason: str = None, order_id: str = None):
        """Log position closing."""
        self.log_trade({
            'type': 'position_close',
            'action': 'SELL',
            'symbol': symbol,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'return_pct': (pnl / (exit_price * quantity)) * 100 if quantity > 0 else 0,
            'exit_reason': exit_reason,
            'order_id': order_id
        })
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get all trades as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary from logged trades."""
        if not self.trades:
            return {}
        
        df = self.get_trades_df()
        closed_trades = df[df['type'] == 'position_close']
        
        if closed_trades.empty:
            return {}
        
        total_pnl = closed_trades['pnl'].sum()
        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] <= 0]
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(closed_trades)) * 100 if len(closed_trades) > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
            'largest_win': closed_trades['pnl'].max() if len(closed_trades) > 0 else 0,
            'largest_loss': closed_trades['pnl'].min() if len(closed_trades) > 0 else 0
        }
