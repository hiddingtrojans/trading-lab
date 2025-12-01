"""
Smart Discovery

Discovery + GPT Moat Analysis = Actually Useful Output

Flow:
1. Scan universe for numerical criteria (free, fast)
2. Filter through GPT moat analyzer (cheap, smart)
3. Only show GOOD or strong MEH stocks

This is what the scanner should have been from the start.
"""

import os
import sys
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.research.discovery import StockDiscovery
from src.research.moat_analyzer import MoatAnalyzer, MoatAnalysis
from src.alpha_lab.telegram_alerts import send_message
import yfinance as yf


def smart_discover(
    max_scan: int = 300,
    min_moat_score: int = 6,
    send_telegram: bool = True,
) -> List[Dict]:
    """
    Smart discovery: Numbers + Moat Analysis.
    
    Args:
        max_scan: Max stocks to scan in universe
        min_moat_score: Minimum GPT moat score (1-10) to include
        send_telegram: Send results to Telegram
    
    Returns:
        List of vetted stocks with moat analysis
    """
    print("\n" + "=" * 60)
    print("🧠 SMART DISCOVERY")
    print("   Numbers + GPT Moat Analysis")
    print("=" * 60)
    
    # Step 1: Numerical discovery
    print("\n📊 Step 1: Scanning universe for numbers...")
    discovery = StockDiscovery()
    candidates = discovery.scan_universe(
        min_market_cap=0.3,
        max_market_cap=10.0,
        min_revenue_growth=10.0,
        min_score=40,
        max_analyst_count=15,
        max_stocks_to_scan=max_scan,
    )
    
    if not candidates:
        print("   No candidates found")
        return []
    
    print(f"\n   Found {len(candidates)} numerical candidates")
    
    # Step 2: GPT Moat Analysis
    print("\n🧠 Step 2: GPT Moat Analysis...")
    print(f"   Filtering to moat score >= {min_moat_score}/10")
    
    analyzer = MoatAnalyzer()
    vetted = []
    rejected = []
    
    for i, stock in enumerate(candidates):
        print(f"   [{i+1}/{len(candidates)}] Analyzing {stock.ticker}...")
        
        try:
            # Get full info for GPT
            info = yf.Ticker(stock.ticker).info
            
            analysis = analyzer.analyze(
                ticker=stock.ticker,
                name=stock.name,
                sector=stock.sector,
                industry=stock.industry,
                description=info.get('longBusinessSummary', ''),
                revenue_b=info.get('totalRevenue', 0) / 1e9,
                revenue_growth=stock.revenue_growth,
                gross_margin=stock.gross_margin,
                operating_margin=(info.get('operatingMargins', 0) or 0) * 100,
            )
            
            if analysis:
                if analysis.moat_score >= min_moat_score and analysis.verdict != "GARBAGE":
                    vetted.append({
                        'stock': stock,
                        'moat': analysis,
                    })
                    print(f"      ✅ {analysis.verdict} - Moat {analysis.moat_score}/10")
                else:
                    rejected.append({
                        'stock': stock,
                        'moat': analysis,
                        'reason': f"{analysis.verdict} (Moat {analysis.moat_score}/10)"
                    })
                    print(f"      ❌ {analysis.verdict} - {analysis.one_liner[:40]}")
            
        except Exception as e:
            print(f"      ⚠️ Error: {e}")
            continue
    
    # Step 3: Results
    print("\n" + "=" * 60)
    print("📊 SMART DISCOVERY RESULTS")
    print("=" * 60)
    
    print(f"\n   Scanned: {max_scan} stocks")
    print(f"   Numerical candidates: {len(candidates)}")
    print(f"   Passed moat filter: {len(vetted)}")
    print(f"   Rejected: {len(rejected)}")
    
    if vetted:
        print("\n" + "-" * 60)
        print("✅ VETTED OPPORTUNITIES")
        print("-" * 60)
        
        # Sort by moat score
        vetted.sort(key=lambda x: x['moat'].moat_score, reverse=True)
        
        for item in vetted:
            stock = item['stock']
            moat = item['moat']
            print(f"\n{analyzer.format_analysis(moat)}")
            print(f"   Numbers: ${stock.market_cap}B cap | +{stock.revenue_growth}% growth | Score {stock.score}")
    
    # Step 4: Telegram Alert
    if send_telegram and vetted:
        alert = format_smart_alert(vetted, len(candidates), len(rejected))
        print("\n📤 Sending to Telegram...")
        success = send_message(alert)
        print("   ✅ Sent!" if success else "   ❌ Failed")
    
    return vetted


def format_smart_alert(vetted: List[Dict], total_candidates: int, rejected: int) -> str:
    """Format smart discovery for Telegram."""
    lines = [
        "🧠 SMART DISCOVERY",
        f"   {datetime.now().strftime('%b %d, %Y')}",
        "",
        f"Scanned → {total_candidates} numerical candidates",
        f"Rejected → {rejected} (banks, commodities, weak moat)",
        f"Passed → {len(vetted)} real opportunities",
        "",
        "═══ VETTED STOCKS ═══",
        "",
    ]
    
    for item in vetted[:5]:
        stock = item['stock']
        moat = item['moat']
        
        # Verdict emoji
        emoji = "✅" if moat.verdict == "GOOD" else "😐"
        
        # Moat indicators
        moat_str = []
        if moat.has_recurring_revenue:
            moat_str.append("🔄")
        if moat.has_switching_costs:
            moat_str.append("🔒")
        if moat.has_network_effects:
            moat_str.append("🕸️")
        if moat.has_pricing_power:
            moat_str.append("💰")
        
        lines.extend([
            f"{emoji} {stock.ticker} - Moat {moat.moat_score}/10 {''.join(moat_str)}",
            f"   {moat.one_liner}",
            f"   ${stock.market_cap}B | +{stock.revenue_growth}% growth",
            f"   💡 {moat.recommendation[:60]}",
            "",
        ])
    
    if len(vetted) > 5:
        lines.append(f"   ... and {len(vetted)-5} more")
        lines.append("")
    
    lines.append("─────────────────")
    lines.append("python deep_research.py TICKER")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', type=int, default=300, help='Max stocks to scan')
    parser.add_argument('--min-moat', type=int, default=6, help='Min moat score (1-10)')
    parser.add_argument('--no-telegram', action='store_true')
    
    args = parser.parse_args()
    
    results = smart_discover(
        max_scan=args.scan,
        min_moat_score=args.min_moat,
        send_telegram=not args.no_telegram,
    )

