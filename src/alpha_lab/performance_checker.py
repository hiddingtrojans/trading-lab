"""
Performance Checker - Validate if signals actually work
========================================================

Run this to check how recent signals performed.
Does not require persistent storage - fetches fresh data each time.

Usage:
    python src/alpha_lab/performance_checker.py
    python src/alpha_lab/performance_checker.py --days 5
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import yfinance as yf

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from alpha_lab.trade_scanner import TradeScanner


class PerformanceChecker:
    """Check how scanner signals would have performed."""
    
    def __init__(self):
        self.scanner = TradeScanner(risk_per_trade=500)
    
    def backtest_signals(self, days_back: int = 5, hold_days: int = 5) -> Dict:
        """
        Backtest: What if we took every signal N days ago?
        
        Args:
            days_back: How many days ago to simulate signals
            hold_days: How long to hold each position
        
        Returns:
            Performance summary
        """
        results = {
            'signals': [],
            'wins': 0,
            'losses': 0,
            'expired': 0,
            'total_pnl_pct': 0,
        }
        
        # Get historical data for each ticker in universe
        print(f"Backtesting signals from {days_back} days ago...")
        print(f"Hold period: {hold_days} days")
        print("-" * 50)
        
        for ticker in self.scanner.universe[:50]:  # Limit for speed
            try:
                outcome = self._check_ticker_signal(ticker, days_back, hold_days)
                if outcome:
                    results['signals'].append(outcome)
                    
                    if outcome['result'] == 'WIN':
                        results['wins'] += 1
                    elif outcome['result'] == 'LOSS':
                        results['losses'] += 1
                    else:
                        results['expired'] += 1
                    
                    results['total_pnl_pct'] += outcome['pnl_pct']
                    
            except Exception as e:
                continue
        
        # Calculate stats
        total = len(results['signals'])
        if total > 0:
            results['win_rate'] = round(results['wins'] / total * 100, 1)
            results['avg_pnl'] = round(results['total_pnl_pct'] / total, 2)
        else:
            results['win_rate'] = 0
            results['avg_pnl'] = 0
        
        return results
    
    def _check_ticker_signal(self, ticker: str, days_back: int, hold_days: int) -> Dict:
        """Check if a ticker would have signaled and how it performed."""
        stock = yf.Ticker(ticker)
        
        # Get enough history
        hist = stock.history(period='3mo')
        if len(hist) < days_back + hold_days + 40:
            return None
        
        # Simulate being at days_back point
        signal_idx = -days_back - hold_days
        signal_hist = hist.iloc[:signal_idx]
        
        if len(signal_hist) < 40:
            return None
        
        price = signal_hist['Close'].iloc[-1]
        
        # Skip penny stocks
        if price < 3 or signal_hist['Volume'].mean() < 500000:
            return None
        
        # Calculate levels at signal time
        atr = self._calc_atr(signal_hist)
        sma20 = signal_hist['Close'].rolling(20).mean().iloc[-1]
        high_20 = signal_hist['High'].rolling(20).max().iloc[-1]
        
        mom_5d = (price / signal_hist['Close'].iloc[-5] - 1) * 100
        vol_ratio = signal_hist['Volume'].iloc[-5:].mean() / signal_hist['Volume'].iloc[-25:-5].mean()
        
        # Extension filter
        if mom_5d > 20:
            return None
        
        # Check for breakout signal
        high_before_5d = signal_hist['High'].iloc[:-5].max()
        is_fresh = price <= high_before_5d * 1.05
        
        if not (price >= high_20 * 0.98 and vol_ratio > 1.5 and mom_5d > 0 and is_fresh):
            return None
        
        # We have a signal - check outcome
        entry = price
        stop = round(price - 1.5 * atr, 2)
        target = round(price + 3 * atr, 2)
        
        # Get forward data
        forward_hist = hist.iloc[signal_idx:signal_idx + hold_days]
        
        result = 'EXPIRED'
        exit_price = forward_hist['Close'].iloc[-1]
        
        for _, row in forward_hist.iterrows():
            if row['Low'] <= stop:
                result = 'LOSS'
                exit_price = stop
                break
            if row['High'] >= target:
                result = 'WIN'
                exit_price = target
                break
        
        pnl_pct = (exit_price - entry) / entry * 100
        
        return {
            'ticker': ticker,
            'entry': round(entry, 2),
            'stop': stop,
            'target': target,
            'exit': round(exit_price, 2),
            'result': result,
            'pnl_pct': round(pnl_pct, 2),
        }
    
    def _calc_atr(self, hist, period: int = 14) -> float:
        """Calculate ATR."""
        import pandas as pd
        tr = pd.concat([
            hist['High'] - hist['Low'],
            abs(hist['High'] - hist['Close'].shift(1)),
            abs(hist['Low'] - hist['Close'].shift(1))
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
    
    def check_recent_performance(self) -> str:
        """Generate performance report for recent signals."""
        results_5d = self.backtest_signals(days_back=5, hold_days=5)
        results_10d = self.backtest_signals(days_back=10, hold_days=5)
        
        lines = []
        lines.append("=" * 50)
        lines.append("SIGNAL PERFORMANCE VALIDATION")
        lines.append("=" * 50)
        
        lines.append(f"\n5 Days Ago (hold 5 days):")
        lines.append(f"  Signals: {len(results_5d['signals'])}")
        lines.append(f"  Win Rate: {results_5d['win_rate']}%")
        lines.append(f"  Avg P&L: {results_5d['avg_pnl']:+.2f}%")
        lines.append(f"  W/L/E: {results_5d['wins']}/{results_5d['losses']}/{results_5d['expired']}")
        
        lines.append(f"\n10 Days Ago (hold 5 days):")
        lines.append(f"  Signals: {len(results_10d['signals'])}")
        lines.append(f"  Win Rate: {results_10d['win_rate']}%")
        lines.append(f"  Avg P&L: {results_10d['avg_pnl']:+.2f}%")
        lines.append(f"  W/L/E: {results_10d['wins']}/{results_10d['losses']}/{results_10d['expired']}")
        
        # Show individual results
        if results_5d['signals']:
            lines.append(f"\nRecent Signal Details:")
            for s in results_5d['signals'][:10]:
                emoji = "+" if s['result'] == 'WIN' else ("-" if s['result'] == 'LOSS' else "~")
                lines.append(f"  {emoji} {s['ticker']}: ${s['entry']} -> ${s['exit']} ({s['pnl_pct']:+.1f}%)")
        
        return "\n".join(lines)


def format_for_telegram(results: Dict) -> str:
    """Format results for Telegram."""
    total = len(results['signals'])
    if total == 0:
        return "No signals to validate."
    
    msg = f"""SIGNAL VALIDATION
Win Rate: {results['win_rate']}% ({results['wins']}W/{results['losses']}L)
Avg P&L: {results['avg_pnl']:+.2f}%

Details:"""
    
    for s in results['signals'][:5]:
        emoji = "+" if s['result'] == 'WIN' else "-"
        msg += f"\n{emoji} {s['ticker']}: {s['pnl_pct']:+.1f}%"
    
    return msg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check signal performance')
    parser.add_argument('--days', type=int, default=5, help='Days back to check')
    parser.add_argument('--hold', type=int, default=5, help='Hold period')
    args = parser.parse_args()
    
    checker = PerformanceChecker()
    print(checker.check_recent_performance())

