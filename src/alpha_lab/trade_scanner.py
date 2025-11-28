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
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

import yfinance as yf

from alpha_lab.universes import get_universe
from alpha_lab.config import get_config
from alpha_lab.market_breadth import is_market_healthy


class TradeScanner:
    """Generate actionable trade signals."""
    
    def __init__(self, risk_per_trade: float = None, universe: str = 'tradeable'):
        # Load from config, allow override
        self.risk_per_trade = risk_per_trade or get_config('account.risk_per_trade', 500)
        self.universe = get_universe(universe)
        
        # Load all thresholds from config
        self.cfg = {
            'min_price': get_config('filters.min_price', 3),
            'min_volume': get_config('filters.min_avg_volume', 500000),
            'extension_reject': get_config('extension.hard_reject_5d', 20),
            'fresh_threshold': get_config('breakout.fresh_threshold', 1.05),
            'volume_surge': get_config('breakout.volume_surge', 1.5),
            'price_near_high': get_config('breakout.price_near_high', 0.98),
            'sma_tolerance': get_config('pullback.sma_tolerance', 0.02),
            'min_20d_momentum': get_config('pullback.min_20d_momentum', 5),
            'consolidation_range': get_config('consolidation.max_range_pct', 0.08),
            'stop_atr_mult': get_config('risk_reward.stop_atr_multiplier', 1.5),
            'target_atr_mult': get_config('risk_reward.target_atr_multiplier', 3.0),
            'atr_period': get_config('indicators.atr_period', 14),
        }
        
    def scan(self, top_n: int = 5, check_breadth: bool = True) -> List[Dict]:
        """Scan for trade setups. Returns actionable signals only."""
        results = []
        
        # Check market breadth first
        if check_breadth:
            healthy, reason = is_market_healthy()
            if not healthy:
                print(f"WARNING: {reason}")
                print("Returning empty - market too weak for new longs.")
                return []
            print(f"Market breadth: OK")
        
        print(f"Scanning {len(self.universe)} stocks for trade setups...")
        
        for ticker in self.universe:
            try:
                signal = self._analyze(ticker)
                if signal and signal['action'] != 'WAIT':
                    results.append(signal)
            except Exception as e:
                continue
        
        # Sort by grade (A>B>C) then risk/reward
        grade_order = {'A': 0, 'B': 1, 'C': 2}
        results.sort(key=lambda x: (grade_order.get(x.get('grade', 'C'), 2), -x.get('rr_ratio', 0)))
        return results[:top_n]
    
    def _analyze(self, ticker: str) -> Optional[Dict]:
        """Analyze single ticker for trade setup."""
        stock = yf.Ticker(ticker)
        hist = stock.history(period='3mo')
        
        if len(hist) < 40:
            return None
        
        info = stock.info or {}
        price = hist['Close'].iloc[-1]
        
        # Skip penny stocks and illiquid (from config)
        if price < self.cfg['min_price'] or hist['Volume'].mean() < self.cfg['min_volume']:
            return None
        
        # === Calculate levels ===
        atr = self._calc_atr(hist, self.cfg['atr_period'])
        sma20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else sma20
        high_20 = hist['High'].rolling(20).max().iloc[-1]
        low_20 = hist['Low'].rolling(20).min().iloc[-1]
        
        # Recent momentum
        mom_5d = (price / hist['Close'].iloc[-5] - 1) * 100
        mom_20d = (price / hist['Close'].iloc[-20] - 1) * 100
        
        # === EXTENSION FILTER (from config) ===
        if mom_5d > self.cfg['extension_reject']:
            return None
        
        # Volume surge
        vol_ratio = hist['Volume'].iloc[-5:].mean() / hist['Volume'].iloc[-25:-5].mean()
        
        # === Determine action ===
        action = 'WAIT'
        entry = None
        stop = None
        target = None
        reason = ''
        
        # Check if breakout is fresh (from config)
        high_before_5d = hist['High'].iloc[:-5].max() if len(hist) > 5 else high_20
        is_fresh_breakout = price <= high_before_5d * self.cfg['fresh_threshold']
        
        # SETUP 1: Breakout with volume (only if FRESH)
        near_high = price >= high_20 * self.cfg['price_near_high']
        vol_surge = vol_ratio > self.cfg['volume_surge']
        
        if near_high and vol_surge and mom_5d > 0 and is_fresh_breakout:
            action = 'BUY NOW'
            entry = round(price, 2)
            stop = round(price - self.cfg['stop_atr_mult'] * atr, 2)
            target = round(price + self.cfg['target_atr_mult'] * atr, 2)
            reason = f"Breakout + Vol surge ({vol_ratio:.1f}x)"
        
        # Extended breakout - already ran, wait for pullback
        elif near_high and vol_surge and not is_fresh_breakout:
            action = 'WAIT'
            reason = f"Extended +{mom_5d:.0f}% - wait for pullback"
        
        # SETUP 2: Pullback to SMA20 in uptrend (from config)
        elif price > sma50 and abs(price - sma20) / price < self.cfg['sma_tolerance'] and mom_20d > self.cfg['min_20d_momentum']:
            action = 'BUY PULLBACK'
            entry = round(sma20, 2)
            stop = round(sma20 - self.cfg['stop_atr_mult'] * atr, 2)
            target = round(high_20, 2)
            reason = f"Pullback to SMA20, uptrend intact"
        
        # SETUP 3: Consolidation breakout watch (from config)
        elif (high_20 - low_20) / price < self.cfg['consolidation_range'] and price > sma20:
            action = 'WATCH'
            entry = round(high_20 * 1.01, 2)
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
        
        # === Earnings check (blackout filter) ===
        should_reject, earnings_warning = self._check_earnings(stock)
        if should_reject:
            return None  # Hard reject - too close to earnings
        
        # === Signal Grading (A/B/C) ===
        grade = self._grade_signal(rr_ratio, vol_ratio, mom_5d)
        
        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'price': round(price, 2),
            'action': action,
            'grade': grade,
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
    
    def _grade_signal(self, rr_ratio: float, vol_ratio: float, mom_5d: float) -> str:
        """
        Grade signal quality: A (best), B (good), C (marginal).
        
        Grade A: High R:R, strong volume, not extended
        Grade B: Decent R:R, good volume
        Grade C: Passes filters but marginal quality
        """
        # Load grading thresholds from config
        grade_a = {
            'min_rr': get_config('grading.grade_a_min_rr', 2.5),
            'min_vol': get_config('grading.grade_a_min_volume', 2.0),
            'max_ext': get_config('grading.grade_a_max_extension', 5),
        }
        grade_b = {
            'min_rr': get_config('grading.grade_b_min_rr', 1.5),
            'min_vol': get_config('grading.grade_b_min_volume', 1.5),
            'max_ext': get_config('grading.grade_b_max_extension', 10),
        }
        
        # Grade A: All criteria met at high level
        if (rr_ratio >= grade_a['min_rr'] and 
            vol_ratio >= grade_a['min_vol'] and 
            mom_5d <= grade_a['max_ext']):
            return 'A'
        
        # Grade B: All criteria met at good level
        if (rr_ratio >= grade_b['min_rr'] and 
            vol_ratio >= grade_b['min_vol'] and 
            mom_5d <= grade_b['max_ext']):
            return 'B'
        
        # Grade C: Everything else that passed filters
        return 'C'
    
    def _calc_atr(self, hist: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        tr = pd.concat([
            hist['High'] - hist['Low'],
            abs(hist['High'] - hist['Close'].shift(1)),
            abs(hist['Low'] - hist['Close'].shift(1))
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
    
    def _check_earnings(self, stock) -> Tuple[bool, str]:
        """
        Check if earnings are coming soon.
        
        Returns:
            (should_reject, warning_message)
        """
        blackout_days = get_config('earnings.blackout_days', 5)
        warn_days = get_config('earnings.warn_days', 7)
        
        try:
            cal = stock.calendar
            if cal is not None and not cal.empty:
                if 'Earnings Date' in cal.index:
                    earnings_date = cal.loc['Earnings Date']
                    if isinstance(earnings_date, pd.Series):
                        earnings_date = earnings_date.iloc[0]
                    if pd.notna(earnings_date):
                        days_until = (earnings_date - datetime.now()).days
                        
                        # Hard reject - too close to earnings
                        if 0 <= days_until <= blackout_days:
                            return True, f"EARNINGS IN {days_until} DAYS - BLACKOUT"
                        
                        # Warn but allow
                        if blackout_days < days_until <= warn_days:
                            return False, f"EARNINGS IN {days_until} DAYS"
        except:
            pass
        
        return False, ""


def format_trade_signals(signals: List[Dict]) -> str:
    """Format signals for Telegram."""
    if not signals:
        return "No trade setups today. Cash is a position."
    
    lines = []
    lines.append(f"TRADE SIGNALS - {datetime.now().strftime('%b %d')}")
    lines.append("=" * 35)
    
    for s in signals:
        warning = f"\n   {s['earnings_warning']}" if s.get('earnings_warning') else ""
        grade = s.get('grade', 'C')
        grade_emoji = {'A': '[A]', 'B': '[B]', 'C': '[C]'}.get(grade, '')
        
        lines.append(f"""
{grade_emoji} {s['action']}: {s['name']} ({s['ticker']})
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

