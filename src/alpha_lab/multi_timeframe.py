#!/usr/bin/env python3
"""
Multi-Timeframe Confirmation
============================

Checks trend alignment across multiple timeframes before entry.
Only take trades when Daily + Weekly trends agree.

Timeframes:
- Intraday (5m/15m): Entry timing
- Daily: Primary trend
- Weekly: Major trend (backdrop)

Rules:
- Long: Price > SMA on Daily AND Weekly
- Short: Price < SMA on Daily AND Weekly
- If mixed: No trade (choppy market)

Usage:
    from alpha_lab.multi_timeframe import MultiTimeframeAnalyzer
    
    mtf = MultiTimeframeAnalyzer()
    signal = mtf.analyze('NVDA')
    
    if signal['aligned']:
        # Take trade
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MultiTimeframeAnalyzer:
    """
    Analyzes trend across multiple timeframes for confirmation.
    """
    
    def __init__(self, sma_period: int = 20):
        """
        Args:
            sma_period: SMA period for trend detection (default 20)
        """
        self.sma_period = sma_period
        self._cache: Dict[str, Dict] = {}
    
    def _get_data(self, ticker: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch OHLCV data."""
        try:
            import yfinance as yf
            
            data = yf.download(
                ticker, period=period, interval=interval,
                progress=False, auto_adjust=True
            )
            
            if data.empty:
                return None
            
            # Handle MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            data.columns = [c.lower() for c in data.columns]
            return data
            
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            return None
    
    def _detect_trend(self, data: pd.DataFrame) -> Tuple[Trend, Dict]:
        """
        Detect trend from price data.
        
        Returns:
            Tuple of (Trend, details_dict)
        """
        if data is None or len(data) < self.sma_period:
            return Trend.NEUTRAL, {'reason': 'Insufficient data'}
        
        # Calculate SMAs
        sma_short = data['close'].rolling(self.sma_period).mean()
        sma_long = data['close'].rolling(self.sma_period * 2).mean()
        
        current_price = data['close'].iloc[-1]
        current_sma_short = sma_short.iloc[-1]
        current_sma_long = sma_long.iloc[-1] if len(sma_long.dropna()) >= 1 else current_sma_short
        
        # Price position relative to SMAs
        above_short = current_price > current_sma_short
        above_long = current_price > current_sma_long
        sma_rising = sma_short.iloc[-1] > sma_short.iloc[-5] if len(sma_short) > 5 else True
        
        # Calculate strength
        distance_from_sma = (current_price - current_sma_short) / current_sma_short * 100
        
        details = {
            'price': current_price,
            'sma_short': current_sma_short,
            'sma_long': current_sma_long,
            'distance_pct': distance_from_sma,
            'sma_rising': sma_rising
        }
        
        # Determine trend
        if above_short and above_long and sma_rising:
            return Trend.BULLISH, details
        elif not above_short and not above_long and not sma_rising:
            return Trend.BEARISH, details
        else:
            return Trend.NEUTRAL, details
    
    def analyze(self, ticker: str) -> Dict:
        """
        Analyze ticker across multiple timeframes.
        
        Returns dict with:
            - daily: Daily trend analysis
            - weekly: Weekly trend analysis
            - aligned: Whether trends are aligned
            - direction: Overall direction if aligned
            - strength: Trend strength (0-100)
            - recommendation: Trade recommendation
        """
        ticker = ticker.upper()
        
        # Daily analysis
        daily_data = self._get_data(ticker, period="6mo", interval="1d")
        daily_trend, daily_details = self._detect_trend(daily_data)
        
        # Weekly analysis
        weekly_data = self._get_data(ticker, period="2y", interval="1wk")
        weekly_trend, weekly_details = self._detect_trend(weekly_data)
        
        # Check alignment
        aligned = False
        direction = None
        
        if daily_trend == weekly_trend and daily_trend != Trend.NEUTRAL:
            aligned = True
            direction = daily_trend.value
        
        # Calculate strength
        strength = self._calculate_strength(daily_details, weekly_details, aligned)
        
        # Generate recommendation
        recommendation = self._get_recommendation(aligned, direction, strength)
        
        result = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'daily': {
                'trend': daily_trend.value,
                **daily_details
            },
            'weekly': {
                'trend': weekly_trend.value,
                **weekly_details
            },
            'aligned': aligned,
            'direction': direction,
            'strength': strength,
            'recommendation': recommendation
        }
        
        self._cache[ticker] = result
        return result
    
    def _calculate_strength(self, daily: Dict, weekly: Dict, aligned: bool) -> float:
        """Calculate trend strength score (0-100)."""
        if not aligned:
            return 0
        
        score = 50  # Base score for alignment
        
        # Daily contribution (up to 25 points)
        daily_dist = abs(daily.get('distance_pct', 0))
        if daily_dist > 5:
            score += 25
        elif daily_dist > 2:
            score += 15
        elif daily_dist > 1:
            score += 10
        
        # Weekly contribution (up to 25 points)
        weekly_dist = abs(weekly.get('distance_pct', 0))
        if weekly_dist > 10:
            score += 25
        elif weekly_dist > 5:
            score += 15
        elif weekly_dist > 2:
            score += 10
        
        return min(100, score)
    
    def _get_recommendation(self, aligned: bool, direction: str, strength: float) -> str:
        """Generate trade recommendation."""
        if not aligned:
            return "NO_TRADE - Timeframes not aligned"
        
        if strength >= 80:
            return f"STRONG_{direction.upper()} - High conviction"
        elif strength >= 60:
            return f"{direction.upper()} - Normal size"
        else:
            return f"WEAK_{direction.upper()} - Reduced size"
    
    def check_entry(self, ticker: str, direction: str = "long") -> Tuple[bool, str]:
        """
        Quick check if entry is allowed.
        
        Args:
            ticker: Stock symbol
            direction: 'long' or 'short'
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        analysis = self.analyze(ticker)
        
        if not analysis['aligned']:
            return False, f"Trends not aligned (Daily: {analysis['daily']['trend']}, Weekly: {analysis['weekly']['trend']})"
        
        if direction == "long" and analysis['direction'] != "bullish":
            return False, f"Trend is {analysis['direction']}, not bullish"
        
        if direction == "short" and analysis['direction'] != "bearish":
            return False, f"Trend is {analysis['direction']}, not bearish"
        
        return True, f"Aligned {analysis['direction']} trend (Strength: {analysis['strength']:.0f})"
    
    def print_analysis(self, ticker: str):
        """Print formatted analysis."""
        analysis = self.analyze(ticker)
        
        print(f"\n{'='*60}")
        print(f"MULTI-TIMEFRAME ANALYSIS: {ticker}")
        print('='*60)
        
        # Daily
        d = analysis['daily']
        print(f"\nDaily Trend: {d['trend'].upper()}")
        print(f"  Price: ${d['price']:.2f}")
        print(f"  SMA{self.sma_period}: ${d['sma_short']:.2f}")
        print(f"  Distance: {d['distance_pct']:+.1f}%")
        print(f"  Rising: {'Yes' if d.get('sma_rising') else 'No'}")
        
        # Weekly
        w = analysis['weekly']
        print(f"\nWeekly Trend: {w['trend'].upper()}")
        print(f"  Price: ${w['price']:.2f}")
        print(f"  SMA{self.sma_period}: ${w['sma_short']:.2f}")
        print(f"  Distance: {w['distance_pct']:+.1f}%")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"ALIGNED: {'YES' if analysis['aligned'] else 'NO'}")
        if analysis['aligned']:
            print(f"DIRECTION: {analysis['direction'].upper()}")
            print(f"STRENGTH: {analysis['strength']:.0f}/100")
        print(f"RECOMMENDATION: {analysis['recommendation']}")
        print('='*60)


def batch_analyze(tickers: list, min_strength: float = 60) -> list:
    """
    Analyze multiple tickers and return only aligned ones.
    
    Args:
        tickers: List of tickers
        min_strength: Minimum strength score to include
    
    Returns:
        List of dicts for aligned tickers sorted by strength
    """
    mtf = MultiTimeframeAnalyzer()
    results = []
    
    for ticker in tickers:
        try:
            analysis = mtf.analyze(ticker)
            if analysis['aligned'] and analysis['strength'] >= min_strength:
                results.append(analysis)
        except Exception as e:
            print(f"  Error analyzing {ticker}: {e}")
    
    # Sort by strength
    results.sort(key=lambda x: x['strength'], reverse=True)
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = "NVDA"
    
    mtf = MultiTimeframeAnalyzer()
    mtf.print_analysis(ticker)
    
    # Quick entry check
    print(f"\nLong Entry Check:")
    allowed, reason = mtf.check_entry(ticker, "long")
    print(f"  {'ALLOWED' if allowed else 'BLOCKED'}: {reason}")

