"""
Earnings History & Calendar Tracker

Track earnings beat/miss history and upcoming earnings dates.

Why this matters:
- Companies that consistently beat = quality management
- Knowing earnings date is critical for options timing
- GPT doesn't have real-time earnings calendar data
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class EarningsResult:
    """Single earnings result."""
    date: str
    quarter: str
    eps_estimate: Optional[float]
    eps_actual: Optional[float]
    surprise: Optional[float]  # Actual - Estimate
    surprise_pct: Optional[float]
    beat: Optional[bool]  # True = beat, False = miss, None = unknown


@dataclass
class EarningsSummary:
    """Complete earnings summary for a stock."""
    ticker: str
    company_name: str
    
    # Next earnings
    next_earnings_date: Optional[str]
    days_until_earnings: Optional[int]
    
    # Track record
    history: List[EarningsResult]
    beats: int
    misses: int
    total: int
    beat_rate: float
    avg_surprise_pct: float
    
    # Streaks
    current_streak: int  # Positive = beats, negative = misses
    streak_type: str  # "beat" or "miss"
    
    # Signal
    signal: str


class EarningsTracker:
    """
    Track earnings history and calendar.
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
    
    def analyze(self) -> EarningsSummary:
        """Analyze earnings history and get next earnings date."""
        
        company_name = self.info.get('shortName', self.ticker)
        
        # Get earnings history
        history = self._get_earnings_history()
        
        # Get next earnings date
        next_date, days_until = self._get_next_earnings()
        
        # Calculate stats
        beats = sum(1 for h in history if h.beat is True)
        misses = sum(1 for h in history if h.beat is False)
        total = beats + misses
        
        beat_rate = (beats / total * 100) if total > 0 else 0
        
        # Average surprise
        surprises = [h.surprise_pct for h in history if h.surprise_pct is not None]
        avg_surprise = sum(surprises) / len(surprises) if surprises else 0
        
        # Calculate streak
        streak, streak_type = self._calculate_streak(history)
        
        # Determine signal
        signal = self._determine_signal(beat_rate, streak, days_until)
        
        return EarningsSummary(
            ticker=self.ticker,
            company_name=company_name,
            next_earnings_date=next_date,
            days_until_earnings=days_until,
            history=history,
            beats=beats,
            misses=misses,
            total=total,
            beat_rate=beat_rate,
            avg_surprise_pct=avg_surprise,
            current_streak=streak,
            streak_type=streak_type,
            signal=signal,
        )
    
    def _get_earnings_history(self) -> List[EarningsResult]:
        """Get historical earnings results."""
        history = []
        
        try:
            # Get earnings history from yfinance
            earnings = self.stock.earnings_history
            
            if earnings is None or earnings.empty:
                # Try quarterly earnings
                quarterly = self.stock.quarterly_earnings
                if quarterly is not None and not quarterly.empty:
                    for idx, row in quarterly.iterrows():
                        date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                        quarter = self._get_quarter(idx) if hasattr(idx, 'month') else ""
                        
                        history.append(EarningsResult(
                            date=date_str,
                            quarter=quarter,
                            eps_estimate=None,
                            eps_actual=row.get('Earnings', None),
                            surprise=None,
                            surprise_pct=None,
                            beat=None,
                        ))
                return history
            
            for idx, row in earnings.iterrows():
                date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                quarter = self._get_quarter(idx) if hasattr(idx, 'month') else ""
                
                eps_estimate = row.get('epsEstimate', None)
                eps_actual = row.get('epsActual', None)
                
                surprise = None
                surprise_pct = None
                beat = None
                
                if eps_estimate is not None and eps_actual is not None:
                    surprise = eps_actual - eps_estimate
                    if eps_estimate != 0:
                        surprise_pct = (surprise / abs(eps_estimate)) * 100
                    beat = eps_actual > eps_estimate
                
                history.append(EarningsResult(
                    date=date_str,
                    quarter=quarter,
                    eps_estimate=eps_estimate,
                    eps_actual=eps_actual,
                    surprise=surprise,
                    surprise_pct=surprise_pct,
                    beat=beat,
                ))
            
            # Sort by date (newest first)
            history.sort(key=lambda x: x.date, reverse=True)
            
            return history[:12]  # Last 12 quarters (3 years)
            
        except Exception as e:
            return []
    
    def _get_quarter(self, date) -> str:
        """Get quarter string from date."""
        try:
            if hasattr(date, 'month'):
                month = date.month
                year = date.year
            else:
                return ""
            
            if month <= 3:
                return f"Q1 {year}"
            elif month <= 6:
                return f"Q2 {year}"
            elif month <= 9:
                return f"Q3 {year}"
            else:
                return f"Q4 {year}"
        except:
            return ""
    
    def _get_next_earnings(self) -> tuple:
        """Get next earnings date."""
        try:
            calendar = self.stock.calendar
            
            if calendar is None:
                return None, None
            
            # Handle different calendar formats
            if isinstance(calendar, dict):
                earnings_date = calendar.get('Earnings Date', [None])[0]
            else:
                # DataFrame format
                if 'Earnings Date' in calendar.columns:
                    earnings_date = calendar['Earnings Date'].iloc[0]
                elif 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date'].iloc[0]
                else:
                    return None, None
            
            if earnings_date is None:
                return None, None
            
            # Parse date
            if hasattr(earnings_date, 'strftime'):
                date_str = earnings_date.strftime('%Y-%m-%d')
                days_until = (earnings_date - datetime.now()).days
            else:
                date_str = str(earnings_date)[:10]
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    days_until = (dt - datetime.now()).days
                except:
                    days_until = None
            
            return date_str, days_until
            
        except Exception as e:
            return None, None
    
    def _calculate_streak(self, history: List[EarningsResult]) -> tuple:
        """Calculate current beat/miss streak."""
        if not history:
            return 0, "none"
        
        streak = 0
        streak_type = None
        
        for result in history:
            if result.beat is None:
                continue
            
            if streak_type is None:
                streak_type = "beat" if result.beat else "miss"
                streak = 1
            elif (result.beat and streak_type == "beat") or (not result.beat and streak_type == "miss"):
                streak += 1
            else:
                break
        
        return streak, streak_type or "none"
    
    def _determine_signal(self, beat_rate: float, streak: int, days_until: Optional[int]) -> str:
        """Determine overall earnings signal."""
        signals = []
        
        # Beat rate signal
        if beat_rate >= 80:
            signals.append("🟢 Consistent Beater")
        elif beat_rate >= 60:
            signals.append("🟡 Mostly Beats")
        elif beat_rate <= 40:
            signals.append("🔴 Frequent Misser")
        
        # Streak signal
        if streak >= 4:
            signals.append(f"🔥 {streak}-Quarter Beat Streak")
        elif streak >= 2 and streak < 4:
            signals.append(f"📈 {streak}-Quarter Streak")
        
        # Upcoming earnings
        if days_until is not None:
            if days_until <= 7:
                signals.append(f"⚠️ Earnings in {days_until} days!")
            elif days_until <= 14:
                signals.append(f"📅 Earnings in {days_until} days")
        
        return " | ".join(signals) if signals else "📊 Mixed Results"
    
    def format_report(self, summary: EarningsSummary) -> str:
        """Format earnings report for display."""
        lines = [
            "═" * 60,
            f"📅 EARNINGS ANALYSIS: {summary.ticker}",
            f"   {summary.company_name}",
            "═" * 60,
            "",
            f"Signal: {summary.signal}",
            "",
        ]
        
        # Next earnings
        lines.append("─" * 60)
        lines.append("NEXT EARNINGS")
        lines.append("─" * 60)
        
        if summary.next_earnings_date:
            lines.append(f"  📅 Date: {summary.next_earnings_date}")
            if summary.days_until_earnings is not None:
                if summary.days_until_earnings <= 0:
                    lines.append(f"  ⏰ Status: IMMINENT or just passed")
                elif summary.days_until_earnings <= 7:
                    lines.append(f"  ⚠️ Countdown: {summary.days_until_earnings} DAYS")
                else:
                    lines.append(f"  ⏰ Countdown: {summary.days_until_earnings} days")
        else:
            lines.append("  📅 Date: Not announced yet")
        
        lines.append("")
        
        # Track record
        lines.append("─" * 60)
        lines.append("TRACK RECORD")
        lines.append("─" * 60)
        lines.append(f"  ✅ Beats:     {summary.beats}")
        lines.append(f"  ❌ Misses:    {summary.misses}")
        lines.append(f"  📊 Beat Rate: {summary.beat_rate:.0f}%")
        lines.append(f"  📈 Avg Surprise: {summary.avg_surprise_pct:+.1f}%")
        
        if summary.current_streak >= 2:
            emoji = "🔥" if summary.streak_type == "beat" else "❄️"
            lines.append(f"  {emoji} Current Streak: {summary.current_streak} {summary.streak_type}s")
        
        lines.append("")
        
        # History
        if summary.history:
            lines.append("─" * 60)
            lines.append("RECENT HISTORY")
            lines.append("─" * 60)
            
            for result in summary.history[:8]:
                if result.beat is True:
                    emoji = "✅"
                    status = "BEAT"
                elif result.beat is False:
                    emoji = "❌"
                    status = "MISS"
                else:
                    emoji = "⚪"
                    status = "N/A"
                
                if result.eps_actual is not None:
                    eps_str = f"${result.eps_actual:.2f}"
                else:
                    eps_str = "N/A"
                
                surprise_str = ""
                if result.surprise_pct is not None:
                    surprise_str = f" ({result.surprise_pct:+.1f}%)"
                
                quarter = result.quarter or result.date[:7]
                lines.append(f"  {emoji} {quarter:8} {status:4} EPS: {eps_str}{surprise_str}")
            
            lines.append("")
        
        lines.append("═" * 60)
        lines.append("💡 Tip: Buy options BEFORE earnings, sell AFTER (IV crush)")
        lines.append("═" * 60)
        
        return "\n".join(lines)


def check_earnings(ticker: str):
    """Check earnings history and calendar for a ticker."""
    tracker = EarningsTracker(ticker)
    summary = tracker.analyze()
    print(tracker.format_report(summary))
    return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_earnings(ticker)
    else:
        print("Usage: python earnings_tracker.py TICKER")
        print("\nExample: python earnings_tracker.py AAPL")

