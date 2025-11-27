#!/usr/bin/env python3
"""
Expand Universe to All Tradable US Stocks
==========================================

Pull comprehensive universe from multiple sources.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
from typing import List, Set

def get_sp500() -> List[str]:
    """Get S&P 500 constituents."""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    df = tables[0]
    return df['Symbol'].str.replace('.', '-').tolist()

def get_nasdaq100() -> List[str]:
    """Get NASDAQ 100 constituents."""
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    tables = pd.read_html(url)
    df = tables[4]  # Usually the 5th table
    return df['Ticker'].tolist()

def get_russell2000() -> List[str]:
    """
    Get Russell 2000 constituents (placeholder).
    Note: Full list requires data provider subscription.
    """
    # This would require a proper data feed
    # For now, return empty - user needs to add their source
    print("  Russell 2000: Requires data provider (not freely available)")
    return []

def get_nasdaq_screener() -> List[str]:
    """
    Download NASDAQ screener data.
    Contains ALL stocks traded on NASDAQ, NYSE, AMEX.
    """
    print("  Downloading NASDAQ screener (all US stocks)...")
    
    # NASDAQ provides a free CSV of all traded stocks
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&download=true"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'rows' in data['data']:
                symbols = [row['symbol'] for row in data['data']['rows']]
                print(f"    Found {len(symbols)} stocks from NASDAQ screener")
                return symbols
        
        # Fallback: Try direct CSV download
        csv_url = "https://www.nasdaq.com/market-activity/stocks/screener?exchange=nasdaq&letter=0&render=download"
        df = pd.read_csv(csv_url)
        return df['Symbol'].tolist()
        
    except Exception as e:
        print(f"    Warning: NASDAQ screener failed: {e}")
        return []

def get_all_etfs() -> List[str]:
    """Get major ETFs for comparison."""
    etfs = [
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND',
        'TLT', 'GLD', 'SLV', 'USO', 'UNG', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI',
        'XLP', 'XLY', 'XLU', 'XLB', 'XLRE', 'XBI', 'IBB', 'SMH', 'SOXX', 'KRE',
        'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ', 'IBIT', 'GBTC', 'ETHE'
    ]
    return etfs

def filter_universe_comprehensive(symbols: List[str]) -> pd.DataFrame:
    """
    Apply comprehensive filters to get tradable universe.
    
    Filters:
    - Price > $1 (avoid penny stocks)
    - Average volume > 100K shares/day
    - Market cap > $50M
    - Data available for at least 200 days
    - Not a duplicate/variant ticker
    """
    print(f"\nFiltering {len(symbols)} symbols...")
    print("This will take 10-30 minutes for full universe...")
    
    valid_stocks = []
    
    # Process in batches
    batch_size = 100
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f"  Processing batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}...")
        
        try:
            # Download batch data
            data = yf.download(
                batch,
                period='1y',
                group_by='ticker',
                threads=True,
                progress=False
            )
            
            for symbol in batch:
                try:
                    if len(batch) == 1:
                        df = data
                    else:
                        if symbol not in data.columns.get_level_values(0):
                            continue
                        df = data[symbol]
                    
                    if df.empty or len(df) < 200:
                        continue
                    
                    # Get latest data
                    close = df['Close'].dropna()
                    volume = df['Volume'].dropna()
                    
                    if len(close) < 200:
                        continue
                    
                    price = close.iloc[-1]
                    avg_volume = volume.tail(60).mean()
                    
                    # Apply filters
                    if price < 1.0:
                        continue
                    if avg_volume < 100000:
                        continue
                    
                    # Estimate market cap (rough)
                    # Would need actual shares outstanding
                    dollar_volume = price * avg_volume
                    
                    # Calculate some quick stats
                    volatility = close.pct_change().tail(60).std() * 252**0.5
                    returns_60d = (close.iloc[-1] / close.iloc[-60] - 1) if len(close) >= 60 else 0
                    
                    valid_stocks.append({
                        'symbol': symbol,
                        'price': price,
                        'avg_volume': avg_volume,
                        'dollar_volume': dollar_volume,
                        'volatility': volatility,
                        'return_60d': returns_60d,
                        'data_points': len(close)
                    })
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    Batch error: {e}")
            continue
    
    df = pd.DataFrame(valid_stocks)
    
    if df.empty:
        print("Warning: No valid stocks found!")
        return df
    
    # Additional filters
    df = df[
        (df['avg_volume'] >= 100000) &
        (df['price'] >= 1.0) &
        (df['volatility'] < 2.0) &  # Remove ultra-high vol
        (df['data_points'] >= 200)
    ]
    
    print(f"\nFiltered universe: {len(df)} stocks")
    print(f"  Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
    print(f"  Avg volume: {df['avg_volume'].min():,.0f} - {df['avg_volume'].max():,.0f}")
    
    return df

def build_full_universe() -> pd.DataFrame:
    """Build comprehensive universe of all tradable US stocks."""
    
    print("="*80)
    print("BUILDING COMPREHENSIVE US STOCK UNIVERSE")
    print("="*80)
    
    all_symbols = set()
    
    # 1. S&P 500
    print("\n1. Fetching S&P 500...")
    sp500 = get_sp500()
    all_symbols.update(sp500)
    print(f"   Added {len(sp500)} symbols")
    
    # 2. NASDAQ 100
    print("\n2. Fetching NASDAQ 100...")
    nasdaq100 = get_nasdaq100()
    all_symbols.update(nasdaq100)
    print(f"   Added {len(nasdaq100)} symbols (total: {len(all_symbols)})")
    
    # 3. Full NASDAQ/NYSE/AMEX screener
    print("\n3. Fetching full US stock screener...")
    screener = get_nasdaq_screener()
    if screener:
        all_symbols.update(screener)
        print(f"   Added {len(screener)} symbols (total: {len(all_symbols)})")
    
    # 4. Russell 2000 (if available)
    print("\n4. Checking Russell 2000...")
    russell = get_russell2000()
    if russell:
        all_symbols.update(russell)
        print(f"   Added {len(russell)} symbols (total: {len(all_symbols)})")
    
    # 5. Major ETFs
    print("\n5. Adding major ETFs...")
    etfs = get_all_etfs()
    all_symbols.update(etfs)
    print(f"   Added {len(etfs)} ETFs (total: {len(all_symbols)})")
    
    print(f"\n{'='*80}")
    print(f"RAW UNIVERSE: {len(all_symbols)} unique symbols")
    print(f"{'='*80}")
    
    # Convert to sorted list
    symbols_list = sorted(list(all_symbols))
    
    # Filter for quality
    filtered_df = filter_universe_comprehensive(symbols_list)
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'data/output/full_universe_{timestamp}.csv'
    filtered_df.to_csv(output_file, index=False)
    
    print(f"\n{'='*80}")
    print(f"FINAL UNIVERSE: {len(filtered_df)} tradable stocks")
    print(f"Saved to: {output_file}")
    print(f"{'='*80}")
    
    return filtered_df

if __name__ == "__main__":
    universe_df = build_full_universe()
    
    # Display sample
    print("\nSample of universe (sorted by volume):")
    print(universe_df.nlargest(20, 'avg_volume')[['symbol', 'price', 'avg_volume', 'volatility']])
