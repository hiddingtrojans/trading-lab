#!/usr/bin/env python3
"""
Market Regime Analysis Module
=============================

Determines the overall market environment ("Traffic Light") to filter trades.
Most strategies fail not because the signal is bad, but because the market is wrong.

Regime Classification:
- GREEN:  Bullish trend, low volatility, strong breadth. (Go Aggressive)
- YELLOW: Choppy/Sideways, moderate volatility. (Reduce Size / Be Selective)
- RED:    Bearish trend, high volatility. (Cash is King / Short Only)

Inputs:
- SPY Trend (SMA 20/50/200)
- VIX Level (Volatility)
- Sector Breadth (Participation)
- RSI (Momentum)
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import sys
import os

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.data_fetcher import DataFetcher
from alpha_lab.sector_rotation import SectorRotationAnalyzer

class MarketRegimeAnalyzer:
    """Analyzes market health to generate a trading permission signal."""
    
    def __init__(self, fetcher: DataFetcher = None):
        self.fetcher = fetcher if fetcher else DataFetcher(None)
        self.sector_analyzer = SectorRotationAnalyzer(self.fetcher)
        
    def _get_indicator_data(self, days: int = 300) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for market indicators."""
        # SPY for trend, ^VIX for volatility
        # Note: yfinance ticker for VIX is ^VIX
        tickers = ['SPY', '^VIX']
        data = {}
        
        for t in tickers:
            df = self.fetcher.get_intraday_data(t, days=days)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                # Resample to daily closes for indicators
                daily = df['close'].resample('D').last().dropna()
                data[t] = daily
                
        return data

    def analyze_regime(self) -> Dict:
        """
        Calculate comprehensive market regime.
        
        Returns:
            Dict containing status (GREEN/YELLOW/RED), score (0-100), and factors.
        """
        data = self._get_indicator_data()
        spy = data.get('SPY')
        vix = data.get('^VIX')
        
        if spy is None or len(spy) < 200:
            return {'status': 'UNKNOWN', 'score': 50, 'reason': 'Insufficient Data'}
            
        # 1. Trend Score (0-40 pts)
        current_price = spy.iloc[-1]
        sma_20 = spy.rolling(window=20).mean().iloc[-1]
        sma_50 = spy.rolling(window=50).mean().iloc[-1]
        sma_200 = spy.rolling(window=200).mean().iloc[-1]
        
        trend_score = 0
        if current_price > sma_20: trend_score += 10
        if current_price > sma_50: trend_score += 10
        if current_price > sma_200: trend_score += 10
        if sma_20 > sma_50: trend_score += 10  # Golden alignment
        
        # 2. Volatility Score (0-30 pts)
        # VIX: Lower is better for Longs
        vix_val = vix.iloc[-1] if vix is not None else 20
        
        vol_score = 0
        if vix_val < 15: vol_score = 30      # Calm
        elif vix_val < 20: vol_score = 20    # Normal
        elif vix_val < 25: vol_score = 10    # Elevated
        else: vol_score = 0                  # Panic
        
        # 3. Breadth Score (0-30 pts)
        # Use Sector Rotation module to count leading sectors
        try:
            sector_data = self.sector_analyzer.analyze_sectors()
            leading_count = len([s for s in sector_data.get('rankings', []) if s['status'] == 'LEADING'])
            improving_count = len([s for s in sector_data.get('rankings', []) if s['status'] == 'IMPROVING'])
            
            # Max 11 sectors
            bullish_sectors = leading_count + (0.5 * improving_count)
            breadth_score = min(30, (bullish_sectors / 6) * 30) # >6 sectors bullish = max score
        except:
            breadth_score = 15 # Neutral fallback
            
        # Total Score
        total_score = trend_score + vol_score + breadth_score
        
        # Classification
        if total_score >= 75:
            status = "GREEN"
            action = "Aggressive Longs"
        elif total_score >= 40:
            status = "YELLOW"
            action = "Selective / Reduced Size"
        else:
            status = "RED"
            action = "Cash / Defensive / Short"
            
        return {
            'status': status,
            'score': round(total_score, 1),
            'action': action,
            'factors': {
                'trend_score': trend_score,
                'volatility_score': vol_score,
                'breadth_score': round(breadth_score, 1),
                'spy_price': round(current_price, 2),
                'sma_200': round(sma_200, 2),
                'vix': round(vix_val, 2)
            }
        }

if __name__ == "__main__":
    print("Analyzing Market Regime...")
    analyzer = MarketRegimeAnalyzer()
    res = analyzer.analyze_regime()
    
    print(f"\n🚦 MARKET STATUS: {res['status']} (Score: {res['score']}/100)")
    print(f"📝 Action: {res['action']}")
    print("\nFactors:")
    print(f"  • Trend: {res['factors']['trend_score']}/40 (SPY vs SMAs)")
    print(f"  • Volatility: {res['factors']['volatility_score']}/30 (VIX: {res['factors']['vix']})")
    print(f"  • Breadth: {res['factors']['breadth_score']}/30 (Sector Participation)")

