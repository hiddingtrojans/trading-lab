"""
Universe Scanner - Find edge in small/mid caps before the crowd

The edge comes from TIMING:
- Finding institutional accumulation BEFORE it shows in 13F filings
- Catching revenue acceleration BEFORE analysts upgrade
- Spotting technical breakouts BEFORE they're obvious

This scanner combines:
1. Volume anomaly detection (institutions entering)
2. Price momentum + relative strength
3. Technical setup quality
4. Basic fundamental sanity checks
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

# Handle imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

import yfinance as yf

from alpha_lab.universes import SMALL_CAP, MID_CAP, get_universe


class UniverseScanner:
    """
    Scans small/mid cap universe for institutional accumulation patterns.
    
    The edge: Find stocks where smart money is entering BEFORE the move.
    """
    
    def __init__(self, include_mid_caps: bool = True):
        if include_mid_caps:
            self.universe = get_universe('tradeable')
        else:
            self.universe = SMALL_CAP.copy()
        
    def scan(self, top_n: int = 10) -> List[Dict]:
        """
        Scan universe and return top opportunities ranked by edge score.
        
        Edge Score Components:
        1. Volume Anomaly (40%) - Institutions entering
        2. Price Momentum (25%) - Trend strength
        3. Relative Strength (20%) - Outperforming market
        4. Technical Setup (15%) - Clean entry available
        """
        results = []
        spy_data = self._get_benchmark_data()
        
        print(f"Scanning {len(self.universe)} stocks...")
        
        for i, ticker in enumerate(self.universe):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(self.universe)}")
            
            try:
                score_data = self._analyze_ticker(ticker, spy_data)
                if score_data:
                    results.append(score_data)
            except Exception as e:
                continue
        
        # Sort by edge score
        results.sort(key=lambda x: x['edge_score'], reverse=True)
        
        return results[:top_n]
    
    def _get_benchmark_data(self) -> pd.DataFrame:
        """Get SPY data for relative strength calculation."""
        spy = yf.Ticker('SPY')
        return spy.history(period='3mo')
    
    def _analyze_ticker(self, ticker: str, spy_data: pd.DataFrame) -> Optional[Dict]:
        """
        Analyze single ticker for edge signals.
        
        Returns None if stock doesn't pass basic filters.
        """
        stock = yf.Ticker(ticker)
        
        # Get price history
        hist = stock.history(period='3mo')
        if len(hist) < 40:
            return None
        
        # Get info for fundamentals
        try:
            info = stock.info
        except:
            info = {}
        
        # === FILTER 1: Basic sanity ===
        price = hist['Close'].iloc[-1]
        if price < 1:  # Penny stock
            return None
        
        avg_volume = hist['Volume'].mean()
        if avg_volume < 500000:  # Too illiquid
            return None
        
        market_cap = info.get('marketCap', 0)
        if market_cap and market_cap < 300_000_000:  # Below $300M
            return None
        
        # === SCORE 1: Volume Anomaly (40%) ===
        volume_score = self._calc_volume_anomaly(hist)
        
        # === SCORE 2: Price Momentum (25%) ===
        momentum_score = self._calc_momentum(hist)
        
        # === SCORE 3: Relative Strength (20%) ===
        rs_score = self._calc_relative_strength(hist, spy_data)
        
        # === SCORE 4: Technical Setup (15%) ===
        tech_score, setup_type = self._calc_technical_setup(hist)
        
        # === EXTENSION FILTER ===
        # Reject stocks that already made the move - you're chasing, not catching
        mom_5d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-5] - 1) * 100
        
        # Hard reject: Already ran 20%+ in 5 days
        if mom_5d > 20:
            return None
        
        # Penalize extended stocks (reduces edge score)
        extension_penalty = 0
        if mom_5d > 15:
            extension_penalty = 30  # Heavy penalty - likely too late
        elif mom_5d > 10:
            extension_penalty = 15  # Moderate penalty - proceed with caution
        elif mom_5d > 7:
            extension_penalty = 5   # Minor penalty
        
        # === COMBINED EDGE SCORE ===
        edge_score = (
            volume_score * 0.40 +
            momentum_score * 0.25 +
            rs_score * 0.20 +
            tech_score * 0.15
        ) - extension_penalty
        
        # Only return if score is meaningful
        if edge_score < 50:
            return None
        
        # Calculate key levels
        support = hist['Low'].rolling(20).min().iloc[-1]
        resistance = hist['High'].rolling(20).max().iloc[-1]
        
        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'price': price,
            'market_cap_b': market_cap / 1_000_000_000 if market_cap else 0,
            'edge_score': round(edge_score, 1),
            'volume_score': round(volume_score, 1),
            'momentum_score': round(momentum_score, 1),
            'rs_score': round(rs_score, 1),
            'tech_score': round(tech_score, 1),
            'setup_type': setup_type,
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'avg_volume': int(avg_volume),
            'volume_change': round(self._get_volume_change(hist), 1),
            'mom_5d': round((hist['Close'].iloc[-1] / hist['Close'].iloc[-5] - 1) * 100, 1),
            'mom_20d': round((hist['Close'].iloc[-1] / hist['Close'].iloc[-20] - 1) * 100, 1),
            'why': self._generate_thesis(volume_score, momentum_score, rs_score, setup_type)
        }
    
    def _calc_volume_anomaly(self, hist: pd.DataFrame) -> float:
        """
        Detect unusual volume - sign of institutional accumulation.
        
        Score 0-100:
        - 100: Volume 3x+ above average with price up
        - 80: Volume 2x above average with price up
        - 60: Volume 1.5x above average
        - 40: Normal volume with uptrend
        - 20: Below average volume
        """
        recent_vol = hist['Volume'].iloc[-5:].mean()
        avg_vol = hist['Volume'].iloc[:-5].mean()
        
        if avg_vol == 0:
            return 0
        
        vol_ratio = recent_vol / avg_vol
        price_change = (hist['Close'].iloc[-1] / hist['Close'].iloc[-5] - 1)
        
        # Volume spike WITH price increase = accumulation
        if vol_ratio > 3 and price_change > 0:
            return 100
        elif vol_ratio > 2 and price_change > 0:
            return 85
        elif vol_ratio > 1.5 and price_change > 0:
            return 70
        elif vol_ratio > 1.5:
            return 55
        elif vol_ratio > 1.2:
            return 45
        elif vol_ratio > 0.8:
            return 35
        else:
            return 20
    
    def _calc_momentum(self, hist: pd.DataFrame) -> float:
        """
        Multi-timeframe momentum score.
        
        Combines:
        - 5-day momentum (short-term)
        - 20-day momentum (medium-term)
        - Price vs SMA20 (trend)
        """
        price = hist['Close'].iloc[-1]
        
        # Short-term momentum (5 days)
        mom_5d = (price / hist['Close'].iloc[-5] - 1) * 100
        
        # Medium-term momentum (20 days)
        mom_20d = (price / hist['Close'].iloc[-20] - 1) * 100
        
        # Trend (price vs SMA20)
        sma20 = hist['Close'].rolling(20).mean().iloc[-1]
        above_sma = price > sma20
        
        score = 50  # Base
        
        # 5-day momentum
        if mom_5d > 10:
            score += 20
        elif mom_5d > 5:
            score += 15
        elif mom_5d > 0:
            score += 10
        elif mom_5d > -5:
            score += 0
        else:
            score -= 15
        
        # 20-day momentum
        if mom_20d > 20:
            score += 20
        elif mom_20d > 10:
            score += 15
        elif mom_20d > 0:
            score += 10
        else:
            score -= 10
        
        # Trend bonus
        if above_sma:
            score += 10
        else:
            score -= 10
        
        return max(0, min(100, score))
    
    def _calc_relative_strength(self, hist: pd.DataFrame, spy_data: pd.DataFrame) -> float:
        """
        Calculate relative strength vs SPY.
        
        A stock outperforming SPY = institutional interest.
        """
        # Align dates
        common_dates = hist.index.intersection(spy_data.index)
        if len(common_dates) < 20:
            return 50
        
        stock_ret = (hist.loc[common_dates, 'Close'].iloc[-1] / 
                     hist.loc[common_dates, 'Close'].iloc[0] - 1)
        spy_ret = (spy_data.loc[common_dates, 'Close'].iloc[-1] / 
                   spy_data.loc[common_dates, 'Close'].iloc[0] - 1)
        
        # Relative performance
        outperformance = (stock_ret - spy_ret) * 100
        
        if outperformance > 30:
            return 100
        elif outperformance > 20:
            return 85
        elif outperformance > 10:
            return 70
        elif outperformance > 0:
            return 55
        elif outperformance > -10:
            return 40
        else:
            return 25
    
    def _calc_technical_setup(self, hist: pd.DataFrame) -> tuple:
        """
        Identify clean technical setups.
        
        Returns (score, setup_type)
        """
        price = hist['Close'].iloc[-1]
        sma20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else sma20
        
        high_20 = hist['High'].rolling(20).max().iloc[-1]
        low_20 = hist['Low'].rolling(20).min().iloc[-1]
        
        # ATR for volatility context
        tr = pd.concat([
            hist['High'] - hist['Low'],
            abs(hist['High'] - hist['Close'].shift(1)),
            abs(hist['Low'] - hist['Close'].shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / price * 100
        
        # Setup detection
        setup_type = "NONE"
        score = 40
        
        # Check if breakout is FRESH (compare to high from 5+ days ago)
        high_before_5d = hist['High'].iloc[:-5].max() if len(hist) > 5 else high_20
        
        # Breakout: Price near/above 20-day high
        if price >= high_20 * 0.98:
            # Only reward if this is a FRESH breakout (just broke above prior high)
            if price > high_before_5d * 1.02:
                # Already extended above old resistance - chasing
                setup_type = "EXTENDED"
                score = 35
            else:
                # Fresh breakout - catching the move
                setup_type = "BREAKOUT"
                score = 85
        
        # Pullback to support: Price near SMA20 in uptrend
        elif price > sma50 and abs(price - sma20) / price < 0.02:
            setup_type = "PULLBACK"
            score = 75
        
        # Consolidation: Tight range, ready to move
        elif (high_20 - low_20) / price < 0.10:
            setup_type = "CONSOLIDATION"
            score = 65
        
        # Reversal: Bouncing off lows
        elif price < sma20 and price > low_20 * 1.05:
            setup_type = "REVERSAL"
            score = 55
        
        return score, setup_type
    
    def _get_volume_change(self, hist: pd.DataFrame) -> float:
        """Calculate volume change % vs 20-day average."""
        recent_vol = hist['Volume'].iloc[-5:].mean()
        avg_vol = hist['Volume'].iloc[-25:-5].mean()
        
        if avg_vol == 0:
            return 0
        
        return (recent_vol / avg_vol - 1) * 100
    
    def _generate_thesis(self, vol_score: float, mom_score: float, 
                         rs_score: float, setup_type: str) -> str:
        """Generate human-readable thesis."""
        reasons = []
        
        if vol_score >= 70:
            reasons.append("Heavy accumulation")
        elif vol_score >= 55:
            reasons.append("Volume building")
        
        if mom_score >= 70:
            reasons.append("Strong momentum")
        
        if rs_score >= 70:
            reasons.append("Outperforming SPY")
        
        if setup_type == "BREAKOUT":
            reasons.append("Fresh breakout")
        elif setup_type == "PULLBACK":
            reasons.append("Pullback to support")
        elif setup_type == "CONSOLIDATION":
            reasons.append("Tight consolidation")
        elif setup_type == "EXTENDED":
            reasons.append("Extended - wait for pullback")
        
        return " + ".join(reasons) if reasons else "Mixed signals"


def format_scan_results(results: List[Dict]) -> str:
    """Format scan results for display/alert."""
    if not results:
        return "No opportunities found meeting criteria."
    
    output = []
    output.append(f"TOP {len(results)} OPPORTUNITIES")
    output.append(f"Scanned at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    output.append("=" * 50)
    
    for i, r in enumerate(results, 1):
        output.append(f"""
{i}. {r['name']} ({r['ticker']})
   Price: ${r['price']:.2f} | MCap: ${r['market_cap_b']:.1f}B
   Edge Score: {r['edge_score']}/100
   
   5D: {r['mom_5d']:+.1f}% | 20D: {r['mom_20d']:+.1f}%
   Volume: {r['volume_change']:+.1f}% vs avg
   Setup: {r['setup_type']}
   
   Support: ${r['support']:.2f} | Resistance: ${r['resistance']:.2f}
   Why: {r['why']}
""")
    
    return "\n".join(output)


if __name__ == "__main__":
    scanner = UniverseScanner(include_mid_caps=True)
    results = scanner.scan(top_n=10)
    print(format_scan_results(results))

