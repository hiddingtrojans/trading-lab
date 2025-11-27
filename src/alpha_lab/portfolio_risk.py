#!/usr/bin/env python3
"""
Portfolio Risk & Heat Check Module
==================================

Analyzes a portfolio for hidden risks:
1. Correlation Clusters: Are you just 100% long Tech?
2. Beta Exposure: How much will you lose if SPY drops 1%?
3. Volatility Risk: Value at Risk (VaR).

Usage:
    python portfolio_risk.py --tickers NVDA,AMD,TSM,MSFT
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import os
from typing import List, Dict

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.data_fetcher import DataFetcher

class PortfolioRiskAnalyzer:
    """Analyzes portfolio risk metrics."""
    
    def __init__(self, fetcher: DataFetcher = None):
        self.fetcher = fetcher if fetcher else DataFetcher(None)
        
    def analyze_portfolio(self, tickers: List[str], benchmark: str = 'SPY') -> Dict:
        """
        Run full risk analysis on a list of tickers.
        """
        if not tickers:
            return {'error': 'No tickers provided'}
            
        # clean tickers
        tickers = [t.strip().upper() for t in tickers]
        all_tickers = tickers + [benchmark]
        
        # Fetch data (1 year daily)
        data = {}
        for t in all_tickers:
            df = self.fetcher.get_intraday_data(t, days=252) # Will get daily if > 60 days via fallback logic usually
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                # Resample to daily closes
                daily = df['close'].resample('D').last().dropna()
                data[t] = daily
        
        if not data:
            return {'error': 'No data found'}
            
        # Create price dataframe
        prices = pd.DataFrame(data).dropna()
        returns = prices.pct_change().dropna()
        
        if returns.empty:
            return {'error': 'Insufficient history overlap'}
            
        # 1. Correlation Matrix
        corr_matrix = returns.corr()
        
        # Average correlation of portfolio assets (excluding benchmark)
        port_tickers = [t for t in tickers if t in returns.columns]
        if len(port_tickers) > 1:
            # Get lower triangle of correlation matrix for assets
            asset_corr = returns[port_tickers].corr()
            avg_corr = (asset_corr.sum().sum() - len(port_tickers)) / (len(port_tickers) * (len(port_tickers) - 1))
        else:
            avg_corr = 1.0
            
        # 2. Beta to Benchmark
        betas = {}
        for t in port_tickers:
            cov = returns[t].cov(returns[benchmark])
            var = returns[benchmark].var()
            betas[t] = cov / var if var != 0 else 0
            
        avg_beta = np.mean(list(betas.values()))
        
        # 3. VaR (Value at Risk) - Historical 95%
        # If we hold equal weight
        if len(port_tickers) > 0:
            port_returns = returns[port_tickers].mean(axis=1) # Equal weight
            var_95 = np.percentile(port_returns, 5) # 5th percentile (negative number)
        else:
            var_95 = 0
            
        # Verdict
        warnings = []
        if avg_corr > 0.7:
            warnings.append("High Correlation (Concentration Risk)")
        if avg_beta > 1.5:
            warnings.append("High Beta (Aggressive/Volatile)")
        if var_95 < -0.03: # >3% daily loss risk
            warnings.append("High VaR (>3% daily risk)")
            
        return {
            'avg_correlation': round(avg_corr, 2),
            'avg_beta': round(avg_beta, 2),
            'var_95_daily': round(var_95 * 100, 2),
            'betas': {k: round(v, 2) for k, v in betas.items()},
            'warnings': warnings,
            'correlation_matrix': corr_matrix.to_dict() # For raw data if needed
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tickers', help='Comma separated tickers')
    args = parser.parse_args()
    
    tickers = args.tickers.split(',') if args.tickers else ['NVDA', 'AMD', 'TSM', 'MSFT']
    
    print(f"Analyzing Portfolio: {', '.join(tickers)}...")
    analyzer = PortfolioRiskAnalyzer()
    res = analyzer.analyze_portfolio(tickers)
    
    if 'error' in res:
        print(f"Error: {res['error']}")
    else:
        print(f"\n📊 PORTFOLIO HEALTH REPORT")
        print(f"---------------------------")
        print(f"Avg Correlation: {res['avg_correlation']} (Scale: 0-1)")
        print(f"Portfolio Beta:  {res['avg_beta']} (vs SPY)")
        print(f"VaR (95% Daily): {res['var_95_daily']}%")
        
        print("\n⚠️  Warnings:")
        if res['warnings']:
            for w in res['warnings']:
                print(f"  • {w}")
        else:
            print("  • Portfolio looks balanced ✅")
            
        print("\nIndividual Betas:")
        for t, b in res['betas'].items():
            print(f"  {t}: {b}")

