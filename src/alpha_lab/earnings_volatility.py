#!/usr/bin/env python3
"""
Earnings Volatility Analysis Module
===================================

Analyzes the "Implied Move" vs "Historical Move" to determine if options are 
cheap or expensive ahead of earnings.

Logic:
1. Implied Move = Cost of ATM Straddle (nearest expiry after earnings) / Stock Price
2. Historical Move = Average absolute % move on earnings day (last 4 quarters)
3. Edge: If Implied < Historical, Volatility is underpriced (Buy options).
         If Implied > Historical, Volatility is overpriced (Sell options/Wait).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, Optional

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.data_fetcher import DataFetcher

class EarningsVolatilityAnalyzer:
    """Analyzes earnings volatility pricing edge."""
    
    def __init__(self, fetcher: DataFetcher = None):
        self.fetcher = fetcher if fetcher else DataFetcher(None)
        
    def _get_next_earnings_date(self, ticker: str) -> Optional[datetime]:
        """Get next confirmed earnings date."""
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            if calendar is None or calendar.empty:
                return None
            
            # yfinance structure varies
            if 'Earnings Date' in calendar:
                dates = calendar['Earnings Date']
                # Get first future date
                future_dates = [d for d in dates if d > datetime.now().date()]
                if future_dates:
                    return pd.to_datetime(future_dates[0])
            
            # Alternative structure: keys are indices
            # often 0 is the next earnings date
            return None # Fallback for now
        except:
            return None

    def _calculate_historical_moves(self, ticker: str, lookback_quarters: int = 4) -> float:
        """
        Calculate average absolute % move on past earnings days.
        """
        try:
            stock = yf.Ticker(ticker)
            # Get earnings dates history (not reliable in yfinance free tier usually)
            # Fallback: Look for large volume/price spikes in 1y history? Hard to pinpoint exact earnings.
            
            # Better: yfinance 'earnings_dates' dataframe often contains history
            earnings_hist = stock.earnings_dates
            if earnings_hist is None or earnings_hist.empty:
                return 0.0
            
            # Filter for past dates
            past_earnings = earnings_hist[earnings_hist.index < pd.Timestamp.now()].sort_index(ascending=False)
            past_earnings = past_earnings.head(lookback_quarters)
            
            if past_earnings.empty:
                return 0.0
                
            moves = []
            
            # Fetch price data around those dates
            # We need daily data for the last year
            hist = stock.history(period="1y")
            
            for date in past_earnings.index:
                # Find the trading day
                try:
                    # Earnings often AMC (After Market Close) or BMO (Before Market Open)
                    # Simple approximation: Abs return of the day OF or day AFTER earnings
                    # We check the day after the date (reaction)
                    
                    # Locate date in history index
                    idx_loc = hist.index.get_indexer([date], method='nearest')[0]
                    if idx_loc + 1 >= len(hist):
                        continue
                        
                    # Reaction is usually the gap from close to next open/close
                    # Let's take close-to-close of the reaction day
                    day_before = hist.iloc[idx_loc]
                    reaction_day = hist.iloc[idx_loc + 1]
                    
                    pct_move = abs((reaction_day['Close'] - day_before['Close']) / day_before['Close']) * 100
                    moves.append(pct_move)
                    
                except Exception:
                    continue
                    
            if not moves:
                return 0.0
                
            return np.mean(moves)
            
        except Exception as e:
            # print(f"Historical move error: {e}")
            return 0.0

    def _calculate_implied_move(self, ticker: str, current_price: float) -> Dict:
        """
        Calculate implied move from option chain.
        Uses ATM Straddle price of nearest monthly expiry.
        """
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                return {}
                
            # Find an expiry ~30 days out (standard) or next earnings?
            # Let's pick nearest expiry at least 14 days out to avoid gamma noise
            target_date = None
            today = datetime.now().date()
            
            for date_str in expirations:
                exp_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if (exp_date - today).days > 14:
                    target_date = date_str
                    break
            
            if not target_date:
                target_date = expirations[0] # Fallback
                
            chain = stock.option_chain(target_date)
            calls = chain.calls
            puts = chain.puts
            
            # Find ATM strike
            strikes = calls['strike']
            atm_strike = strikes.iloc[(strikes - current_price).abs().argsort()[:1]].values[0]
            
            # Get ATM Call and Put price (Midpoint if possible, else Last)
            call_row = calls[calls['strike'] == atm_strike].iloc[0]
            put_row = puts[puts['strike'] == atm_strike].iloc[0]
            
            call_price = (call_row['bid'] + call_row['ask']) / 2 if call_row['bid'] > 0 else call_row['lastPrice']
            put_price = (put_row['bid'] + put_row['ask']) / 2 if put_row['bid'] > 0 else put_row['lastPrice']
            
            straddle_cost = call_price + put_price
            implied_move_pct = (straddle_cost / current_price) * 100 * 0.85 # 0.85 is a breakeven adjustment factor often used
            
            return {
                'expiry': target_date,
                'atm_strike': atm_strike,
                'straddle_cost': straddle_cost,
                'implied_move_pct': implied_move_pct
            }
            
        except Exception as e:
            # print(f"Implied move error: {e}")
            return {}

    def analyze_earnings(self, ticker: str, current_price: float) -> Dict:
        """
        Full analysis.
        """
        # 1. Historical Moves
        avg_move = self._calculate_historical_moves(ticker)
        
        # 2. Implied Move
        implied_data = self._calculate_implied_move(ticker, current_price)
        implied_move = implied_data.get('implied_move_pct', 0.0)
        
        # 3. Verdict
        verdict = "NEUTRAL"
        if avg_move > 0 and implied_move > 0:
            if implied_move < avg_move * 0.8:
                verdict = "CHEAP_VOLATILITY" # Market underestimates move
            elif implied_move > avg_move * 1.2:
                verdict = "EXPENSIVE_VOLATILITY" # Market overestimates move
                
        return {
            'historical_avg_move': round(avg_move, 2),
            'implied_move': round(implied_move, 2),
            'expiry_used': implied_data.get('expiry', 'N/A'),
            'verdict': verdict,
            'edge_ratio': round(avg_move / implied_move, 2) if implied_move > 0 else 0
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('ticker', nargs='?', default='NVDA')
    args = parser.parse_args()
    
    print(f"Analyzing Earnings Volatility for {args.ticker}...")
    
    # Quick price fetch
    import yfinance as yf
    curr_price = yf.Ticker(args.ticker).history(period='1d')['Close'].iloc[-1]
    print(f"Price: ${curr_price:.2f}")
    
    analyzer = EarningsVolatilityAnalyzer()
    res = analyzer.analyze_earnings(args.ticker, curr_price)
    
    print("\n📊 RESULTS:")
    print(f"  • Avg Historical Move: {res['historical_avg_move']}%")
    print(f"  • Current Implied Move: {res['implied_move']}% (Expiry: {res['expiry_used']})")
    print(f"  • Verdict: {res['verdict']}")
    print(f"  • Edge: {res['edge_ratio']}x (Higher is better for buying)")

