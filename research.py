#!/usr/bin/env python3
"""
RESEARCH LAUNCHER
=================

Quick deep-dive analysis on any ticker.
Uses GPT + FinBERT + Fundamentals for comprehensive analysis.

Usage:
    ./research.py NVDA           # Full analysis
    ./research.py NVDA --quick   # Fast analysis (no GPT, saves $)
    ./research.py NVDA --leaps   # Focus on LEAPS recommendation

This is the RESEARCH side - run locally when you want to dig deep.
The ALERTS side runs on AWS automatically.
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(ticker: str):
    """Print nice header."""
    print()
    print("=" * 60)
    print(f"  🔬 DEEP RESEARCH: {ticker}")
    print(f"  📅 {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print("=" * 60)
    print()


def run_quick_analysis(ticker: str):
    """Quick analysis without GPT (free)."""
    print("⚡ QUICK MODE (no GPT - free)")
    print("-" * 40)
    
    # FIRST: Check earnings risk (CRITICAL)
    try:
        from src.alpha_lab.earnings_calendar import check_earnings_risk
        earnings = check_earnings_risk(ticker)
        
        print()
        if earnings['risk_level'] == 'HIGH':
            print("  " + "="*50)
            print(f"  ⛔ {earnings['message']}")
            print("  ⛔ DO NOT BUY OPTIONS BEFORE EARNINGS")
            print("  " + "="*50)
            print()
            proceed = input("  Continue anyway? (y/N): ").strip().lower()
            if proceed != 'y':
                print("  Aborted. Check again after earnings.")
                return
        elif earnings['risk_level'] == 'MEDIUM':
            print(f"  {earnings['message']}")
        elif earnings['risk_level'] == 'UNKNOWN':
            print(f"  ⚠️ {earnings['message']}")
        else:
            print(f"  {earnings['message']}")
        print()
    except Exception as e:
        print(f"  ⚠️ Earnings check failed: {e}")
    
    # Second: Get news sentiment (FREE via Yahoo Finance + FinBERT)
    try:
        from src.alpha_lab.news_sentiment import get_ticker_sentiment, print_sentiment_report
        sentiment_result = get_ticker_sentiment(ticker, max_articles=10)
        print_sentiment_report(sentiment_result)
    except Exception as e:
        print(f"  ⚠️ News sentiment unavailable: {e}")
        sentiment_result = None
    
    # Then run fundamentals analysis
    try:
        from src.leaps.complete_leaps_system import CompleteLEAPSSystem
        
        system = CompleteLEAPSSystem(
            use_gpt=False,  # No GPT = free
            try_ibkr=True,
            use_finbert=False  # We use our own news_sentiment instead
        )
        
        result = system.complete_systematic_analysis(ticker)
        
        if result:
            system.display_complete_analysis(result)
        else:
            print(f"❌ Analysis failed for {ticker}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def run_full_analysis(ticker: str):
    """Full analysis with GPT (costs ~$0.05)."""
    print("🤖 FULL MODE (GPT enabled - ~$0.05)")
    print("-" * 40)
    print()
    print("⚠️  HONEST WARNING:")
    print("   GPT is NOT a replacement for real financial analysis.")
    print("   It doesn't have real-time data and can hallucinate.")
    print("   Use the fundamentals, not GPT predictions.")
    print()
    
    # Check for OpenAI key
    if not os.environ.get('OPENAI_API_KEY'):
        env_file = os.path.join(os.path.dirname(__file__), 'configs', 'openai.env')
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"').strip("'")
    
    if not os.environ.get('OPENAI_API_KEY'):
        print("⚠️  No OPENAI_API_KEY found. Running quick mode instead.")
        print("   To enable GPT: create configs/openai.env with OPENAI_API_KEY=sk-...")
        print()
        return run_quick_analysis(ticker)
    
    try:
        from src.leaps.complete_leaps_system import CompleteLEAPSSystem
        
        system = CompleteLEAPSSystem(
            use_gpt=True,
            try_ibkr=True,
            use_finbert=False  # FinBERT needs news source we don't have
        )
        
        result = system.complete_systematic_analysis(ticker)
        
        if result:
            system.display_complete_analysis(result)
        else:
            print(f"❌ Analysis failed for {ticker}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def run_leaps_focus(ticker: str):
    """Focus specifically on LEAPS recommendation."""
    print("📈 LEAPS FOCUS MODE")
    print("-" * 40)
    
    try:
        from src.leaps.complete_leaps_system import CompleteLEAPSSystem
        
        system = CompleteLEAPSSystem(
            use_gpt=True,
            try_ibkr=True,
            use_finbert=True
        )
        
        result = system.run_full_analysis(ticker)
        
        if result and 'leaps_recommendation' in result:
            print_leaps_summary(result, ticker)
        else:
            print(f"❌ LEAPS analysis failed for {ticker}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def print_summary(result: dict, ticker: str):
    """Print clean summary of analysis."""
    print()
    print("=" * 60)
    print(f"  📊 SUMMARY: {ticker}")
    print("=" * 60)
    
    # Overall score
    score = result.get('overall_score', 0)
    if score >= 70:
        verdict = "🟢 BULLISH"
    elif score >= 50:
        verdict = "🟡 NEUTRAL"
    else:
        verdict = "🔴 BEARISH"
    
    print(f"\n  Overall Score: {score}/100 {verdict}")
    
    # Key metrics
    fundamentals = result.get('fundamentals', {})
    print(f"\n  📈 Fundamentals:")
    print(f"     Revenue Growth: {fundamentals.get('revenue_growth', 'N/A')}%")
    print(f"     Gross Margin:   {fundamentals.get('gross_margin', 'N/A')}%")
    print(f"     Analyst Target: ${fundamentals.get('analyst_target', 'N/A')}")
    
    # Sentiment
    news = result.get('news', {})
    print(f"\n  📰 News Sentiment: {news.get('sentiment', 'N/A')}")
    
    # Price prediction
    gpt = result.get('gpt_analysis', {})
    price_pred = gpt.get('price_prediction', {})
    if price_pred:
        print(f"\n  🎯 Price Targets:")
        print(f"     12-month: ${price_pred.get('12_month_target', 'N/A')}")
        print(f"     24-month: ${price_pred.get('24_month_target', 'N/A')}")
        print(f"     Confidence: {price_pred.get('confidence_level', 'N/A')}%")
    
    # LEAPS recommendation
    leaps = result.get('leaps_recommendation', {})
    if leaps:
        print(f"\n  📜 LEAPS Strategy:")
        rec = leaps.get('recommendation', 'N/A')
        if rec == 'BUY':
            print(f"     Recommendation: 🟢 {rec}")
        elif rec == 'CONSIDER':
            print(f"     Recommendation: 🟡 {rec}")
        else:
            print(f"     Recommendation: 🔴 {rec}")
        print(f"     Strike: ${leaps.get('strike', 'N/A')}")
        print(f"     Expiry: {leaps.get('expiry', 'N/A')}")
        print(f"     Expected Return: {leaps.get('expected_return', 'N/A')}%")
    
    # Risks
    risks = result.get('key_risks', [])
    if risks:
        print(f"\n  ⚠️  Key Risks:")
        for risk in risks[:3]:
            print(f"     • {risk}")
    
    print()
    print("=" * 60)


def print_leaps_summary(result: dict, ticker: str):
    """Print focused LEAPS summary."""
    print()
    print("=" * 60)
    print(f"  📜 LEAPS RECOMMENDATION: {ticker}")
    print("=" * 60)
    
    leaps = result.get('leaps_recommendation', {})
    gpt = result.get('gpt_analysis', {})
    price_pred = gpt.get('price_prediction', {})
    fundamentals = result.get('fundamentals', {})
    
    current_price = fundamentals.get('current_price', 0)
    
    rec = leaps.get('recommendation', 'N/A')
    if rec == 'BUY':
        print(f"\n  🟢 RECOMMENDATION: BUY LEAPS")
    elif rec == 'CONSIDER':
        print(f"\n  🟡 RECOMMENDATION: CONSIDER")
    else:
        print(f"\n  🔴 RECOMMENDATION: AVOID")
    
    print(f"\n  Current Price: ${current_price:.2f}")
    print(f"  12-mo Target:  ${price_pred.get('12_month_target', 'N/A')}")
    print(f"  24-mo Target:  ${price_pred.get('24_month_target', 'N/A')}")
    
    print(f"\n  Suggested Contract:")
    print(f"     Strike: ${leaps.get('strike', 'N/A')}")
    print(f"     Expiry: {leaps.get('expiry', 'N/A')}")
    print(f"     Type:   CALL")
    
    exp_return = leaps.get('expected_return', 0)
    print(f"\n  Expected Return: {exp_return}%")
    
    # Position sizing
    print(f"\n  Position Sizing (assuming $10K portfolio):")
    print(f"     Max Risk: 5% = $500")
    print(f"     Suggested Contracts: 1-2")
    
    print()
    print("=" * 60)


def list_recent_alerts():
    """Show recent alerts that might need research."""
    print("\n📬 Recent Alerts (research candidates):")
    print("-" * 40)
    
    # Check for signal tracker data
    signals_file = os.path.join(os.path.dirname(__file__), 'data', 'signals.json')
    
    if os.path.exists(signals_file):
        import json
        with open(signals_file) as f:
            signals = json.load(f)
        
        recent = sorted(signals, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
        
        for sig in recent:
            ticker = sig.get('ticker', '?')
            signal_type = sig.get('type', '?')
            date = sig.get('timestamp', '')[:10]
            print(f"  • {ticker} - {signal_type} ({date})")
        
        print(f"\nRun: ./research.py <TICKER> for deep analysis")
    else:
        print("  No recent alerts found")
        print("  Alerts will appear here after the scanners run")


def main():
    parser = argparse.ArgumentParser(
        description="Deep research analysis on any ticker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./research.py NVDA           Full analysis with GPT
  ./research.py NVDA --quick   Fast analysis (no GPT, free)
  ./research.py NVDA --leaps   Focus on LEAPS recommendation
  ./research.py --alerts       Show recent alerts to research
        """
    )
    
    parser.add_argument('ticker', nargs='?', help='Stock ticker to analyze')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick mode (no GPT)')
    parser.add_argument('--leaps', '-l', action='store_true', help='Focus on LEAPS')
    parser.add_argument('--alerts', '-a', action='store_true', help='Show recent alerts')
    
    args = parser.parse_args()
    
    if args.alerts:
        list_recent_alerts()
        return
    
    if not args.ticker:
        parser.print_help()
        print("\n💡 Tip: Run ./research.py --alerts to see recent alert candidates")
        return
    
    ticker = args.ticker.upper()
    print_header(ticker)
    
    if args.quick:
        run_quick_analysis(ticker)
    elif args.leaps:
        run_leaps_focus(ticker)
    else:
        run_full_analysis(ticker)


if __name__ == "__main__":
    main()

