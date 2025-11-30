#!/usr/bin/env python3
"""
Earnings Calendar
=================

Check upcoming earnings dates to avoid buying before announcements.
LEAPS before earnings = gambling, not investing.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def get_next_earnings(ticker: str) -> Optional[Dict]:
    """
    Get next earnings date for a ticker.
    
    Returns:
    {
        'ticker': str,
        'earnings_date': datetime,
        'days_until': int,
        'is_confirmed': bool,
    }
    """
    import yfinance as yf
    from datetime import date
    
    try:
        stock = yf.Ticker(ticker)
        
        # Try calendar first (most reliable)
        calendar = stock.calendar
        
        if calendar is not None:
            # Calendar can be dict or DataFrame
            if isinstance(calendar, dict):
                earnings_dates = calendar.get('Earnings Date', [])
                if earnings_dates:
                    # It's a list of dates
                    if isinstance(earnings_dates, list):
                        earnings_date = earnings_dates[0]
                    else:
                        earnings_date = earnings_dates
                    
                    # Convert to datetime if needed
                    if isinstance(earnings_date, date):
                        earnings_date = datetime.combine(earnings_date, datetime.min.time())
                    
                    days_until = (earnings_date - datetime.now()).days
                    
                    return {
                        'ticker': ticker,
                        'earnings_date': earnings_date,
                        'days_until': days_until,
                        'is_confirmed': True,
                    }
        
        # Fallback to earnings_dates
        earnings = stock.earnings_dates
        if earnings is not None and not earnings.empty:
            # Get next future date
            now = datetime.now()
            for idx in earnings.index:
                # Handle timezone-aware datetimes
                if hasattr(idx, 'tzinfo') and idx.tzinfo:
                    idx_naive = idx.replace(tzinfo=None)
                else:
                    idx_naive = idx
                
                if idx_naive > now:
                    days_until = (idx_naive - now).days
                    return {
                        'ticker': ticker,
                        'earnings_date': idx_naive,
                        'days_until': days_until,
                        'is_confirmed': False,
                    }
            
    except Exception as e:
        pass
        
    return None


def check_earnings_risk(ticker: str, warning_days: int = 14) -> Dict:
    """
    Check if ticker has earnings coming up.
    
    Args:
        ticker: Stock ticker
        warning_days: Days before earnings to warn (default 14)
        
    Returns:
    {
        'ticker': str,
        'has_risk': bool,
        'risk_level': 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE',
        'earnings_date': datetime or None,
        'days_until': int or None,
        'message': str,
    }
    """
    earnings = get_next_earnings(ticker)
    
    if earnings is None:
        return {
            'ticker': ticker,
            'has_risk': False,
            'risk_level': 'UNKNOWN',
            'earnings_date': None,
            'days_until': None,
            'message': 'Earnings date unknown - check manually',
        }
    
    days = earnings['days_until']
    
    if days <= 7:
        return {
            'ticker': ticker,
            'has_risk': True,
            'risk_level': 'HIGH',
            'earnings_date': earnings['earnings_date'],
            'days_until': days,
            'message': f'⛔ EARNINGS IN {days} DAYS - DO NOT BUY',
        }
    elif days <= 14:
        return {
            'ticker': ticker,
            'has_risk': True,
            'risk_level': 'MEDIUM',
            'earnings_date': earnings['earnings_date'],
            'days_until': days,
            'message': f'⚠️ Earnings in {days} days - HIGH RISK',
        }
    elif days <= 30:
        return {
            'ticker': ticker,
            'has_risk': False,
            'risk_level': 'LOW',
            'earnings_date': earnings['earnings_date'],
            'days_until': days,
            'message': f'📅 Earnings in {days} days - monitor',
        }
    else:
        return {
            'ticker': ticker,
            'has_risk': False,
            'risk_level': 'NONE',
            'earnings_date': earnings['earnings_date'],
            'days_until': days,
            'message': f'✅ Earnings in {days} days - safe',
        }


def get_earnings_for_watchlist(tickers: List[str]) -> List[Dict]:
    """Get earnings info for multiple tickers."""
    results = []
    
    for ticker in tickers:
        result = check_earnings_risk(ticker)
        results.append(result)
        
    # Sort by days until earnings (soonest first)
    results.sort(key=lambda x: x['days_until'] if x['days_until'] else 999)
    
    return results


def print_earnings_report(tickers: List[str]):
    """Print earnings calendar for a list of tickers."""
    print()
    print("=" * 60)
    print("  📅 EARNINGS CALENDAR")
    print("=" * 60)
    
    results = get_earnings_for_watchlist(tickers)
    
    # High risk
    high_risk = [r for r in results if r['risk_level'] == 'HIGH']
    if high_risk:
        print("\n  ⛔ HIGH RISK (< 7 days):")
        for r in high_risk:
            date_str = r['earnings_date'].strftime('%b %d') if r['earnings_date'] else '?'
            print(f"     {r['ticker']:6} - {date_str} ({r['days_until']} days)")
    
    # Medium risk
    med_risk = [r for r in results if r['risk_level'] == 'MEDIUM']
    if med_risk:
        print("\n  ⚠️ MEDIUM RISK (7-14 days):")
        for r in med_risk:
            date_str = r['earnings_date'].strftime('%b %d') if r['earnings_date'] else '?'
            print(f"     {r['ticker']:6} - {date_str} ({r['days_until']} days)")
    
    # Safe
    safe = [r for r in results if r['risk_level'] in ['LOW', 'NONE']]
    if safe:
        print("\n  ✅ SAFE (> 14 days):")
        for r in safe[:10]:  # Show top 10
            date_str = r['earnings_date'].strftime('%b %d') if r['earnings_date'] else '?'
            print(f"     {r['ticker']:6} - {date_str} ({r['days_until']} days)")
    
    # Unknown
    unknown = [r for r in results if r['risk_level'] == 'UNKNOWN']
    if unknown:
        print("\n  ❓ UNKNOWN:")
        for r in unknown:
            print(f"     {r['ticker']:6} - check manually")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Earnings Calendar")
    parser.add_argument("tickers", nargs="+", help="Tickers to check")
    
    args = parser.parse_args()
    
    tickers = [t.upper() for t in args.tickers]
    print_earnings_report(tickers)

