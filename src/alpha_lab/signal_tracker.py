"""
Signal Tracker - Log and track signal outcomes
==============================================

Logs every signal with unique ID, then tracks:
- Did it hit target?
- Did it hit stop?
- How long did it take?
- What was the max adverse excursion (MAE)?

Usage:
    from alpha_lab.signal_tracker import SignalTracker
    
    tracker = SignalTracker()
    signal_id = tracker.log_signal('EXAS', 'BUY NOW', 101.45, 95.43, 113.48)
    
    # Later...
    tracker.check_outcomes()  # Updates all open signals
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf

# Signal database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/signals.json')


class SignalTracker:
    """Track signal performance over time."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.signals = self._load_signals()
    
    def _load_signals(self) -> Dict:
        """Load signals from JSON file."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'signals': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'open': 0}}
    
    def _save_signals(self):
        """Save signals to JSON file."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(self.signals, f, indent=2, default=str)
    
    def log_signal(self, ticker: str, action: str, entry: float, stop: float, 
                   target: float, reason: str = '') -> str:
        """
        Log a new signal.
        
        Returns:
            Unique signal ID
        """
        signal_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        signal = {
            'id': signal_id,
            'ticker': ticker,
            'action': action,
            'entry': entry,
            'stop': stop,
            'target': target,
            'reason': reason,
            'created_at': datetime.now().isoformat(),
            'status': 'OPEN',  # OPEN, WIN, LOSS, EXPIRED
            'outcome': None,
            'outcome_price': None,
            'outcome_date': None,
            'days_held': None,
            'max_adverse': None,  # Max drawdown from entry
            'max_favorable': None,  # Max profit from entry
        }
        
        self.signals['signals'].append(signal)
        self.signals['stats']['total'] += 1
        self.signals['stats']['open'] += 1
        self._save_signals()
        
        return signal_id
    
    def check_outcomes(self, max_days: int = 10) -> List[Dict]:
        """
        Check all open signals for outcomes.
        
        Args:
            max_days: Expire signals after this many days
        
        Returns:
            List of signals that closed today
        """
        closed_today = []
        
        for signal in self.signals['signals']:
            if signal['status'] != 'OPEN':
                continue
            
            ticker = signal['ticker']
            entry = signal['entry']
            stop = signal['stop']
            target = signal['target']
            created = datetime.fromisoformat(signal['created_at'])
            
            # Get price history since signal
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=created.strftime('%Y-%m-%d'))
                
                if hist.empty:
                    continue
                
                # Track max adverse/favorable excursion
                lows = hist['Low'].values
                highs = hist['High'].values
                
                max_adverse = min((entry - low) / entry * 100 for low in lows)
                max_favorable = max((high - entry) / entry * 100 for high in highs)
                
                signal['max_adverse'] = round(max_adverse, 2)
                signal['max_favorable'] = round(max_favorable, 2)
                
                # Check each day for stop/target hit
                for idx, row in hist.iterrows():
                    # Check stop hit (low touched stop)
                    if row['Low'] <= stop:
                        signal['status'] = 'LOSS'
                        signal['outcome'] = 'STOPPED OUT'
                        signal['outcome_price'] = stop
                        signal['outcome_date'] = idx.isoformat()
                        signal['days_held'] = (idx - created).days
                        self.signals['stats']['losses'] += 1
                        self.signals['stats']['open'] -= 1
                        closed_today.append(signal)
                        break
                    
                    # Check target hit (high touched target)
                    if row['High'] >= target:
                        signal['status'] = 'WIN'
                        signal['outcome'] = 'TARGET HIT'
                        signal['outcome_price'] = target
                        signal['outcome_date'] = idx.isoformat()
                        signal['days_held'] = (idx - created).days
                        self.signals['stats']['wins'] += 1
                        self.signals['stats']['open'] -= 1
                        closed_today.append(signal)
                        break
                
                # Check expiration
                days_open = (datetime.now() - created).days
                if signal['status'] == 'OPEN' and days_open > max_days:
                    current_price = hist['Close'].iloc[-1]
                    pnl_pct = (current_price - entry) / entry * 100
                    
                    signal['status'] = 'EXPIRED'
                    signal['outcome'] = f"EXPIRED ({pnl_pct:+.1f}%)"
                    signal['outcome_price'] = current_price
                    signal['outcome_date'] = datetime.now().isoformat()
                    signal['days_held'] = days_open
                    
                    # Count as win if profitable at expiration
                    if pnl_pct > 0:
                        self.signals['stats']['wins'] += 1
                    else:
                        self.signals['stats']['losses'] += 1
                    self.signals['stats']['open'] -= 1
                    closed_today.append(signal)
                    
            except Exception as e:
                continue
        
        self._save_signals()
        return closed_today
    
    def get_stats(self) -> Dict:
        """Get performance statistics."""
        stats = self.signals['stats']
        total_closed = stats['wins'] + stats['losses']
        
        return {
            'total_signals': stats['total'],
            'open': stats['open'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': round(stats['wins'] / total_closed * 100, 1) if total_closed > 0 else 0,
            'total_closed': total_closed,
        }
    
    def get_open_signals(self) -> List[Dict]:
        """Get all currently open signals."""
        return [s for s in self.signals['signals'] if s['status'] == 'OPEN']
    
    def get_recent_closed(self, days: int = 7) -> List[Dict]:
        """Get signals closed in the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        closed = []
        
        for s in self.signals['signals']:
            if s['status'] == 'OPEN':
                continue
            if s['outcome_date']:
                outcome_date = datetime.fromisoformat(s['outcome_date'])
                if outcome_date > cutoff:
                    closed.append(s)
        
        return closed
    
    def format_report(self) -> str:
        """Generate performance report."""
        stats = self.get_stats()
        open_signals = self.get_open_signals()
        recent = self.get_recent_closed(days=7)
        
        lines = []
        lines.append("=" * 50)
        lines.append("SIGNAL PERFORMANCE REPORT")
        lines.append("=" * 50)
        lines.append(f"\nOverall Stats:")
        lines.append(f"  Total Signals: {stats['total_signals']}")
        lines.append(f"  Win Rate: {stats['win_rate']}% ({stats['wins']}W / {stats['losses']}L)")
        lines.append(f"  Currently Open: {stats['open']}")
        
        if open_signals:
            lines.append(f"\nOpen Positions ({len(open_signals)}):")
            for s in open_signals:
                days = (datetime.now() - datetime.fromisoformat(s['created_at'])).days
                lines.append(f"  {s['ticker']}: Entry ${s['entry']} | Stop ${s['stop']} | Target ${s['target']} ({days}d)")
        
        if recent:
            lines.append(f"\nRecent Closes ({len(recent)}):")
            for s in recent:
                emoji = "+" if s['status'] == 'WIN' else "-"
                lines.append(f"  {emoji} {s['ticker']}: {s['outcome']} @ ${s['outcome_price']} ({s['days_held']}d)")
        
        return "\n".join(lines)


def log_signals_from_scanner(signals: List[Dict]) -> List[str]:
    """
    Helper to log signals from TradeScanner output.
    
    Args:
        signals: List of signal dicts from TradeScanner.scan()
    
    Returns:
        List of signal IDs
    """
    tracker = SignalTracker()
    ids = []
    
    for s in signals:
        if s['action'] in ['BUY NOW', 'BUY PULLBACK']:
            signal_id = tracker.log_signal(
                ticker=s['ticker'],
                action=s['action'],
                entry=s['entry'],
                stop=s['stop'],
                target=s['target'],
                reason=s['reason']
            )
            ids.append(signal_id)
            print(f"  Logged: {signal_id}")
    
    return ids


if __name__ == "__main__":
    tracker = SignalTracker()
    
    # Check outcomes of existing signals
    print("Checking signal outcomes...")
    closed = tracker.check_outcomes()
    
    if closed:
        print(f"\n{len(closed)} signals closed:")
        for s in closed:
            print(f"  {s['ticker']}: {s['outcome']}")
    
    # Print report
    print(tracker.format_report())

