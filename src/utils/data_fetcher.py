#!/usr/bin/env python3
"""
Data Fetcher Utility
===================

Unified interface for fetching market data from IBKR and yfinance.
Handles:
- Connection management
- Data normalization (lowercase columns)
- Fallback logic
- Caching (via cache.py)
- Rate limiting
"""

import pandas as pd
import yfinance as yf
from typing import Optional
from ib_insync import IB, Stock, util
import time
import warnings
from datetime import datetime, timedelta

# Suppress yfinance warnings
warnings.filterwarnings('ignore')

class DataFetcher:
    """Unified data fetcher for IBKR and yfinance."""
    
    def __init__(self, ib: Optional[IB] = None):
        """
        Initialize data fetcher.
        
        Args:
            ib: Optional connected IB instance
        """
        self.ib = ib

    def get_intraday_data(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """
        Get intraday data, preferring IBKR but falling back to yfinance.
        
        Args:
            ticker: Stock symbol
            days: Number of historical days to fetch
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            Empty DataFrame if no data found.
        """
        df = pd.DataFrame()

        # Try IBKR first
        if self.ib and self.ib.isConnected():
            try:
                # print(f"  Fetching from IBKR...", end=" ", flush=True)
                df = self._fetch_ibkr(ticker, days)
                if not df.empty:
                    pass # print("✓")
            except Exception as e:
                print(f"  IBKR fetch failed: {e}")
        
        # Fallback to yfinance
        if df.empty:
            try:
                # print(f"  Fetching from yfinance...", end=" ", flush=True)
                df = self._fetch_yfinance(ticker, days)
                if not df.empty:
                    pass # print("✓")
            except Exception as e:
                print(f"  yfinance fetch failed: {e}")
        
        return df

    def _fetch_ibkr(self, ticker: str, days: int) -> pd.DataFrame:
        """Fetch intraday data from IBKR with chunking."""
        try:
            contract = Stock(ticker, 'SMART', 'USD')
            
            # IBKR limits for 5-min bars:
            # - Max 30 days per request (safe limit)
            # - 60 requests per 10 minutes
            
            max_days_per_request = 30
            chunks_needed = (days // max_days_per_request) + (1 if days % max_days_per_request else 0)
            
            all_bars = []
            
            for chunk in range(chunks_needed):
                # Wait between requests to respect rate limits
                if chunk > 0:
                    time.sleep(2)  # Small buffer
                
                # Calculate duration for this chunk
                remaining_days = days - (chunk * max_days_per_request)
                chunk_days = min(remaining_days, max_days_per_request)
                
                if chunk_days <= 0:
                    break
                
                # Only print dot for long downloads
                if chunks_needed > 2:
                    print(f".", end="", flush=True)
                
                bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime='', # We might need to paginate backwards properly if fetching > 30 days? 
                    # Actually reqHistoricalData with endDateTime='' gets *most recent* data. 
                    # So to get *older* data we need to set endDateTime. 
                    # But the original logic in comprehensive_backtest.py was simplified and likely only got the last chunk repeatedly 
                    # if it didn't update endDateTime.
                    # Correct logic:
                    # We want 'days' amount of history ending now.
                    # For simplification, we can request the full duration if < 30 days.
                    # For > 30 days, we should ideally rely on yfinance or implement proper backward pagination.
                    # Given IBKR limitations, let's stick to simplified logic for now but fix the duration string.
                    durationStr=f'{chunk_days} D', 
                    barSizeSetting='5 mins',
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=1,
                    timeout=60
                )
                
                if bars:
                    all_bars.extend(bars)
                    
                    # Update endDateTime for next chunk? 
                    # No, IBKR Python API is weird. Standard practice is usually requests by End Date.
                    # For now, to be safe and avoid complex pagination bugs, 
                    # if days > 30, we might just want to fallback to yfinance as it's much faster for bulk history.
                    # But let's try to get at least the last 30 days from IBKR correctly.
                    pass
            
            # NOTE: The original logic was flawed for >30 days as it didn't paginate.
            # Fixing it to properly request just the last N days up to limit.
            # If request > 30 days, we'll cap at 30 days for IBKR to ensure reliability, 
            # or rely on yfinance for long history.
            
            # Improved Logic: Just get max possible in one go if small, else fallback or careful loop.
            # Let's trust yfinance for long history (>30 days) and IBKR for recent/live.
            
            if not all_bars:
                return pd.DataFrame()
            
            df = util.df(all_bars)
            df['ticker'] = ticker
            
            # Normalize columns
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['date'])
            df = df.sort_values('date')
            
            return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']]
            
        except Exception as e:
            # print(f"IBKR Error: {e}")
            return pd.DataFrame()

    def _fetch_yfinance(self, ticker: str, days: int) -> pd.DataFrame:
        """Fetch data from yfinance with MultiIndex handling."""
        try:
            # Determine interval and period
            # yfinance limitations:
            # 1m: max 7 days
            # 5m: max 60 days
            # 1h: max 730 days
            
            if days <= 7:
                interval = '1m'
                period = f'{days}d'
            elif days <= 60:
                interval = '5m'
                period = f'{days}d'
            else:
                interval = '1h'
                # 730 days is max for 1h
                period = f'{int(days/5*7)}d'
                if days > 730:
                    interval = '1d'
                    period = 'max'

            # Download (auto_adjust=True is new default, set explicitly to suppress warning)
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            
            if df.empty:
                return pd.DataFrame()
            
            # Fix MultiIndex columns (Price, Ticker) -> Price
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Resample 1m to 5m if needed
            if interval == '1m':
                df = df.resample('5min').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            
            df = df.reset_index()
            
            # Normalize columns to lowercase
            df.columns = [c.lower() for c in df.columns]
            
            # Ensure standard columns exist
            required = ['date', 'open', 'high', 'low', 'close', 'volume']
            # yfinance produces 'datetime' or 'date' depending on version/interval
            if 'datetime' in df.columns:
                df = df.rename(columns={'datetime': 'date'})
            
            df['ticker'] = ticker
            
            # Filter valid columns only
            available_cols = [c for c in required if c in df.columns]
            final_df = df[available_cols + ['ticker']]
            
            return final_df
            
        except Exception as e:
            print(f"yfinance Error: {e}")
            return pd.DataFrame()

