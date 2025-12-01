#!/usr/bin/env python3
"""
DEEP RESEARCH PLATFORM
======================

Your edge: Doing the work others won't.

Commands:
    python deep_research.py                     # Show your watchlist
    python deep_research.py TICKER              # Full analysis of TICKER
    python deep_research.py --discover          # Find undiscovered stocks
    python deep_research.py --add TICKER        # Add to watchlist
    python deep_research.py --thesis TICKER     # Update your thesis
    python deep_research.py --alerts            # Check price alerts

The goal: Find and understand stocks BEFORE the crowd.
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from research.discovery import StockDiscovery, discover_stocks
from research.fundamentals import FundamentalAnalyzer, analyze_fundamentals
from research.business import BusinessAnalyzer, analyze_business
from research.database import (
    save_research, add_note, get_research, get_watchlist,
    format_watchlist, get_price_alerts
)


def full_analysis(ticker: str):
    """Run complete analysis on a ticker."""
    ticker = ticker.upper()
    
    print("\n" + "═" * 60)
    print(f"🔬 DEEP RESEARCH: {ticker}")
    print("═" * 60)
    
    # 1. Business Understanding
    print("\n📍 Step 1: Understanding the Business...")
    business = BusinessAnalyzer(ticker)
    business.analyze()
    print(business.format_report())
    
    # 2. Fundamental Analysis
    print("\n📍 Step 2: Analyzing Financials...")
    fundamentals = FundamentalAnalyzer(ticker)
    fundamentals.analyze()
    print(fundamentals.format_report())
    
    # 3. Technical Context (simple)
    print("\n📍 Step 3: Price Context...")
    import yfinance as yf
    stock = yf.Ticker(ticker)
    hist = stock.history(period='1y')
    
    if not hist.empty:
        current = hist['Close'].iloc[-1]
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()
        sma_50 = hist['Close'].iloc[-50:].mean() if len(hist) >= 50 else current
        sma_200 = hist['Close'].iloc[-200:].mean() if len(hist) >= 200 else current
        
        print("─" * 60)
        print("PRICE CONTEXT")
        print("─" * 60)
        print(f"Current Price: ${current:.2f}")
        print(f"52-Week Range: ${low_52w:.2f} - ${high_52w:.2f}")
        print(f"Distance from 52w High: {((current/high_52w)-1)*100:.1f}%")
        print(f"Distance from 52w Low: {((current/low_52w)-1)*100:.1f}%")
        print(f"50-Day SMA: ${sma_50:.2f} ({'above' if current > sma_50 else 'below'})")
        print(f"200-Day SMA: ${sma_200:.2f} ({'above' if current > sma_200 else 'below'})")
    
    # 4. Check if in watchlist
    existing = get_research(ticker)
    if existing:
        print("\n" + "─" * 60)
        print("YOUR RESEARCH")
        print("─" * 60)
        print(f"Status: {existing['status']}")
        print(f"Conviction: {existing['conviction']}")
        if existing['thesis']:
            print(f"Thesis: {existing['thesis']}")
        if existing['buy_below']:
            print(f"Buy Below: ${existing['buy_below']:.2f}")
        if existing['sell_above']:
            print(f"Sell Above: ${existing['sell_above']:.2f}")
        if existing['notes']:
            print(f"\nRecent Notes:")
            for note in existing['notes'][:3]:
                print(f"  [{note['created_at'][:10]}] {note['note'][:60]}...")
    else:
        print("\n💡 Not in your watchlist. Add with: python deep_research.py --add " + ticker)
    
    print("\n" + "═" * 60)


def add_to_watchlist(ticker: str):
    """Add a stock to watchlist with basic info."""
    ticker = ticker.upper()
    
    import yfinance as yf
    stock = yf.Ticker(ticker)
    info = stock.info
    
    name = info.get('shortName', ticker)
    
    save_research(ticker=ticker, name=name, status='watching')
    
    print(f"\n✅ Added {ticker} ({name}) to watchlist")
    print(f"   Run: python deep_research.py {ticker}")
    print(f"   To do full analysis and set your thesis")


def update_thesis(ticker: str):
    """Interactive thesis update."""
    ticker = ticker.upper()
    
    existing = get_research(ticker)
    
    print(f"\n📝 Update Thesis for {ticker}")
    print("─" * 40)
    
    if existing and existing['thesis']:
        print(f"Current thesis: {existing['thesis']}")
    
    print("\nEnter your thesis (what makes this a good investment?):")
    thesis = input("> ").strip()
    
    print("\nBull case (what could go right?):")
    bull = input("> ").strip()
    
    print("\nBear case (what could go wrong?):")
    bear = input("> ").strip()
    
    print("\nBuy below price (your entry zone):")
    try:
        buy = float(input("> $").strip())
    except:
        buy = None
    
    print("\nSell above price (your target):")
    try:
        sell = float(input("> $").strip())
    except:
        sell = None
    
    print("\nConviction (low/medium/high):")
    conviction = input("> ").strip().lower()
    if conviction not in ['low', 'medium', 'high']:
        conviction = 'medium'
    
    # Get name if not exists
    name = None
    if not existing:
        import yfinance as yf
        name = yf.Ticker(ticker).info.get('shortName', ticker)
    
    save_research(
        ticker=ticker,
        name=name,
        thesis=thesis if thesis else None,
        bull_case=bull if bull else None,
        bear_case=bear if bear else None,
        buy_below=buy,
        sell_above=sell,
        conviction=conviction,
    )
    
    print(f"\n✅ Saved thesis for {ticker}")


def check_price_alerts():
    """Check if any watchlist stocks hit price targets."""
    import yfinance as yf
    
    alerts = get_price_alerts()
    
    if not alerts:
        print("\n📭 No price alerts set. Add targets with: python deep_research.py --thesis TICKER")
        return
    
    print("\n" + "═" * 60)
    print("📊 PRICE ALERT CHECK")
    print("═" * 60)
    
    triggered = []
    
    for stock in alerts:
        ticker = stock['ticker']
        try:
            current = yf.Ticker(ticker).info.get('regularMarketPrice', 0)
            
            buy_below = stock['buy_below']
            sell_above = stock['sell_above']
            
            status = "—"
            if buy_below and current <= buy_below:
                status = f"🟢 BUY ZONE (${current:.2f} ≤ ${buy_below:.2f})"
                triggered.append((ticker, 'buy', current, buy_below))
            elif sell_above and current >= sell_above:
                status = f"🔴 SELL ZONE (${current:.2f} ≥ ${sell_above:.2f})"
                triggered.append((ticker, 'sell', current, sell_above))
            else:
                status = f"👀 ${current:.2f}"
                if buy_below:
                    status += f" (buy < ${buy_below:.2f})"
            
            print(f"  {ticker}: {status}")
            
        except Exception as e:
            print(f"  {ticker}: Error getting price")
    
    if triggered:
        print("\n" + "─" * 60)
        print("⚠️  ALERTS TRIGGERED:")
        for ticker, action, current, target in triggered:
            print(f"   {ticker}: {action.upper()} at ${current:.2f} (target: ${target:.2f})")
    
    print("\n" + "═" * 60)
    
    return triggered


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('ticker', nargs='?', help='Stock ticker to analyze')
    parser.add_argument('--discover', action='store_true', help='Discover undercovered stocks')
    parser.add_argument('--add', metavar='TICKER', help='Add ticker to watchlist')
    parser.add_argument('--thesis', metavar='TICKER', help='Update thesis for ticker')
    parser.add_argument('--alerts', action='store_true', help='Check price alerts')
    parser.add_argument('--note', metavar='TICKER', help='Add note to ticker')
    
    args = parser.parse_args()
    
    if args.discover:
        discover_stocks()
    elif args.add:
        add_to_watchlist(args.add)
    elif args.thesis:
        update_thesis(args.thesis)
    elif args.alerts:
        check_price_alerts()
    elif args.note:
        ticker = args.note.upper()
        print(f"\nAdd note for {ticker}:")
        note = input("> ").strip()
        if note:
            add_note(ticker, note)
            print(f"✅ Note added")
    elif args.ticker:
        full_analysis(args.ticker)
    else:
        # Show watchlist
        print(format_watchlist())


if __name__ == "__main__":
    main()

