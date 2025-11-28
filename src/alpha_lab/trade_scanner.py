"""
Trade Scanner - Actionable trade signals, not research

Outputs:
- BUY NOW / BUY PULLBACK / WAIT
- Exact entry, stop, target
- Risk/Reward ratio
- Position size for $500 risk
- Earnings warning
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

import yfinance as yf

from alpha_lab.universes import get_universe


class TradeScanner:
    """Generate actionable trade signals."""
    
    def __init__(self, risk_per_trade: float = 500, universe: str = 'tradeable'):
        self.risk_per_trade = risk_per_trade
        self.universe = get_universe(universe)
        
    def scan(self, top_n: int = 5) -> List[Dict]:
        """Scan for trade setups. Returns actionable signals only."""
        results = []
        
        print(f"Scanning {len(self.universe)} stocks for trade setups...")
        
        for ticker in self.universe:
            try:
                signal = self._analyze(ticker)
                if signal and signal['action'] != 'WAIT':
                    results.append(signal)
            except Exception as e:
                continue
        
        # Sort by risk/reward
        results.sort(key=lambda x: x.get('rr_ratio', 0), reverse=True)
        return results[:top_n]
    
    def _analyze(self, ticker: str) -> Optional[Dict]:
        """Analyze single ticker for trade setup."""
        stock = yf.Ticker(ticker)
        hist = stock.history(period='3mo')
        
        if len(hist) < 40:
            return None
        
        info = stock.info or {}
        price = hist['Close'].iloc[-1]
        
        # Skip penny stocks and illiquid
        if price < 3 or hist['Volume'].mean() < 500000:
            return None
        
        # === Calculate levels ===
        atr = self._calc_atr(hist)
        sma20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else sma20
        high_20 = hist['High'].rolling(20).max().iloc[-1]
        low_20 = hist['Low'].rolling(20).min().iloc[-1]
        
        # Recent momentum
        mom_5d = (price / hist['Close'].iloc[-5] - 1) * 100
        mom_20d = (price / hist['Close'].iloc[-20] - 1) * 100
        
        # === EXTENSION FILTER ===
        # Reject stocks that already made the move - you're chasing
        if mom_5d > 20:
            return None  # Hard reject: already ran 20%+ in 5 days
        
        # Volume surge
        vol_ratio = hist['Volume'].iloc[-5:].mean() / hist['Volume'].iloc[-25:-5].mean()
        
        # === Determine action ===
        action = 'WAIT'
        entry = None
        stop = None
        target = None
        reason = ''
        
        # Check if breakout is fresh (not extended)
        high_before_5d = hist['High'].iloc[:-5].max() if len(hist) > 5 else high_20
        is_fresh_breakout = price <= high_before_5d * 1.05  # Within 5% of prior resistance
        
        # SETUP 1: Breakout with volume (only if FRESH)
        if price >= high_20 * 0.98 and vol_ratio > 1.5 and mom_5d > 0 and is_fresh_breakout:
            action = 'BUY NOW'
            entry = round(price, 2)
            stop = round(price - 1.5 * atr, 2)
            target = round(price + 3 * atr, 2)
            reason = f"Breakout + Vol surge ({vol_ratio:.1f}x)"
        
        # Extended breakout - already ran, wait for pullback
        elif price >= high_20 * 0.98 and vol_ratio > 1.5 and not is_fresh_breakout:
            action = 'WAIT'  # Don't chase
            reason = f"Extended +{mom_5d:.0f}% - wait for pullback"
        
        # SETUP 2: Pullback to SMA20 in uptrend
        elif price > sma50 and abs(price - sma20) / price < 0.02 and mom_20d > 5:
            action = 'BUY PULLBACK'
            entry = round(sma20, 2)
            stop = round(sma20 - 1.5 * atr, 2)
            target = round(high_20, 2)
            reason = f"Pullback to SMA20, uptrend intact"
        
        # SETUP 3: Consolidation breakout watch
        elif (high_20 - low_20) / price < 0.08 and price > sma20:
            action = 'WATCH'
            entry = round(high_20 * 1.01, 2)  # Buy on breakout
            stop = round(low_20 * 0.98, 2)
            target = round(high_20 + (high_20 - low_20), 2)
            reason = f"Tight range, wait for breakout above ${high_20:.2f}"
        
        if action == 'WAIT':
            return None
        
        # === Risk/Reward ===
        if entry and stop and target:
            risk = entry - stop
            reward = target - entry
            rr_ratio = round(reward / risk, 1) if risk > 0 else 0
        else:
            rr_ratio = 0
        
        # === Position size ===
        if risk > 0:
            shares = int(self.risk_per_trade / risk)
        else:
            shares = 0
        
        # === Earnings check ===
        earnings_warning = self._check_earnings(stock)
        
        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'price': round(price, 2),
            'action': action,
            'entry': entry,
            'stop': stop,
            'target': target,
            'rr_ratio': rr_ratio,
            'shares': shares,
            'risk_amount': round(shares * risk, 2) if risk > 0 else 0,
            'reason': reason,
            'mom_5d': round(mom_5d, 1),
            'vol_ratio': round(vol_ratio, 1),
            'earnings_warning': earnings_warning,
        }
    
    def _calc_atr(self, hist: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        tr = pd.concat([
            hist['High'] - hist['Low'],
            abs(hist['High'] - hist['Close'].shift(1)),
            abs(hist['Low'] - hist['Close'].shift(1))
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
    
    def _check_earnings(self, stock) -> str:
        """Check if earnings are coming soon."""
        try:
            cal = stock.calendar
            if cal is not None and not cal.empty:
                if 'Earnings Date' in cal.index:
                    earnings_date = cal.loc['Earnings Date']
                    if isinstance(earnings_date, pd.Series):
                        earnings_date = earnings_date.iloc[0]
                    if pd.notna(earnings_date):
                        days_until = (earnings_date - datetime.now()).days
                        if 0 <= days_until <= 7:
                            return f"EARNINGS IN {days_until} DAYS"
        except:
            pass
        return ""


def format_trade_signals(signals: List[Dict]) -> str:
    """Format signals for Telegram."""
    if not signals:
        return "No trade setups today. Cash is a position."
    
    lines = []
    lines.append(f"TRADE SIGNALS - {datetime.now().strftime('%b %d')}")
    lines.append("=" * 35)
    
    for s in signals:
        warning = f"\n   {s['earnings_warning']}" if s['earnings_warning'] else ""
        
        lines.append(f"""
{s['action']}: {s['name']} ({s['ticker']})
Price: ${s['price']} | 5D: {s['mom_5d']:+.1f}%

Entry: ${s['entry']}
Stop:  ${s['stop']}
Target: ${s['target']}
R:R = 1:{s['rr_ratio']}

Size: {s['shares']} shares (${s['risk_amount']:.0f} risk)
Why: {s['reason']}{warning}
""")
    
    return "\n".join(lines)


if __name__ == "__main__":
    scanner = TradeScanner(risk_per_trade=500)
    signals = scanner.scan(top_n=5)
    print(format_trade_signals(signals))

