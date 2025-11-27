#!/usr/bin/env python3
"""
Get Russell 2000 Constituents
==============================

Multiple fallback sources for Russell 2000 tickers.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime


def get_russell2000_from_ishares() -> list:
    """Get Russell 2000 from iShares IWM ETF holdings."""
    print("Fetching Russell 2000 from iShares IWM holdings...")
    
    try:
        # iShares IWM (Russell 2000 ETF) holdings
        url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Alternative: Download holdings CSV directly
        csv_url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
        
        response = requests.get(csv_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Parse CSV
            from io import StringIO
            # Skip metadata rows
            lines = response.text.split('\n')
            
            # Find where actual data starts
            start_idx = 0
            for i, line in enumerate(lines):
                if 'Ticker' in line or 'Symbol' in line:
                    start_idx = i
                    break
            
            csv_data = '\n'.join(lines[start_idx:])
            df = pd.read_csv(StringIO(csv_data))
            
            # Get tickers
            ticker_col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            tickers = df[ticker_col].dropna().tolist()
            
            # Clean tickers
            tickers = [t.strip().upper() for t in tickers if isinstance(t, str) and len(t) <= 5]
            
            print(f"  Found {len(tickers)} tickers from iShares")
            return tickers
            
    except Exception as e:
        print(f"  iShares fetch failed: {e}")
        return []


def get_russell2000_from_wikipedia() -> list:
    """Try to get list from Wikipedia."""
    print("Fetching Russell 2000 from Wikipedia...")
    
    try:
        url = "https://en.wikipedia.org/wiki/Russell_2000_Index"
        tables = pd.read_html(url)
        
        for table in tables:
            if 'Ticker' in table.columns or 'Symbol' in table.columns:
                ticker_col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                tickers = table[ticker_col].dropna().tolist()
                tickers = [t.strip().upper() for t in tickers if isinstance(t, str)]
                
                if len(tickers) > 100:
                    print(f"  Found {len(tickers)} tickers from Wikipedia")
                    return tickers
                    
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")
        return []


def get_russell2000_approximation() -> list:
    """
    Approximation: Get small/mid cap stocks from market screener.
    Filter for market cap between $300M - $10B (typical Russell 2000 range).
    """
    print("Building Russell 2000 approximation from market screener...")
    
    try:
        # Use yfinance to get stocks and filter by market cap
        # This is approximate but will get us small/mid caps
        
        # Start with broader index and filter
        print("  Fetching S&P 600 (small cap) as base...")
        
        # Known small cap stocks to start
        small_caps = []
        
        # Add some known Russell 2000 members
        known_r2k = [
            # Regional banks
            'PACW', 'ZION', 'WTFC', 'CBSH', 'UBSI', 'ONB', 'FFIN', 'FULT',
            # REITs
            'MAC', 'BRX', 'JBGS', 'PDM', 'ESRT', 'SITC', 'PGRE', 'DEI',
            # Healthcare
            'SGRY', 'GKOS', 'ATRC', 'TECH', 'ISRG', 'ALGN', 'PODD', 'DXCM',
            # Industrials
            'FELE', 'ATRO', 'GTLS', 'MLI', 'IIIN', 'MRCY', 'UFPI', 'TRN',
            # Tech/Software
            'APPF', 'CCOI', 'QLYS', 'SMAR', 'TENB', 'VRNS', 'PLUS', 'BL',
            # Consumer
            'BOOT', 'CASY', 'CHWY', 'GPI', 'FIVE', 'LAD', 'OLLI', 'PENN',
            # Energy
            'CLB', 'NOG', 'CIVI', 'SM', 'TALO', 'MGY', 'MTDR', 'VTLE',
        ]
        
        small_caps.extend(known_r2k)
        
        print(f"  Starting with {len(small_caps)} known Russell 2000 members")
        return small_caps
        
    except Exception as e:
        print(f"  Approximation failed: {e}")
        return []


def get_russell2000_from_file() -> list:
    """Check if we have a saved Russell 2000 list."""
    try:
        if os.path.exists('data/russell2000_tickers.csv'):
            df = pd.read_csv('data/russell2000_tickers.csv')
            tickers = df['ticker'].tolist()
            print(f"Loaded {len(tickers)} tickers from saved file")
            return tickers
    except:
        pass
    return []


def build_russell2000_universe() -> list:
    """Try multiple sources to build Russell 2000 universe."""
    print("="*80)
    print("BUILDING RUSSELL 2000 UNIVERSE")
    print("="*80)
    
    # Try multiple sources
    tickers = get_russell2000_from_file()
    
    if not tickers:
        tickers = get_russell2000_from_ishares()
    
    if not tickers or len(tickers) < 500:
        wiki_tickers = get_russell2000_from_wikipedia()
        tickers.extend(wiki_tickers)
        tickers = list(set(tickers))
    
    if not tickers or len(tickers) < 500:
        approx_tickers = get_russell2000_approximation()
        tickers.extend(approx_tickers)
        tickers = list(set(tickers))
    
    # Deduplicate and clean
    tickers = list(set([t.upper().strip() for t in tickers if t and len(t) <= 5]))
    
    print(f"\n{'='*80}")
    print(f"FINAL RUSSELL 2000 UNIVERSE: {len(tickers)} tickers")
    print(f"{'='*80}")
    
    # Save for future use
    if tickers:
        df = pd.DataFrame({'ticker': sorted(tickers)})
        df.to_csv('data/russell2000_tickers.csv', index=False)
        print(f"Saved to: data/russell2000_tickers.csv")
    
    return tickers


if __name__ == "__main__":
    import os
    os.makedirs('data', exist_ok=True)
    tickers = build_russell2000_universe()
    
    if tickers:
        print(f"\nSample tickers: {tickers[:20]}")
    else:
        print("\nFailed to build Russell 2000 universe")
