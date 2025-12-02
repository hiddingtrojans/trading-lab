"""
Buyback & Dividend Tracker

Track share buybacks and dividend history.

Why this matters:
- Buybacks reduce float = less supply = price support
- Dividends = income + signal of financial health
- Dividend growth = compound returns over time
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class BuybackData:
    """Buyback activity data."""
    ticker: str
    
    # Share count changes
    shares_outstanding: int
    shares_1yr_ago: Optional[int]
    shares_change: Optional[int]
    shares_change_pct: Optional[float]
    
    # Cash spent on buybacks (from cash flow)
    buyback_ttm: Optional[float]  # Last 12 months
    
    # Context
    market_cap: float
    free_cash_flow: Optional[float]
    
    # Analysis
    is_buying_back: bool
    buyback_yield: Optional[float]  # % of market cap spent on buybacks
    signal: str


@dataclass
class DividendData:
    """Dividend data."""
    ticker: str
    company_name: str
    
    # Current dividend
    dividend_rate: float  # Annual dividend per share
    dividend_yield: float  # As percentage
    
    # Payout analysis
    payout_ratio: Optional[float]  # % of earnings paid as dividends
    
    # Growth
    dividend_5yr_growth: Optional[float]  # 5-year CAGR
    
    # Streak
    ex_dividend_date: Optional[str]
    consecutive_years: Optional[int]  # Years of consecutive dividends
    
    # Safety
    fcf_payout_ratio: Optional[float]  # Dividend as % of free cash flow
    
    # Classification
    classification: str  # "Dividend Aristocrat", "Dividend King", etc.
    signal: str


class BuybackDividendTracker:
    """
    Track buybacks and dividends.
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
    
    def analyze_buybacks(self) -> BuybackData:
        """Analyze share buyback activity."""
        
        shares_outstanding = self.info.get('sharesOutstanding', 0)
        market_cap = self.info.get('marketCap', 0)
        fcf = self.info.get('freeCashflow', 0)
        
        # Get historical share count
        shares_1yr_ago = None
        shares_change = None
        shares_change_pct = None
        
        try:
            # Try to get from balance sheet
            balance = self.stock.quarterly_balance_sheet
            if balance is not None and not balance.empty:
                if 'Ordinary Shares Number' in balance.index:
                    shares_history = balance.loc['Ordinary Shares Number']
                    if len(shares_history) >= 4:
                        shares_1yr_ago = shares_history.iloc[-1]  # Oldest quarter
                        shares_now = shares_history.iloc[0]  # Most recent
                        shares_change = shares_now - shares_1yr_ago
                        if shares_1yr_ago > 0:
                            shares_change_pct = (shares_change / shares_1yr_ago) * 100
        except:
            pass
        
        # Get buyback amount from cash flow
        buyback_ttm = None
        try:
            cashflow = self.stock.quarterly_cashflow
            if cashflow is not None and not cashflow.empty:
                # Look for repurchase line items
                repurchase_labels = [
                    'Repurchase Of Capital Stock',
                    'Common Stock Repurchased',
                    'Repurchase of Common Stock',
                ]
                for label in repurchase_labels:
                    if label in cashflow.index:
                        buyback_ttm = abs(cashflow.loc[label].iloc[:4].sum())
                        break
        except:
            pass
        
        # Calculate buyback yield
        buyback_yield = None
        if buyback_ttm and market_cap > 0:
            buyback_yield = (buyback_ttm / market_cap) * 100
        
        # Determine if company is buying back
        is_buying_back = False
        if shares_change_pct and shares_change_pct < -1:  # Share count decreased
            is_buying_back = True
        elif buyback_ttm and buyback_ttm > 0:
            is_buying_back = True
        
        # Generate signal
        signal = self._buyback_signal(is_buying_back, shares_change_pct, buyback_yield)
        
        return BuybackData(
            ticker=self.ticker,
            shares_outstanding=shares_outstanding,
            shares_1yr_ago=shares_1yr_ago,
            shares_change=shares_change,
            shares_change_pct=shares_change_pct,
            buyback_ttm=buyback_ttm,
            market_cap=market_cap,
            free_cash_flow=fcf,
            is_buying_back=is_buying_back,
            buyback_yield=buyback_yield,
            signal=signal,
        )
    
    def _buyback_signal(self, is_buying_back: bool, change_pct: Optional[float], 
                        buyback_yield: Optional[float]) -> str:
        """Generate buyback signal."""
        if not is_buying_back:
            return "⚪ No Active Buyback"
        
        signals = []
        
        if change_pct and change_pct < -5:
            signals.append("🟢 Aggressive Buyback")
        elif change_pct and change_pct < -2:
            signals.append("🟢 Active Buyback")
        elif change_pct and change_pct < 0:
            signals.append("🟡 Modest Buyback")
        
        if buyback_yield and buyback_yield > 5:
            signals.append("💰 High Buyback Yield")
        elif buyback_yield and buyback_yield > 2:
            signals.append("💵 Good Buyback Yield")
        
        return " | ".join(signals) if signals else "🟢 Buying Back Shares"
    
    def analyze_dividends(self) -> DividendData:
        """Analyze dividend history and safety."""
        
        company_name = self.info.get('shortName', self.ticker)
        
        # Current dividend info
        dividend_rate = self.info.get('dividendRate', 0) or 0
        dividend_yield = self.info.get('dividendYield', 0) or 0
        # Convert if needed (sometimes comes as ratio, sometimes as pct)
        if dividend_yield > 1:
            dividend_yield = dividend_yield  # Already percentage
        else:
            dividend_yield = dividend_yield * 100  # Convert ratio to percentage
        
        # Payout ratio
        payout_ratio = self.info.get('payoutRatio', None)
        if payout_ratio:
            payout_ratio = payout_ratio * 100 if payout_ratio < 1 else payout_ratio
        
        # 5-year growth
        dividend_5yr_growth = self.info.get('fiveYearAvgDividendYield', None)
        
        # Ex-dividend date
        ex_date = self.info.get('exDividendDate', None)
        ex_dividend_date = None
        if ex_date:
            try:
                if isinstance(ex_date, (int, float)):
                    ex_dividend_date = datetime.fromtimestamp(ex_date).strftime('%Y-%m-%d')
                else:
                    ex_dividend_date = str(ex_date)[:10]
            except:
                pass
        
        # FCF payout ratio
        fcf = self.info.get('freeCashflow', 0)
        shares = self.info.get('sharesOutstanding', 0)
        fcf_payout = None
        if fcf and fcf > 0 and shares and dividend_rate:
            total_dividend = dividend_rate * shares
            fcf_payout = (total_dividend / fcf) * 100
        
        # Determine consecutive years (approximate from history)
        consecutive_years = self._estimate_dividend_years()
        
        # Classification
        classification = self._classify_dividend(dividend_yield, consecutive_years, payout_ratio)
        
        # Signal
        signal = self._dividend_signal(dividend_yield, payout_ratio, fcf_payout)
        
        return DividendData(
            ticker=self.ticker,
            company_name=company_name,
            dividend_rate=dividend_rate,
            dividend_yield=dividend_yield,
            payout_ratio=payout_ratio,
            dividend_5yr_growth=dividend_5yr_growth,
            ex_dividend_date=ex_dividend_date,
            consecutive_years=consecutive_years,
            fcf_payout_ratio=fcf_payout,
            classification=classification,
            signal=signal,
        )
    
    def _estimate_dividend_years(self) -> Optional[int]:
        """Estimate consecutive dividend years from history."""
        try:
            dividends = self.stock.dividends
            if dividends is None or dividends.empty:
                return 0
            
            # Count unique years with dividends
            years = set()
            for date in dividends.index:
                years.add(date.year)
            
            return len(years)
        except:
            return None
    
    def _classify_dividend(self, div_yield: float, years: Optional[int], 
                          payout: Optional[float]) -> str:
        """Classify dividend stock."""
        if not div_yield or div_yield == 0:
            return "⚪ Non-Dividend Stock"
        
        if years and years >= 50:
            return "👑 Dividend King (50+ years)"
        elif years and years >= 25:
            return "🏆 Dividend Aristocrat (25+ years)"
        elif years and years >= 10:
            return "⭐ Dividend Achiever (10+ years)"
        elif div_yield >= 5:
            return "💰 High Yield Stock"
        elif div_yield >= 2:
            return "📈 Income Stock"
        else:
            return "💵 Dividend Payer"
    
    def _dividend_signal(self, div_yield: float, payout: Optional[float],
                        fcf_payout: Optional[float]) -> str:
        """Generate dividend signal."""
        if not div_yield or div_yield == 0:
            return "❌ No Dividend"
        
        signals = []
        
        # Yield analysis
        if div_yield >= 6:
            signals.append("⚠️ Very High Yield (risk?)")
        elif div_yield >= 4:
            signals.append("🟢 High Yield")
        elif div_yield >= 2:
            signals.append("🟡 Moderate Yield")
        else:
            signals.append("📊 Low Yield")
        
        # Safety analysis
        if payout:
            if payout > 100:
                signals.append("🔴 Unsustainable Payout")
            elif payout > 80:
                signals.append("⚠️ High Payout Ratio")
            elif payout < 50:
                signals.append("✅ Safe Payout")
        
        if fcf_payout:
            if fcf_payout > 100:
                signals.append("🔴 FCF Doesn't Cover")
            elif fcf_payout < 60:
                signals.append("✅ Well Covered by FCF")
        
        return " | ".join(signals)
    
    def format_report(self, buyback: BuybackData, dividend: DividendData) -> str:
        """Format combined buyback and dividend report."""
        lines = [
            "═" * 60,
            f"💰 SHAREHOLDER RETURNS: {self.ticker}",
            f"   {dividend.company_name}",
            "═" * 60,
            "",
        ]
        
        # Buyback section
        lines.append("─" * 60)
        lines.append("📉 SHARE BUYBACKS")
        lines.append("─" * 60)
        lines.append(f"  Signal: {buyback.signal}")
        lines.append("")
        lines.append(f"  Shares Outstanding: {buyback.shares_outstanding:,}")
        
        if buyback.shares_change_pct is not None:
            emoji = "📉" if buyback.shares_change_pct < 0 else "📈"
            lines.append(f"  YoY Change: {emoji} {buyback.shares_change_pct:+.1f}%")
        
        if buyback.buyback_ttm:
            lines.append(f"  Buybacks (TTM): ${buyback.buyback_ttm/1e9:.1f}B")
        
        if buyback.buyback_yield:
            lines.append(f"  Buyback Yield: {buyback.buyback_yield:.1f}%")
        
        if buyback.free_cash_flow:
            fcf_b = buyback.free_cash_flow / 1e9
            lines.append(f"  Free Cash Flow: ${fcf_b:.1f}B")
        
        lines.append("")
        
        # Dividend section
        lines.append("─" * 60)
        lines.append("💵 DIVIDENDS")
        lines.append("─" * 60)
        lines.append(f"  Classification: {dividend.classification}")
        lines.append(f"  Signal: {dividend.signal}")
        lines.append("")
        
        if dividend.dividend_rate > 0:
            lines.append(f"  Annual Dividend: ${dividend.dividend_rate:.2f}/share")
            lines.append(f"  Dividend Yield: {dividend.dividend_yield:.2f}%")
            
            if dividend.payout_ratio:
                lines.append(f"  Payout Ratio: {dividend.payout_ratio:.0f}% of earnings")
            
            if dividend.fcf_payout_ratio:
                lines.append(f"  FCF Payout: {dividend.fcf_payout_ratio:.0f}% of free cash flow")
            
            if dividend.ex_dividend_date:
                lines.append(f"  Ex-Dividend Date: {dividend.ex_dividend_date}")
            
            if dividend.consecutive_years:
                lines.append(f"  Dividend History: ~{dividend.consecutive_years} years")
        else:
            lines.append("  ❌ This stock does not pay dividends")
        
        lines.append("")
        
        # Total shareholder return
        lines.append("─" * 60)
        lines.append("📊 TOTAL SHAREHOLDER YIELD")
        lines.append("─" * 60)
        
        total_yield = dividend.dividend_yield + (buyback.buyback_yield or 0)
        lines.append(f"  Dividend Yield:     {dividend.dividend_yield:.1f}%")
        lines.append(f"  Buyback Yield:      {buyback.buyback_yield or 0:.1f}%")
        lines.append(f"  ─────────────────────────")
        lines.append(f"  TOTAL:              {total_yield:.1f}%")
        
        lines.append("")
        lines.append("═" * 60)
        
        return "\n".join(lines)


def check_buyback_dividend(ticker: str):
    """Check buyback and dividend data for a ticker."""
    tracker = BuybackDividendTracker(ticker)
    buyback = tracker.analyze_buybacks()
    dividend = tracker.analyze_dividends()
    print(tracker.format_report(buyback, dividend))
    return buyback, dividend


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_buyback_dividend(ticker)
    else:
        print("Usage: python buyback_dividend.py TICKER")
        print("\nExample: python buyback_dividend.py AAPL")

