#!/usr/bin/env python3
"""
Get Russell 1000 Constituents
==============================

Russell 1000 = Large/mid caps, better liquidity than R2K.
"""

import pandas as pd
import requests
from datetime import datetime


def get_russell1000_from_ishares() -> list:
    """Get Russell 1000 from iShares IWB ETF holdings."""
    print("Fetching Russell 1000 from iShares IWB holdings...")
    
    try:
        # iShares IWB (Russell 1000 ETF) holdings
        csv_url = "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/1467271812596.ajax?fileType=csv&fileName=IWB_holdings&dataType=fund"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(csv_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            from io import StringIO
            lines = response.text.split('\n')
            
            # Find where data starts
            start_idx = 0
            for i, line in enumerate(lines):
                if 'Ticker' in line or 'Symbol' in line:
                    start_idx = i
                    break
            
            csv_data = '\n'.join(lines[start_idx:])
            df = pd.read_csv(StringIO(csv_data))
            
            ticker_col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            tickers = df[ticker_col].dropna().tolist()
            
            # Clean
            tickers = [t.strip().upper() for t in tickers if isinstance(t, str) and len(t) <= 5]
            tickers = [t for t in tickers if t != '-']  # Remove invalid
            
            print(f"  Found {len(tickers)} tickers from iShares IWB")
            return tickers
            
    except Exception as e:
        print(f"  Failed: {e}")
        return []


def main():
    import os
    os.makedirs('data', exist_ok=True)
    
    print("="*80)
    print("BUILDING RUSSELL 1000 UNIVERSE")
    print("="*80)
    
    tickers = get_russell1000_from_ishares()
    
    if tickers:
        # Deduplicate
        tickers = list(set(tickers))
        tickers = sorted(tickers)
        
        print(f"\n{'='*80}")
        print(f"FINAL RUSSELL 1000: {len(tickers)} tickers")
        print(f"{'='*80}")
        
        # Save
        df = pd.DataFrame({'ticker': tickers})
        df.to_csv('data/russell1000_tickers.csv', index=False)
        print(f"Saved to: data/russell1000_tickers.csv")
        
        print(f"\nSample: {tickers[:20]}")
        
        return tickers
    else:
        print("\nFailed to build Russell 1000 universe")
        return []


if __name__ == "__main__":
    main()
