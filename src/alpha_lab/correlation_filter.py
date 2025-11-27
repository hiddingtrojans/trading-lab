#!/usr/bin/env python3
"""
Correlation Filter
==================

Prevents over-concentration by checking correlation between:
- New trade candidate vs existing positions
- Candidates in a batch screening

Rules:
- Skip if correlation > 0.80 with any existing position
- In batch, keep only the strongest uncorrelated picks

Usage:
    from alpha_lab.correlation_filter import CorrelationFilter
    
    cf = CorrelationFilter()
    cf.set_positions(['NVDA', 'AMD'])
    
    # Check single candidate
    if cf.is_allowed('TSM'):
        # Trade TSM
    
    # Filter batch
    filtered = cf.filter_batch(['AAPL', 'MSFT', 'GOOGL', 'AMD'])
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta


class CorrelationFilter:
    """
    Filters trade candidates based on correlation with existing positions.
    """
    
    def __init__(self, max_correlation: float = 0.80, lookback_days: int = 60):
        """
        Args:
            max_correlation: Maximum allowed correlation (default 0.80)
            lookback_days: Days of history to calculate correlation
        """
        self.max_correlation = max_correlation
        self.lookback_days = lookback_days
        self.positions: List[str] = []
        self._price_cache: Dict[str, pd.Series] = {}
        self._correlation_cache: Dict[Tuple[str, str], float] = {}
        
    def set_positions(self, positions: List[str]):
        """Set current portfolio positions."""
        self.positions = [p.upper() for p in positions]
        self._correlation_cache.clear()  # Clear cache when positions change
    
    def _get_prices(self, ticker: str) -> Optional[pd.Series]:
        """Get price series for a ticker (cached)."""
        if ticker in self._price_cache:
            return self._price_cache[ticker]
        
        try:
            import yfinance as yf
            
            end = datetime.now()
            start = end - timedelta(days=self.lookback_days * 1.5)  # Extra for trading days
            
            data = yf.download(
                ticker, start=start, end=end, 
                progress=False, auto_adjust=True
            )
            
            if data.empty:
                return None
            
            # Handle MultiIndex columns
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            prices = data['Close'].dropna()
            self._price_cache[ticker] = prices
            return prices
            
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            return None
    
    def calculate_correlation(self, ticker1: str, ticker2: str) -> float:
        """Calculate correlation between two tickers."""
        # Check cache
        cache_key = tuple(sorted([ticker1.upper(), ticker2.upper()]))
        if cache_key in self._correlation_cache:
            return self._correlation_cache[cache_key]
        
        prices1 = self._get_prices(ticker1.upper())
        prices2 = self._get_prices(ticker2.upper())
        
        if prices1 is None or prices2 is None:
            return 0.0  # Assume uncorrelated if data unavailable
        
        # Align dates
        common_idx = prices1.index.intersection(prices2.index)
        if len(common_idx) < 20:
            return 0.0  # Not enough data
        
        # Calculate returns
        returns1 = prices1.loc[common_idx].pct_change().dropna()
        returns2 = prices2.loc[common_idx].pct_change().dropna()
        
        # Correlation
        corr = returns1.corr(returns2)
        
        # Cache result
        self._correlation_cache[cache_key] = corr
        
        return corr
    
    def get_max_correlation_with_positions(self, ticker: str) -> Tuple[float, Optional[str]]:
        """
        Get highest correlation between ticker and any existing position.
        
        Returns:
            Tuple of (max_correlation, most_correlated_ticker)
        """
        if not self.positions:
            return 0.0, None
        
        ticker = ticker.upper()
        
        # Skip if already in positions
        if ticker in self.positions:
            return 1.0, ticker
        
        max_corr = 0.0
        max_ticker = None
        
        for pos in self.positions:
            corr = self.calculate_correlation(ticker, pos)
            if abs(corr) > abs(max_corr):
                max_corr = corr
                max_ticker = pos
        
        return max_corr, max_ticker
    
    def is_allowed(self, ticker: str) -> Tuple[bool, str]:
        """
        Check if ticker passes correlation filter.
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        max_corr, corr_with = self.get_max_correlation_with_positions(ticker)
        
        if abs(max_corr) > self.max_correlation:
            return False, f"High correlation ({max_corr:.2f}) with {corr_with}"
        
        return True, f"OK (max corr: {max_corr:.2f})"
    
    def filter_batch(self, candidates: List[str], scores: Dict[str, float] = None) -> List[str]:
        """
        Filter a batch of candidates to remove highly correlated picks.
        
        Keeps the highest-scoring uncorrelated candidates.
        
        Args:
            candidates: List of ticker candidates
            scores: Optional dict of ticker -> score (higher = better)
        
        Returns:
            Filtered list of tickers
        """
        if not candidates:
            return []
        
        # Default scores: equal priority
        if scores is None:
            scores = {t: 1.0 for t in candidates}
        
        # Sort by score (highest first)
        sorted_candidates = sorted(candidates, key=lambda t: scores.get(t, 0), reverse=True)
        
        filtered = []
        
        for ticker in sorted_candidates:
            ticker = ticker.upper()
            
            # Check against positions
            allowed, reason = self.is_allowed(ticker)
            if not allowed:
                print(f"  Skipping {ticker}: {reason}")
                continue
            
            # Check against already-selected candidates
            correlated_with_selected = False
            for selected in filtered:
                corr = self.calculate_correlation(ticker, selected)
                if abs(corr) > self.max_correlation:
                    print(f"  Skipping {ticker}: correlated ({corr:.2f}) with {selected}")
                    correlated_with_selected = True
                    break
            
            if not correlated_with_selected:
                filtered.append(ticker)
        
        return filtered
    
    def get_correlation_matrix(self, tickers: List[str]) -> pd.DataFrame:
        """Get correlation matrix for a list of tickers."""
        n = len(tickers)
        matrix = np.zeros((n, n))
        
        for i, t1 in enumerate(tickers):
            for j, t2 in enumerate(tickers):
                if i == j:
                    matrix[i, j] = 1.0
                elif i < j:
                    corr = self.calculate_correlation(t1, t2)
                    matrix[i, j] = corr
                    matrix[j, i] = corr
        
        return pd.DataFrame(matrix, index=tickers, columns=tickers)
    
    def analyze_portfolio(self, positions: List[str] = None) -> Dict:
        """
        Analyze portfolio for concentration risk.
        
        Returns dict with:
            - correlation_matrix: Full correlation matrix
            - high_correlations: List of highly correlated pairs
            - diversification_score: 0-100 (higher = more diversified)
        """
        if positions is None:
            positions = self.positions
        
        if len(positions) < 2:
            return {
                'correlation_matrix': None,
                'high_correlations': [],
                'diversification_score': 100
            }
        
        matrix = self.get_correlation_matrix(positions)
        
        # Find high correlations
        high_corrs = []
        for i, t1 in enumerate(positions):
            for j, t2 in enumerate(positions):
                if i < j:
                    corr = matrix.loc[t1, t2]
                    if abs(corr) > self.max_correlation:
                        high_corrs.append({
                            'ticker1': t1,
                            'ticker2': t2,
                            'correlation': corr
                        })
        
        # Calculate diversification score
        # Average of (1 - abs(correlation)) for all pairs
        n = len(positions)
        total_corr = 0
        pairs = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                total_corr += abs(matrix.iloc[i, j])
                pairs += 1
        
        avg_corr = total_corr / pairs if pairs > 0 else 0
        div_score = (1 - avg_corr) * 100
        
        return {
            'correlation_matrix': matrix,
            'high_correlations': high_corrs,
            'diversification_score': div_score,
            'avg_correlation': avg_corr
        }
    
    def print_analysis(self, positions: List[str] = None):
        """Print portfolio correlation analysis."""
        analysis = self.analyze_portfolio(positions)
        
        print(f"\n{'='*60}")
        print("PORTFOLIO CORRELATION ANALYSIS")
        print('='*60)
        
        print(f"\nDiversification Score: {analysis['diversification_score']:.1f}/100")
        print(f"Average Correlation: {analysis['avg_correlation']:.2f}")
        
        if analysis['high_correlations']:
            print(f"\nHigh Correlations (>{self.max_correlation}):")
            for pair in analysis['high_correlations']:
                print(f"  {pair['ticker1']} <-> {pair['ticker2']}: {pair['correlation']:.2f}")
        else:
            print("\nNo highly correlated pairs found.")
        
        if analysis['correlation_matrix'] is not None:
            print("\nCorrelation Matrix:")
            print(analysis['correlation_matrix'].round(2).to_string())
        
        print('='*60)


if __name__ == "__main__":
    # Test correlation filter
    cf = CorrelationFilter(max_correlation=0.80)
    
    # Set existing positions
    cf.set_positions(['NVDA', 'AMD'])
    
    print("Testing correlation filter...")
    print(f"Positions: {cf.positions}")
    
    # Test single candidates
    for ticker in ['TSM', 'INTC', 'AAPL', 'GOOGL']:
        allowed, reason = cf.is_allowed(ticker)
        status = "ALLOWED" if allowed else "BLOCKED"
        print(f"  {ticker}: {status} - {reason}")
    
    # Test batch filtering
    candidates = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSM', 'INTC']
    print(f"\nFiltering batch: {candidates}")
    filtered = cf.filter_batch(candidates)
    print(f"Result: {filtered}")
    
    # Analyze portfolio
    cf.print_analysis(['NVDA', 'AMD', 'TSM', 'AAPL'])

