#!/usr/bin/env python3
"""
DEEP RESEARCH PLATFORM
======================

Your edge: Doing the work others won't.

Commands:
    python deep_research.py                     # Show your watchlist
    python deep_research.py TICKER              # Full analysis of TICKER
    python deep_research.py --discover          # Quick discovery (500 stocks)
    python deep_research.py --weekly-scan       # Full scan (11,552 stocks) + track improvements
    python deep_research.py --improvements      # Show stocks that improved this week
    python deep_research.py --insiders TICKER   # Check insider buying (SEC Form 4)
    python deep_research.py --insiders          # Scan watchlist for insider buying
    python deep_research.py --institutions TICKER # Check 13F institutional holdings
    python deep_research.py --add TICKER        # Add to watchlist
    python deep_research.py --thesis TICKER     # Update your thesis
    python deep_research.py --alerts            # Check price alerts

The goal: Find and understand stocks BEFORE the crowd.
The edge: Track improvements over time, not just snapshots.
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from research.discovery import StockDiscovery, discover_stocks, run_weekly_discovery
from research.fundamentals import FundamentalAnalyzer, analyze_fundamentals
from research.business import BusinessAnalyzer, analyze_business
from research.database import (
    save_research, add_note, get_research, get_watchlist,
    format_watchlist, get_price_alerts
)
from research.discovery_db import DiscoveryDatabase
from research.insider_tracker import InsiderTracker, check_insider
from research.institutional_tracker import InstitutionalTracker, check_institutions


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
    
    # 3. Insider Activity (GPT can't do this - real-time SEC data)
    print("\n📍 Step 3: Insider Activity (SEC Form 4)...")
    tracker = InsiderTracker()
    insider_summary = tracker.get_insider_summary(ticker)
    if insider_summary:
        print(tracker.format_summary(insider_summary))
    else:
        print("   No recent insider transactions found")
    
    # 4. Technical Context (simple)
    print("\n📍 Step 4: Price Context...")
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


def show_improvements():
    """Show stocks that improved week-over-week."""
    db = DiscoveryDatabase()
    
    improvements = db.find_improvements(min_score_change=10)
    new_discoveries = db.get_new_discoveries()
    
    print("\n" + "═" * 60)
    print("📈 STOCKS THAT IMPROVED THIS WEEK")
    print("═" * 60)
    
    if not improvements and not new_discoveries:
        print("\n   No improvements detected.")
        print("   Run --weekly-scan first to build history.")
        print("\n" + "═" * 60)
        return
    
    if improvements:
        print("\n🚀 SCORE IMPROVEMENTS (+10 points or more)")
        print("─" * 60)
        for imp in improvements[:15]:
            fcf = " 🔥 FCF+" if imp.fcf_turned_positive else ""
            print(f"   {imp.ticker}: {imp.prev_score} → {imp.curr_score} (+{imp.score_change}){fcf}")
            print(f"      {imp.improvement_reason}")
            print()
    
    if new_discoveries:
        print("\n✨ NEW DISCOVERIES (just started meeting criteria)")
        print("─" * 60)
        for disc in new_discoveries[:10]:
            print(f"   {disc['ticker']}: Score {disc['score']}")
    
    # Show FCF flips prominently
    fcf_flips = [imp for imp in improvements if imp.fcf_turned_positive]
    if fcf_flips:
        print("\n" + "═" * 60)
        print("🔥 FCF TURNED POSITIVE (biggest signal)")
        print("═" * 60)
        for imp in fcf_flips:
            print(f"   💰 {imp.ticker} - Was burning cash, now profitable!")
    
    print("\n" + "═" * 60)
    print("These improved BEFORE the crowd noticed.")
    print("python deep_research.py TICKER for full analysis")
    print("═" * 60)


def show_score_trend(ticker: str):
    """Show a stock's score history over time."""
    ticker = ticker.upper()
    db = DiscoveryDatabase()
    
    trend = db.get_score_trend(ticker, weeks=8)
    
    if not trend:
        print(f"\n   No history for {ticker}. Run --weekly-scan to build history.")
        return
    
    print(f"\n📊 Score Trend for {ticker}")
    print("─" * 40)
    
    for week, score in trend:
        bar = "█" * (score // 5)
        print(f"   {week}: {score:3d} {bar}")
    
    if len(trend) >= 2:
        change = trend[-1][1] - trend[0][1]
        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        print(f"\n   {direction} Change over period: {change:+d} points")


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('ticker', nargs='?', help='Stock ticker to analyze')
    parser.add_argument('--discover', action='store_true', help='Quick discovery scan (500 stocks)')
    parser.add_argument('--weekly-scan', action='store_true', help='Full weekly scan (all 11,552 stocks)')
    parser.add_argument('--improvements', action='store_true', help='Show stocks that improved this week')
    parser.add_argument('--trend', metavar='TICKER', help='Show score trend for ticker')
    parser.add_argument('--add', metavar='TICKER', help='Add ticker to watchlist')
    parser.add_argument('--thesis', metavar='TICKER', help='Update thesis for ticker')
    parser.add_argument('--alerts', action='store_true', help='Check price alerts')
    parser.add_argument('--note', metavar='TICKER', help='Add note to ticker')
    parser.add_argument('--insiders', metavar='TICKER', nargs='?', const='watchlist', 
                        help='Check insider buying (TICKER or "watchlist")')
    parser.add_argument('--institutions', metavar='TICKER', 
                        help='Check institutional 13F holdings')
    parser.add_argument('--max-scan', type=int, default=500, help='Max stocks to scan in quick discover')
    
    args = parser.parse_args()
    
    if args.weekly_scan:
        # Full comprehensive scan
        results = run_weekly_discovery()
        # Show improvements after scan
        if results.get('improvements'):
            engine = StockDiscovery()
            print("\n" + engine.format_improvements_report(results['improvements']))
    elif args.discover:
        # Quick discovery
        discover_stocks(max_scan=args.max_scan)
    elif args.improvements:
        show_improvements()
    elif args.trend:
        show_score_trend(args.trend)
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
    elif args.insiders:
        if args.insiders == 'watchlist':
            # Scan watchlist for insider buying
            watchlist = get_watchlist()
            tickers = [w['ticker'] for w in watchlist]
            if not tickers:
                print("\n📭 Watchlist is empty. Add stocks with: python deep_research.py --add TICKER")
            else:
                tracker = InsiderTracker()
                results = tracker.scan_for_buying(tickers)
                if results:
                    print("\n" + "═" * 50)
                    print("🔔 INSIDER BUYING IN YOUR WATCHLIST")
                    print("═" * 50)
                    for summary in results:
                        print(f"\n{summary.signal}")
                        print(f"   {summary.ticker}: {summary.total_buys_30d} buys (${summary.buy_value_30d:,.0f})")
                else:
                    print("\n   No significant insider buying in watchlist")
        else:
            # Check single ticker
            check_insider(args.insiders)
    elif args.institutions:
        # Check institutional 13F holdings
        check_institutions(args.institutions)
    elif args.ticker:
        full_analysis(args.ticker)
    else:
        # Show watchlist
        print(format_watchlist())


if __name__ == "__main__":
    main()

