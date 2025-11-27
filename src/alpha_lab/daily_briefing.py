#!/usr/bin/env python3
"""
Daily Briefing Generator
========================

Automates the morning research routine:
1. Market Regime (Green/Yellow/Red?)
2. Leading Sectors (Where is money flowing?)
3. Top 3 Trade Ideas (Filtered by Sector & Quality)
4. Whale/Flow Checks on Ideas.

Usage:
    python src/alpha_lab/daily_briefing.py
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root) # Add root for unified_analyzer
sys.path.insert(0, os.path.join(project_root, 'src')) # Add src for utils

from unified_analyzer import UnifiedAnalyzer

class DailyBriefing:
    def __init__(self):
        self.analyzer = UnifiedAnalyzer()
        
    def generate_report(self):
        print("\n☕ Generating Daily Market Briefing...")
        print("   (This takes about 60 seconds)...")
        
        report = []
        report.append("="*60)
        report.append(f"🚀 DAILY MARKET BRIEFING | {datetime.now().strftime('%Y-%m-%d')}")
        report.append("="*60)
        
        # 1. Market Regime (SPY)
        print("   • Checking Market Regime...")
        spy_analysis = self.analyzer.analyze_ticker('SPY', ['fundamentals']) # Just trigger regime check
        regime = spy_analysis.get('market_regime', {})
        
        report.append(f"\n1. MARKET STATUS: {regime.get('status', 'UNKNOWN')}")
        report.append(f"   Score: {regime.get('score', 0)}/100")
        report.append(f"   Action: {regime.get('action', 'Wait')}")
        
        # 2. Sector Rotation
        print("   • Analyzing Sectors...")
        sector_res = self.analyzer.sector_analyzer.analyze_sectors()
        leading = sector_res.get('leading_sectors', [])
        
        report.append(f"\n2. LEADING SECTORS (Focus Here):")
        if leading:
            report.append(f"   🔥 {', '.join(leading)}")
        else:
            report.append("   ⚠️ No clear leaders (Market is choppy)")
            
        # 3. Find Top Ideas
        print("   • Screening for Top Opportunities...")
        # We want Growth stocks in Leading sectors
        screen_res = self.analyzer.screen_stocks('growth')
        
        # Filter by Leading Sectors (Approximate map)
        # We map ETF names back to yahoo sector names crudely or just check if stock's sector is leading
        
        top_picks = []
        for _, row in screen_res.iterrows():
            ticker = row['ticker']
            # Run quick check
            analysis = self.analyzer.analyze_ticker(ticker, ['intraday']) # Quick check
            sec_status = analysis.get('analyses', {}).get('sector_rotation', {}).get('status', '')
            
            # Prioritize Leading/Improving
            if sec_status in ['LEADING', 'IMPROVING']:
                top_picks.append(analysis)
                if len(top_picks) >= 3:
                    break
        
        report.append(f"\n3. TOP TRADE IDEAS (Sector Aligned):")
        if top_picks:
            for pick in top_picks:
                ticker = pick['ticker']
                price = pick['current_price']
                regime = pick['market_regime']['status']
                whale = pick['analyses'].get('whale_alert', {}).get('status', 'NEUTRAL')
                plan = pick.get('tactical_plan', {})
                
                report.append(f"\n   💎 {ticker} (${price:.2f})")
                report.append(f"      • Whale Flow: {whale}")
                if 'entry' in plan:
                    report.append(f"      • Plan: {plan['action']} @ ${plan['entry']:.2f} (Target: ${plan['target']:.2f})")
                else:
                    report.append(f"      • Plan: Wait for setup")
        else:
            report.append("   No high-quality setups found in leading sectors.")
            
        # Final Output
        print("\n" + "\n".join(report))
        
        # Save to file
        filename = f"data/output/daily_briefing_{datetime.now().strftime('%Y%m%d')}.txt"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write("\n".join(report))
        print(f"\n📄 Report saved to: {filename}")

if __name__ == "__main__":
    briefing = DailyBriefing()
    briefing.generate_report()

