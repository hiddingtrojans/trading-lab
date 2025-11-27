#!/usr/bin/env python3
"""
Sector Rotation Analysis Module
===============================

Implements institutional-grade sector rotation analysis.
Identifies which sectors are outperforming the market (SPY) to filter trade ideas.

Logic based on Relative Rotation Graphs (RRG) concepts:
1. Relative Strength (RS) = Sector Price / SPY Price
2. Momentum = Rate of Change of RS
3. Classification: Leading, Weakening, Lagging, Improving
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

# Add src to path
# Go up two levels from src/alpha_lab/sector_rotation.py to get to project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
# Insert at 0 to prioritize project src over local alpha_lab modules
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.data_fetcher import DataFetcher

class SectorRotationAnalyzer:
    """Analyzes sector trends relative to the broad market."""
    
    SECTORS = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLV': 'Healthcare',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLC': 'Communication Services',
        'XLB': 'Materials',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate'
    }
    
    def __init__(self, fetcher: DataFetcher = None):
        """
        Initialize analyzer.
        
        Args:
            fetcher: Optional DataFetcher instance. If None, creates a new one.
        """
        self.fetcher = fetcher if fetcher else DataFetcher(None)
        
    def get_sector_data(self, days: int = 120) -> Dict[str, pd.DataFrame]:
        """Fetch daily data for all sectors + SPY."""
        data = {}
        tickers = list(self.SECTORS.keys()) + ['SPY']
        
        # print(f"  Fetching sector data ({len(tickers)} ETFs)...")
        
        # We can fetch sequentially or use a batch fetch if DataFetcher supported it.
        # For now, sequential with cache via DataFetcher is fine.
        # We use yfinance fallback mostly as IBKR might throttle 12 requests quickly.
        
        for ticker in tickers:
            df = self.fetcher.get_intraday_data(ticker, days=days)
            if not df.empty:
                # Resample to daily if needed (DataFetcher returns 5m or 1h mostly)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                daily = df['close'].resample('D').last().dropna()
                data[ticker] = daily
                
        return data

    def calculate_relative_strength(self, sector_prices: pd.Series, market_prices: pd.Series) -> pd.DataFrame:
        """
        Calculate Relative Strength and Momentum.
        
        Returns:
            DataFrame with columns: ['rs_ratio', 'rs_momentum']
        """
        # Align dates
        df = pd.DataFrame({'sector': sector_prices, 'market': market_prices}).dropna()
        
        if len(df) < 50:
            return pd.DataFrame()
            
        # 1. Relative Strength Ratio (Price vs Market)
        # Simple ratio
        df['rs_raw'] = df['sector'] / df['market']
        
        # Normalize using a moving average (100 day) to center around 100
        # RRG standard: (RS / MovingAvg(RS)) * 100
        df['rs_ratio'] = 100 + ((df['rs_raw'] - df['rs_raw'].rolling(window=20).mean()) / df['rs_raw'].rolling(window=20).std()) * 10
        # Simplified normalization: Z-score * 10 + 100
        
        # 2. RS Momentum (Rate of Change of the Ratio)
        # RRG uses 10-day ROC of the Ratio
        df['rs_momentum'] = 100 + ((df['rs_ratio'] - df['rs_ratio'].rolling(window=10).mean()) / df['rs_ratio'].rolling(window=10).std()) * 10
        
        return df[['rs_ratio', 'rs_momentum']].dropna()

    def analyze_sectors(self) -> Dict:
        """
        Perform full sector analysis.
        
        Returns:
            Dictionary of sector classifications and top picks.
        """
        data = self.get_sector_data()
        if 'SPY' not in data:
            return {'error': 'Market data (SPY) missing'}
            
        market = data['SPY']
        results = []
        
        for ticker, name in self.SECTORS.items():
            if ticker not in data:
                continue
                
            sector_px = data[ticker]
            metrics = self.calculate_relative_strength(sector_px, market)
            
            if metrics.empty:
                continue
                
            last = metrics.iloc[-1]
            ratio = last['rs_ratio']
            momentum = last['rs_momentum']
            
            # RRG Classification Logic
            # Leading: Ratio > 100, Momentum > 100 (Strong trend, getting stronger)
            # Weakening: Ratio > 100, Momentum < 100 (Strong trend, losing steam)
            # Lagging: Ratio < 100, Momentum < 100 (Weak trend, getting weaker)
            # Improving: Ratio < 100, Momentum > 100 (Weak trend, gaining strength)
            
            status = "Unknown"
            score = 0
            
            if ratio > 100 and momentum > 100:
                status = "LEADING"
                score = 90 + (ratio - 100) + (momentum - 100)
            elif ratio > 100 and momentum < 100:
                status = "WEAKENING"
                score = 70
            elif ratio < 100 and momentum < 100:
                status = "LAGGING"
                score = 30
            elif ratio < 100 and momentum > 100:
                status = "IMPROVING"
                score = 60
            
            results.append({
                'ticker': ticker,
                'name': name,
                'status': status,
                'rs_ratio': round(ratio, 2),
                'rs_momentum': round(momentum, 2),
                'score': round(score, 2)
            })
            
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        top_sectors = [r['name'] for r in results if r['status'] == 'LEADING']
        
        return {
            'rankings': results,
            'leading_sectors': top_sectors,
            'timestamp': pd.Timestamp.now().isoformat()
        }

if __name__ == "__main__":
    # Simple test
    print("Analyzing Sectors...")
    analyzer = SectorRotationAnalyzer()
    results = analyzer.analyze_sectors()
    
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        print(f"\n{'Sector':<25} {'Status':<12} {'Score':<6} {'Ratio':<6} {'Mom':<6}")
        print("-" * 60)
        for r in results['rankings']:
            print(f"{r['name']:<25} {r['status']:<12} {r['score']:<6} {r['rs_ratio']:<6} {r['rs_momentum']:<6}")
            
        print("\n🔥 LEADING SECTORS (Focus Longs Here):")
        print(", ".join(results['leading_sectors']))

