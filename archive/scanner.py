#!/usr/bin/env python3
"""
Unified Trading Scanner
=======================

Consolidated scanner combining all scanning functionality:
- Intraday signals (gap/momentum/VWAP)
- After-hours movers
- 1-hour momentum  
- Multiple universe options
- Real-time IBKR data
- Backtesting capability

Replaces 7 separate scanner scripts.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ib_insync import IB, Stock, util
import yfinance as yf
import warnings
import argparse
warnings.filterwarnings('ignore')

from alpha_lab.intraday_signals import IntradaySignalGenerator


# ============================================================================
# UNIVERSE DEFINITIONS
# ============================================================================

UNIVERSES = {
    'liquid': [
        # High volume tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'NFLX',
        # Volatile growth
        'COIN', 'PLTR', 'SNOW', 'CRWD', 'ZS', 'DDOG', 'NET',
        # Meme/retail
        'GME', 'AMC', 'SOFI', 'HOOD', 'RIVN', 'LCID',
        # Energy
        'XOM', 'CVX', 'SLB', 'HAL', 'OXY', 'MPC',
        # Biotech
        'MRNA', 'BNTX', 'NVAX', 'REGN', 'VRTX', 'GILD',
        # Financials
        'JPM', 'BAC', 'GS', 'MS', 'C', 'WFC',
        # Crypto proxies
        'MARA', 'RIOT', 'MSTR', 'HUT', 'BTBT',
        # EV
        'NIO', 'XPEV', 'LI', 'PLUG', 'ENPH',
        # High beta
        'UPST', 'AFRM', 'CVNA', 'DASH', 'UBER', 'LYFT',
        # ETFs
        'SPY', 'QQQ', 'IWM', 'ARKK', 'SOXL', 'TQQQ'
    ],
    
    'russell1000': None,  # Loaded from file
    'russell2000': None,  # Loaded from file
    'custom': None  # User-provided
}


class UnifiedScanner:
    """Unified scanner for all trading signals."""
    
    def __init__(self, ib: Optional[IB] = None):
        """
        Initialize scanner.
        
        Args:
            ib: IBKR connection (optional, will create if None)
        """
        self.ib = ib
        self.owns_ib = False
        
        if self.ib is None:
            self.ib = IB()
            self.owns_ib = True
            
        self.signal_gen = IntradaySignalGenerator(self.ib)
        
    def connect_ibkr(self, host: str = '127.0.0.1', port: int = 4001, 
                     client_id: int = 1) -> bool:
        """Connect to IBKR Gateway."""
        if self.ib.isConnected():
            return True
            
        try:
            self.ib.connect(host, port, clientId=client_id, timeout=15)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IBKR if we own the connection."""
        if self.owns_ib and self.ib.isConnected():
            self.ib.disconnect()
    
    def load_universe(self, universe_name: str) -> List[str]:
        """
        Load universe of stocks to scan.
        
        Args:
            universe_name: 'liquid', 'russell1000', 'russell2000', or 'custom'
            
        Returns:
            List of ticker symbols
        """
        if universe_name == 'liquid':
            return UNIVERSES['liquid']
            
        elif universe_name == 'russell1000':
            try:
                df = pd.read_csv('data/russell1000_tickers.csv')
                return df['ticker'].tolist()
            except:
                print("Warning: Russell 1000 file not found, run get_russell1000.py first")
                return []
                
        elif universe_name == 'russell2000':
            try:
                df = pd.read_csv('data/russell2000_tickers.csv')
                return df['ticker'].tolist()
            except:
                print("Warning: Russell 2000 file not found, run get_russell2000.py first")
                return []
                
        elif universe_name == 'custom':
            try:
                df = pd.read_csv('data/custom_universe.csv')
                return df['ticker'].tolist()
            except:
                print("Warning: custom_universe.csv not found")
                return []
        else:
            print(f"Unknown universe: {universe_name}")
            return []
    
    def scan_intraday(self, universe: List[str], 
                      signal_types: List[str] = None) -> pd.DataFrame:
        """
        Scan for intraday signals.
        
        Args:
            universe: List of symbols to scan
            signal_types: List of signal types to detect:
                         ['gap', 'momentum', 'vwap', 'all']
                         
        Returns:
            DataFrame with signals ranked by confidence
        """
        if signal_types is None or 'all' in signal_types:
            signal_types = ['gap', 'momentum', 'vwap']
        
        print(f"\nScanning {len(universe)} symbols for intraday signals...")
        print(f"Signal types: {', '.join(signal_types)}")
        print("="*80)
        
        return self.signal_gen.scan_universe(universe)
    
    def scan_after_hours(self, universe: List[str], 
                        min_gap: float = 0.5) -> pd.DataFrame:
        """
        Scan for after-hours movers.
        
        Args:
            universe: List of symbols
            min_gap: Minimum gap percentage to report
            
        Returns:
            DataFrame with after-hours movers
        """
        print(f"\nScanning {len(universe)} symbols for after-hours movers...")
        print(f"Minimum gap: {min_gap}%")
        print("="*80)
        
        movers = []
        
        for i, symbol in enumerate(universe):
            if (i + 1) % 20 == 0:
                print(f"  Scanned {i+1}/{len(universe)}...")
            
            try:
                # Get current price from IBKR
                contract = Stock(symbol, 'SMART', 'USD')
                self.ib.reqMktData(contract, '', False, False)
                self.ib.sleep(0.5)
                ticker = self.ib.ticker(contract)
                self.ib.cancelMktData(contract)
                
                current_price = None
                if ticker.last and ticker.last > 0:
                    current_price = ticker.last
                elif ticker.bid and ticker.ask:
                    current_price = (ticker.bid + ticker.ask) / 2
                elif ticker.close and ticker.close > 0:
                    current_price = ticker.close
                
                if not current_price:
                    continue
                
                # Get previous close
                yf_ticker = yf.Ticker(symbol)
                hist = yf_ticker.history(period='2d', interval='1d')
                
                if len(hist) < 1:
                    continue
                
                prev_close = hist['Close'].iloc[-1]
                gap_pct = (current_price - prev_close) / prev_close * 100
                
                if abs(gap_pct) >= min_gap:
                    movers.append({
                        'symbol': symbol,
                        'gap_pct': gap_pct,
                        'current_price': current_price,
                        'prev_close': prev_close,
                        'direction': 'UP' if gap_pct > 0 else 'DOWN'
                    })
                    
            except Exception as e:
                continue
        
        if not movers:
            return pd.DataFrame()
        
        df = pd.DataFrame(movers)
        df = df.sort_values('gap_pct', key=abs, ascending=False)
        
        print(f"\nFound {len(df)} after-hours movers")
        return df
    
    def scan_1hour_momentum(self, universe: List[str],
                           min_change: float = 1.0) -> pd.DataFrame:
        """
        Scan for 1-hour momentum moves.
        
        Args:
            universe: List of symbols
            min_change: Minimum 1-hour change percentage
            
        Returns:
            DataFrame with 1-hour movers
        """
        print(f"\nScanning {len(universe)} symbols for 1-hour momentum...")
        print(f"Minimum change: {min_change}%")
        print("="*80)
        
        movers = []
        
        for i, symbol in enumerate(universe):
            if (i + 1) % 20 == 0:
                print(f"  Scanned {i+1}/{len(universe)}...")
            
            try:
                # Get current price from IBKR
                contract = Stock(symbol, 'SMART', 'USD')
                self.ib.reqMktData(contract, '', False, False)
                self.ib.sleep(0.5)
                ticker = self.ib.ticker(contract)
                self.ib.cancelMktData(contract)
                
                current_price = None
                if ticker.last and ticker.last > 0:
                    current_price = ticker.last
                elif ticker.bid and ticker.ask:
                    current_price = (ticker.bid + ticker.ask) / 2
                
                if not current_price:
                    continue
                
                # Get 1-hour ago price
                yf_ticker = yf.Ticker(symbol)
                hist = yf_ticker.history(period='2d', interval='1m')
                
                if len(hist) < 60:
                    continue
                
                price_1h_ago = hist['Close'].iloc[-60]
                change_pct = (current_price - price_1h_ago) / price_1h_ago * 100
                
                if abs(change_pct) >= min_change:
                    movers.append({
                        'symbol': symbol,
                        'change_pct': change_pct,
                        'current_price': current_price,
                        'price_1h_ago': price_1h_ago,
                        'direction': 'UP' if change_pct > 0 else 'DOWN'
                    })
                    
            except Exception as e:
                continue
        
        if not movers:
            return pd.DataFrame()
        
        df = pd.DataFrame(movers)
        df = df.sort_values('change_pct', key=abs, ascending=False)
        
        print(f"\nFound {len(df)} 1-hour movers")
        return df


def display_results(results: pd.DataFrame, scan_type: str, top_n: int = 10):
    """Display scan results in formatted table."""
    if results.empty:
        print(f"\nNo {scan_type} signals found")
        return
    
    print("\n" + "="*80)
    print(f"{scan_type.upper()} RESULTS - TOP {min(top_n, len(results))}")
    print("="*80)
    
    if scan_type == 'intraday':
        print(f"\n{'Rank':<5} {'Symbol':<8} {'Signal':<25} {'Confidence':<12} {'Price':<10}")
        print("-"*80)
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            print(f"{i:<5} {row['symbol']:<8} {row['signal']:<25} "
                  f"{row['confidence']:<11.1f} ${row['price']:<9.2f}")
            
    elif scan_type == 'after_hours':
        print(f"\n{'Rank':<5} {'Symbol':<8} {'Gap %':<10} {'Direction':<10} "
              f"{'Prev Close':<12} {'Current':<10}")
        print("-"*80)
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            print(f"{i:<5} {row['symbol']:<8} {row['gap_pct']:>+7.2f}% "
                  f"{row['direction']:<10} ${row['prev_close']:<11.2f} "
                  f"${row['current_price']:<9.2f}")
            
    elif scan_type == '1hour':
        print(f"\n{'Rank':<5} {'Symbol':<8} {'Change %':<10} {'Direction':<10} "
              f"{'1h Ago':<12} {'Current':<10}")
        print("-"*80)
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            print(f"{i:<5} {row['symbol']:<8} {row['change_pct']:>+7.2f}% "
                  f"{row['direction']:<10} ${row['price_1h_ago']:<11.2f} "
                  f"${row['current_price']:<9.2f}")


def save_results(results: pd.DataFrame, scan_type: str, output_dir: str = 'data/output'):
    """Save scan results to CSV."""
    if results.empty:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{output_dir}/{scan_type}_signals_{timestamp}.csv'
    results.to_csv(filename, index=False)
    print(f"\nResults saved to: {filename}")


def main():
    """Main scanner interface."""
    parser = argparse.ArgumentParser(description='Unified Trading Scanner')
    parser.add_argument('--mode', choices=['intraday', 'after_hours', '1hour', 'all'],
                       default='intraday', help='Scan mode')
    parser.add_argument('--universe', choices=['liquid', 'russell1000', 'russell2000', 'custom'],
                       default='liquid', help='Universe to scan')
    parser.add_argument('--host', default='127.0.0.1', help='IBKR Gateway host')
    parser.add_argument('--port', type=int, default=4001, help='IBKR Gateway port')
    parser.add_argument('--top', type=int, default=10, help='Number of top results to display')
    parser.add_argument('--save', action='store_true', help='Save results to CSV')
    args = parser.parse_args()
    
    print("="*80)
    print("UNIFIED TRADING SCANNER")
    print("="*80)
    print(f"Mode: {args.mode}")
    print(f"Universe: {args.universe}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize scanner
    scanner = UnifiedScanner()
    
    # Connect to IBKR
    print(f"\nConnecting to IBKR Gateway ({args.host}:{args.port})...")
    if not scanner.connect_ibkr(args.host, args.port):
        print("Failed to connect. Make sure IBKR Gateway is running.")
        return
    
    print(f"Connected to IBKR (Account: {scanner.ib.managedAccounts()[0]})")
    
    # Load universe
    print(f"\nLoading {args.universe} universe...")
    universe = scanner.load_universe(args.universe)
    
    if not universe:
        print("Failed to load universe")
        scanner.disconnect()
        return
    
    print(f"Loaded {len(universe)} symbols")
    
    try:
        # Run scans based on mode
        if args.mode == 'intraday' or args.mode == 'all':
            results = scanner.scan_intraday(universe)
            display_results(results, 'intraday', args.top)
            if args.save:
                save_results(results, 'intraday')
        
        if args.mode == 'after_hours' or args.mode == 'all':
            results = scanner.scan_after_hours(universe)
            display_results(results, 'after_hours', args.top)
            if args.save:
                save_results(results, 'after_hours')
        
        if args.mode == '1hour' or args.mode == 'all':
            results = scanner.scan_1hour_momentum(universe)
            display_results(results, '1hour', args.top)
            if args.save:
                save_results(results, '1hour')
    
    finally:
        scanner.disconnect()
    
    print("\n" + "="*80)
    print("Scan complete")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()

