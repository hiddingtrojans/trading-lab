#!/usr/bin/env python3
"""
Sector-Weighted Screener
========================

Enhances fundamental scores by weighting them with sector strength.
Prioritizes stocks in leading sectors.

Logic:
- Base Score: Fundamental analysis (0-100)
- Sector Multiplier: Based on sector relative strength
  - LEADING sector: 1.2x
  - IMPROVING sector: 1.1x
  - WEAKENING sector: 0.9x
  - LAGGING sector: 0.8x

Final Score = Base Score * Sector Multiplier

Usage:
    from alpha_lab.sector_weighted_screener import SectorWeightedScreener
    
    screener = SectorWeightedScreener()
    results = screener.screen(['AAPL', 'XOM', 'JPM', 'NVDA'])
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime


# Sector to ETF mapping
SECTOR_ETF_MAP = {
    'Technology': 'XLK',
    'Financial Services': 'XLF',
    'Financials': 'XLF',
    'Healthcare': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Consumer Defensive': 'XLP',
    'Energy': 'XLE',
    'Industrials': 'XLI',
    'Communication Services': 'XLC',
    'Basic Materials': 'XLB',
    'Utilities': 'XLU',
    'Real Estate': 'XLRE'
}

# Sector status multipliers
SECTOR_MULTIPLIERS = {
    'LEADING': 1.20,
    'IMPROVING': 1.10,
    'WEAKENING': 0.90,
    'LAGGING': 0.80,
    'Unknown': 1.00,
    'Neutral': 1.00
}


class SectorWeightedScreener:
    """
    Screens stocks with sector-adjusted scoring.
    """
    
    def __init__(self):
        self._sector_cache: Dict[str, Dict] = {}
        self._fundamentals_cache: Dict[str, Dict] = {}
        self._sector_analyzer = None
    
    def _get_sector_analyzer(self):
        """Lazy load sector analyzer."""
        if self._sector_analyzer is None:
            from alpha_lab.sector_rotation import SectorRotationAnalyzer
            from utils.data_fetcher import DataFetcher
            
            fetcher = DataFetcher(None)
            self._sector_analyzer = SectorRotationAnalyzer(fetcher)
        
        return self._sector_analyzer
    
    def _get_sector_status(self, sector_name: str) -> Dict:
        """Get sector status and multiplier."""
        if sector_name in self._sector_cache:
            return self._sector_cache[sector_name]
        
        etf = SECTOR_ETF_MAP.get(sector_name, 'SPY')
        
        try:
            analyzer = self._get_sector_analyzer()
            results = analyzer.analyze_sectors()
            
            for rank in results.get('rankings', []):
                if rank['ticker'] == etf:
                    status = rank.get('status', 'Unknown')
                    self._sector_cache[sector_name] = {
                        'etf': etf,
                        'status': status,
                        'score': rank.get('score', 50),
                        'multiplier': SECTOR_MULTIPLIERS.get(status, 1.0)
                    }
                    return self._sector_cache[sector_name]
        except Exception as e:
            print(f"  Error getting sector status: {e}")
        
        return {
            'etf': etf,
            'status': 'Unknown',
            'score': 50,
            'multiplier': 1.0
        }
    
    def _get_fundamentals(self, ticker: str) -> Dict:
        """Get fundamental metrics for a ticker."""
        if ticker in self._fundamentals_cache:
            return self._fundamentals_cache[ticker]
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Calculate base score (simplified version)
            score = 0
            
            # Revenue growth (0-25)
            rev_growth = info.get('revenueGrowth', 0) or 0
            if rev_growth > 0.4:
                score += 25
            elif rev_growth > 0.2:
                score += 20
            elif rev_growth > 0.1:
                score += 15
            elif rev_growth > 0:
                score += 10
            
            # Earnings (0-25)
            pe = info.get('forwardPE') or info.get('trailingPE') or 0
            earn_growth = info.get('earningsGrowth', 0) or 0
            
            if pe > 0 and earn_growth > 0.3:
                score += 25
            elif pe > 0 and earn_growth > 0.15:
                score += 20
            elif pe > 0 and earn_growth > 0:
                score += 15
            elif pe > 0:
                score += 10
            
            # Margins (0-25)
            gross_margin = info.get('grossMargins', 0) or 0
            if gross_margin > 0.6:
                score += 25
            elif gross_margin > 0.4:
                score += 20
            elif gross_margin > 0.25:
                score += 15
            elif gross_margin > 0.1:
                score += 10
            
            # Valuation (0-25)
            if pe > 0:
                if pe < 15:
                    score += 25
                elif pe < 25:
                    score += 20
                elif pe < 35:
                    score += 10
            
            result = {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'price': info.get('currentPrice') or info.get('previousClose', 0),
                'revenue_growth': rev_growth,
                'earnings_growth': earn_growth,
                'gross_margin': gross_margin,
                'pe_ratio': pe,
                'base_score': score
            }
            
            self._fundamentals_cache[ticker] = result
            return result
            
        except Exception as e:
            print(f"  Error getting fundamentals for {ticker}: {e}")
            return {
                'ticker': ticker,
                'sector': 'Unknown',
                'base_score': 0,
                'error': str(e)
            }
    
    def analyze_ticker(self, ticker: str) -> Dict:
        """
        Analyze a single ticker with sector weighting.
        
        Returns dict with:
            - base_score: Raw fundamental score
            - sector_status: Sector strength
            - sector_multiplier: Applied multiplier
            - weighted_score: Final adjusted score
        """
        fundamentals = self._get_fundamentals(ticker)
        sector = fundamentals.get('sector', 'Unknown')
        sector_data = self._get_sector_status(sector)
        
        base_score = fundamentals.get('base_score', 0)
        multiplier = sector_data.get('multiplier', 1.0)
        weighted_score = min(100, base_score * multiplier)
        
        return {
            **fundamentals,
            'sector_etf': sector_data['etf'],
            'sector_status': sector_data['status'],
            'sector_score': sector_data['score'],
            'sector_multiplier': multiplier,
            'weighted_score': weighted_score
        }
    
    def screen(self, tickers: List[str], min_score: float = 60) -> List[Dict]:
        """
        Screen multiple tickers with sector weighting.
        
        Args:
            tickers: List of ticker symbols
            min_score: Minimum weighted score to include
        
        Returns:
            List of analysis dicts, sorted by weighted_score
        """
        results = []
        
        print(f"\nScreening {len(tickers)} tickers with sector weighting...")
        
        for ticker in tickers:
            try:
                analysis = self.analyze_ticker(ticker.upper())
                
                if analysis.get('weighted_score', 0) >= min_score:
                    results.append(analysis)
                    
            except Exception as e:
                print(f"  Error with {ticker}: {e}")
        
        # Sort by weighted score
        results.sort(key=lambda x: x.get('weighted_score', 0), reverse=True)
        
        return results
    
    def print_results(self, results: List[Dict], top_n: int = 10):
        """Print formatted screening results."""
        print(f"\n{'='*80}")
        print("SECTOR-WEIGHTED SCREENING RESULTS")
        print('='*80)
        
        print(f"\n{'Ticker':<8} {'Name':<25} {'Sector':<15} {'Base':>6} {'Mult':>6} {'Final':>6}")
        print('-'*80)
        
        for r in results[:top_n]:
            name = r.get('name', r['ticker'])[:24]
            sector_status = r.get('sector_status', 'UNK')[:3]
            
            print(f"{r['ticker']:<8} {name:<25} {sector_status:<15} "
                  f"{r.get('base_score', 0):>5.0f} "
                  f"{r.get('sector_multiplier', 1.0):>5.2f}x "
                  f"{r.get('weighted_score', 0):>5.0f}")
        
        if len(results) > top_n:
            print(f"\n... and {len(results) - top_n} more")
        
        print('='*80)
        
        # Sector summary
        sectors = {}
        for r in results:
            sector = r.get('sector_status', 'Unknown')
            if sector not in sectors:
                sectors[sector] = 0
            sectors[sector] += 1
        
        print("\nBy Sector Status:")
        for status, count in sorted(sectors.items(), key=lambda x: -x[1]):
            print(f"  {status}: {count} stocks")


if __name__ == "__main__":
    # Test screening
    test_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        'JPM', 'BAC', 'GS',
        'XOM', 'CVX', 'SLB',
        'JNJ', 'PFE', 'UNH',
        'CAT', 'BA', 'UNP'
    ]
    
    screener = SectorWeightedScreener()
    results = screener.screen(test_tickers, min_score=50)
    screener.print_results(results)

