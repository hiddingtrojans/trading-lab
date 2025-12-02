"""
Short Interest Tracker

Track short interest changes to find potential squeeze candidates.

Data sources:
- FINRA (free, delayed 2 weeks)
- Yahoo Finance (free, approximate)

Why this matters:
- High short interest = lots of bets against the stock
- Rising short interest = more bears piling in
- Short squeeze = when shorts are forced to cover, sending price up
- Famous examples: GME, TSLA, AMC
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class ShortInterestData:
    """Short interest data for a stock."""
    ticker: str
    company_name: str
    
    # Current metrics
    short_interest: int  # Number of shares shorted
    short_pct_float: float  # % of float that is shorted
    short_ratio: float  # Days to cover (short interest / avg volume)
    
    # Change metrics (if available)
    prev_short_interest: Optional[int] = None
    change_pct: Optional[float] = None
    
    # Context
    avg_volume: int = 0
    float_shares: int = 0
    
    # Analysis
    signal: str = ""
    squeeze_risk: str = ""


class ShortInterestTracker:
    """
    Track short interest using free data sources.
    
    The edge: Identify potential squeeze setups before they happen.
    """
    
    def __init__(self):
        pass
    
    def get_short_interest(self, ticker: str) -> Optional[ShortInterestData]:
        """
        Get short interest data for a ticker.
        
        Uses Yahoo Finance which provides approximate short data.
        """
        ticker = ticker.upper()
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get key metrics
            short_interest = info.get('sharesShort', 0)
            short_pct_float = info.get('shortPercentOfFloat', 0) 
            short_ratio = info.get('shortRatio', 0)  # Days to cover
            prev_short_interest = info.get('sharesShortPriorMonth', 0)
            avg_volume = info.get('averageVolume', 0)
            float_shares = info.get('floatShares', 0)
            company_name = info.get('shortName', info.get('longName', ticker))
            
            if short_interest == 0 and short_pct_float == 0:
                return None
            
            # Calculate change
            change_pct = None
            if prev_short_interest and prev_short_interest > 0:
                change_pct = ((short_interest - prev_short_interest) / prev_short_interest) * 100
            
            # Convert short_pct_float to percentage if it's a ratio
            if short_pct_float and short_pct_float < 1:
                short_pct_float = short_pct_float * 100
            
            # Determine signal
            signal = self._determine_signal(short_pct_float, short_ratio, change_pct)
            squeeze_risk = self._assess_squeeze_risk(short_pct_float, short_ratio, change_pct)
            
            return ShortInterestData(
                ticker=ticker,
                company_name=company_name,
                short_interest=short_interest,
                short_pct_float=short_pct_float or 0,
                short_ratio=short_ratio or 0,
                prev_short_interest=prev_short_interest,
                change_pct=change_pct,
                avg_volume=avg_volume,
                float_shares=float_shares,
                signal=signal,
                squeeze_risk=squeeze_risk,
            )
            
        except Exception as e:
            print(f"   Error getting short data for {ticker}: {e}")
            return None
    
    def _determine_signal(self, short_pct: float, days_to_cover: float, change_pct: Optional[float]) -> str:
        """Determine the short interest signal."""
        signals = []
        
        # High short interest
        if short_pct >= 20:
            signals.append("🔴 Very High Short Interest")
        elif short_pct >= 10:
            signals.append("🟠 High Short Interest")
        elif short_pct >= 5:
            signals.append("🟡 Moderate Short Interest")
        else:
            signals.append("🟢 Low Short Interest")
        
        # Days to cover
        if days_to_cover >= 5:
            signals.append("⏰ Long Days to Cover")
        
        # Trend
        if change_pct:
            if change_pct >= 20:
                signals.append("📈 Shorts Increasing Rapidly")
            elif change_pct >= 5:
                signals.append("📈 Shorts Increasing")
            elif change_pct <= -20:
                signals.append("📉 Shorts Covering Rapidly")
            elif change_pct <= -5:
                signals.append("📉 Shorts Covering")
        
        return " | ".join(signals)
    
    def _assess_squeeze_risk(self, short_pct: float, days_to_cover: float, change_pct: Optional[float]) -> str:
        """Assess potential for a short squeeze."""
        score = 0
        
        # Short % of float scoring
        if short_pct >= 30:
            score += 3
        elif short_pct >= 20:
            score += 2
        elif short_pct >= 10:
            score += 1
        
        # Days to cover scoring
        if days_to_cover >= 7:
            score += 2
        elif days_to_cover >= 4:
            score += 1
        
        # Trend scoring (shorts increasing = more squeeze potential)
        if change_pct:
            if change_pct >= 20:
                score += 2
            elif change_pct >= 10:
                score += 1
        
        # Determine risk level
        if score >= 5:
            return "🚨 HIGH SQUEEZE POTENTIAL"
        elif score >= 3:
            return "⚠️ Moderate Squeeze Risk"
        elif score >= 1:
            return "📊 Low Squeeze Risk"
        else:
            return "✅ Minimal Squeeze Risk"
    
    def format_report(self, data: ShortInterestData) -> str:
        """Format short interest report for display."""
        lines = [
            "═" * 55,
            f"📊 SHORT INTEREST: {data.ticker}",
            f"   {data.company_name}",
            "═" * 55,
            "",
            f"Signal: {data.signal}",
            f"Squeeze Risk: {data.squeeze_risk}",
            "",
            "─" * 55,
            "KEY METRICS",
            "─" * 55,
            f"  Short Interest:     {data.short_interest:,} shares",
            f"  % of Float Shorted: {data.short_pct_float:.1f}%",
            f"  Days to Cover:      {data.short_ratio:.1f} days",
            f"  Avg Daily Volume:   {data.avg_volume:,}",
            f"  Float:              {data.float_shares:,} shares",
            "",
        ]
        
        if data.prev_short_interest and data.change_pct is not None:
            lines.append("─" * 55)
            lines.append("CHANGE FROM PRIOR MONTH")
            lines.append("─" * 55)
            change_emoji = "📈" if data.change_pct > 0 else "📉" if data.change_pct < 0 else "➡️"
            lines.append(f"  Previous:  {data.prev_short_interest:,} shares")
            lines.append(f"  Current:   {data.short_interest:,} shares")
            lines.append(f"  Change:    {change_emoji} {data.change_pct:+.1f}%")
            lines.append("")
        
        # Add interpretation
        lines.append("─" * 55)
        lines.append("INTERPRETATION")
        lines.append("─" * 55)
        
        if data.short_pct_float >= 20:
            lines.append("  ⚠️  HEAVILY SHORTED - Many are betting against this stock")
            lines.append("      High risk of squeeze if positive catalyst occurs")
        elif data.short_pct_float >= 10:
            lines.append("  🔸 Significant short interest - Bears are positioned")
            lines.append("     Watch for catalysts that could trigger covering")
        elif data.short_pct_float >= 5:
            lines.append("  📊 Moderate short interest - Some skepticism exists")
        else:
            lines.append("  ✅ Low short interest - Not a squeeze candidate")
        
        if data.short_ratio >= 5:
            lines.append(f"  ⏰ Takes {data.short_ratio:.0f} days to cover all shorts")
            lines.append("     Long covering time increases squeeze potential")
        
        if data.change_pct and data.change_pct >= 10:
            lines.append("  📈 Shorts are INCREASING - Bears getting more confident")
        elif data.change_pct and data.change_pct <= -10:
            lines.append("  📉 Shorts are COVERING - Bears losing confidence")
        
        lines.append("")
        lines.append("═" * 55)
        lines.append("📅 Data from Yahoo Finance (2-week delay typical)")
        lines.append("═" * 55)
        
        return "\n".join(lines)
    
    def scan_for_squeezes(self, tickers: List[str], min_short_pct: float = 10) -> List[ShortInterestData]:
        """
        Scan multiple tickers for potential squeeze candidates.
        
        Args:
            tickers: List of tickers to scan
            min_short_pct: Minimum short % of float
        
        Returns:
            List of stocks with high short interest
        """
        results = []
        
        print(f"\n📊 Scanning {len(tickers)} stocks for high short interest...")
        
        for i, ticker in enumerate(tickers):
            if i % 10 == 0 and i > 0:
                print(f"   Progress: {i}/{len(tickers)}...")
            
            data = self.get_short_interest(ticker)
            
            if data and data.short_pct_float >= min_short_pct:
                results.append(data)
                print(f"   ✅ {ticker}: {data.short_pct_float:.1f}% short ({data.squeeze_risk})")
        
        # Sort by short % of float
        results.sort(key=lambda x: x.short_pct_float, reverse=True)
        
        return results
    
    def find_squeeze_candidates(self, tickers: List[str]) -> List[ShortInterestData]:
        """Find stocks with highest squeeze potential."""
        all_data = []
        
        print(f"\n🎯 Finding squeeze candidates in {len(tickers)} stocks...")
        
        for ticker in tickers:
            data = self.get_short_interest(ticker)
            if data:
                all_data.append(data)
        
        # Filter and sort by squeeze potential
        squeeze_candidates = [
            d for d in all_data 
            if d.short_pct_float >= 10 or 
               (d.short_ratio >= 4 and d.short_pct_float >= 5)
        ]
        
        # Sort by a squeeze score
        def squeeze_score(d):
            score = d.short_pct_float * 2  # Weight short %
            score += d.short_ratio * 3  # Weight days to cover
            if d.change_pct and d.change_pct > 0:
                score += d.change_pct * 0.5  # Bonus for increasing shorts
            return score
        
        squeeze_candidates.sort(key=squeeze_score, reverse=True)
        
        return squeeze_candidates[:10]


def check_short_interest(ticker: str):
    """Quick check of short interest for a ticker."""
    tracker = ShortInterestTracker()
    
    print(f"\n📊 Checking short interest for {ticker}...")
    
    data = tracker.get_short_interest(ticker)
    
    if data:
        print(tracker.format_report(data))
    else:
        print(f"   No short interest data available for {ticker}")


def find_squeezes(tickers: List[str]):
    """Find squeeze candidates in a list of tickers."""
    tracker = ShortInterestTracker()
    
    candidates = tracker.find_squeeze_candidates(tickers)
    
    if candidates:
        print("\n" + "═" * 55)
        print("🎯 POTENTIAL SQUEEZE CANDIDATES")
        print("═" * 55)
        
        for data in candidates:
            print(f"\n{data.squeeze_risk}")
            print(f"   {data.ticker}: {data.short_pct_float:.1f}% short, {data.short_ratio:.1f} days to cover")
            if data.change_pct:
                change_emoji = "📈" if data.change_pct > 0 else "📉"
                print(f"   {change_emoji} {data.change_pct:+.1f}% change from last month")
    else:
        print("\n   No significant squeeze candidates found")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_short_interest(ticker)
    else:
        print("Usage: python short_interest_tracker.py TICKER")
        print("\nExample: python short_interest_tracker.py GME")
        print("\nThis shows:")
        print("  - Short interest (shares and % of float)")
        print("  - Days to cover")
        print("  - Change from prior month")
        print("  - Squeeze potential assessment")

