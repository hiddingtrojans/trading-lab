"""
Fundamental Analysis Module

Deep dive into company financials:
- Revenue & earnings trends
- Margin analysis
- Cash flow health
- Balance sheet strength
- Valuation vs peers

This is the work others won't do. That's the edge.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
import json


@dataclass
class FundamentalAnalysis:
    """Complete fundamental analysis of a stock."""
    ticker: str
    name: str
    sector: str
    industry: str
    
    # Valuation
    market_cap: float
    enterprise_value: float
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    ps_ratio: Optional[float]
    pb_ratio: Optional[float]
    ev_ebitda: Optional[float]
    
    # Growth
    revenue_growth: float
    earnings_growth: float
    revenue_3yr_cagr: Optional[float]
    
    # Profitability
    gross_margin: float
    operating_margin: float
    net_margin: float
    roe: float
    roa: float
    
    # Cash Flow
    free_cash_flow: float
    fcf_margin: float
    operating_cash_flow: float
    
    # Balance Sheet
    total_cash: float
    total_debt: float
    debt_to_equity: float
    current_ratio: float
    
    # Quality
    insider_ownership: float
    institutional_ownership: float
    short_percent: float
    
    # Historical data
    revenue_history: List[Dict]
    earnings_history: List[Dict]


class FundamentalAnalyzer:
    """
    Deep fundamental analysis of companies.
    
    The goal: Understand the business, not just the stock.
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self.analysis: Optional[FundamentalAnalysis] = None
    
    def analyze(self) -> FundamentalAnalysis:
        """Run complete fundamental analysis."""
        info = self.info
        
        # Basic info
        name = info.get('shortName', self.ticker)
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        # Valuation metrics
        market_cap = info.get('marketCap', 0) / 1e9
        ev = info.get('enterpriseValue', 0) / 1e9
        pe = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        ps = info.get('priceToSalesTrailing12Months')
        pb = info.get('priceToBook')
        ev_ebitda = info.get('enterpriseToEbitda')
        
        # Growth metrics
        revenue_growth = (info.get('revenueGrowth', 0) or 0) * 100
        earnings_growth = (info.get('earningsGrowth', 0) or 0) * 100
        
        # Calculate 3-year CAGR from financials
        revenue_3yr_cagr = self._calculate_revenue_cagr()
        
        # Profitability
        gross_margin = (info.get('grossMargins', 0) or 0) * 100
        operating_margin = (info.get('operatingMargins', 0) or 0) * 100
        net_margin = (info.get('profitMargins', 0) or 0) * 100
        roe = (info.get('returnOnEquity', 0) or 0) * 100
        roa = (info.get('returnOnAssets', 0) or 0) * 100
        
        # Cash flow
        fcf = info.get('freeCashflow', 0) / 1e9
        ocf = info.get('operatingCashflow', 0) / 1e9
        revenue = info.get('totalRevenue', 1)
        fcf_margin = (info.get('freeCashflow', 0) / revenue * 100) if revenue else 0
        
        # Balance sheet
        total_cash = info.get('totalCash', 0) / 1e9
        total_debt = info.get('totalDebt', 0) / 1e9
        debt_to_equity = info.get('debtToEquity', 0) or 0
        current_ratio = info.get('currentRatio', 0) or 0
        
        # Quality metrics
        insider_own = (info.get('heldPercentInsiders', 0) or 0) * 100
        inst_own = (info.get('heldPercentInstitutions', 0) or 0) * 100
        short_pct = (info.get('shortPercentOfFloat', 0) or 0) * 100
        
        # Historical financials
        revenue_history = self._get_revenue_history()
        earnings_history = self._get_earnings_history()
        
        self.analysis = FundamentalAnalysis(
            ticker=self.ticker,
            name=name,
            sector=sector,
            industry=industry,
            market_cap=round(market_cap, 2),
            enterprise_value=round(ev, 2),
            pe_ratio=round(pe, 1) if pe else None,
            forward_pe=round(forward_pe, 1) if forward_pe else None,
            ps_ratio=round(ps, 2) if ps else None,
            pb_ratio=round(pb, 2) if pb else None,
            ev_ebitda=round(ev_ebitda, 1) if ev_ebitda else None,
            revenue_growth=round(revenue_growth, 1),
            earnings_growth=round(earnings_growth, 1),
            revenue_3yr_cagr=round(revenue_3yr_cagr, 1) if revenue_3yr_cagr else None,
            gross_margin=round(gross_margin, 1),
            operating_margin=round(operating_margin, 1),
            net_margin=round(net_margin, 1),
            roe=round(roe, 1),
            roa=round(roa, 1),
            free_cash_flow=round(fcf, 2),
            fcf_margin=round(fcf_margin, 1),
            operating_cash_flow=round(ocf, 2),
            total_cash=round(total_cash, 2),
            total_debt=round(total_debt, 2),
            debt_to_equity=round(debt_to_equity / 100, 2) if debt_to_equity > 10 else round(debt_to_equity, 2),
            current_ratio=round(current_ratio, 2),
            insider_ownership=round(insider_own, 1),
            institutional_ownership=round(inst_own, 1),
            short_percent=round(short_pct, 1),
            revenue_history=revenue_history,
            earnings_history=earnings_history,
        )
        
        return self.analysis
    
    def _calculate_revenue_cagr(self) -> Optional[float]:
        """Calculate 3-year revenue CAGR."""
        try:
            financials = self.stock.financials
            if financials is None or financials.empty:
                return None
            
            if 'Total Revenue' in financials.index:
                revenues = financials.loc['Total Revenue'].dropna()
            else:
                return None
            
            if len(revenues) < 3:
                return None
            
            # Most recent and 3 years ago
            current = revenues.iloc[0]
            past = revenues.iloc[min(3, len(revenues)-1)]
            
            if past <= 0 or current <= 0:
                return None
            
            years = min(3, len(revenues) - 1)
            cagr = ((current / past) ** (1 / years) - 1) * 100
            return cagr
            
        except Exception:
            return None
    
    def _get_revenue_history(self) -> List[Dict]:
        """Get historical revenue data."""
        try:
            financials = self.stock.financials
            if financials is None or financials.empty:
                return []
            
            if 'Total Revenue' in financials.index:
                revenues = financials.loc['Total Revenue'].dropna()
                return [
                    {'year': str(date.year), 'revenue': float(val) / 1e9}
                    for date, val in revenues.items()
                ]
            return []
        except Exception:
            return []
    
    def _get_earnings_history(self) -> List[Dict]:
        """Get historical earnings data."""
        try:
            financials = self.stock.financials
            if financials is None or financials.empty:
                return []
            
            if 'Net Income' in financials.index:
                earnings = financials.loc['Net Income'].dropna()
                return [
                    {'year': str(date.year), 'earnings': float(val) / 1e9}
                    for date, val in earnings.items()
                ]
            return []
        except Exception:
            return []
    
    def get_quality_score(self) -> tuple[int, List[str]]:
        """Calculate fundamental quality score."""
        if not self.analysis:
            self.analyze()
        
        a = self.analysis
        score = 0
        positives = []
        negatives = []
        
        # Growth (0-25)
        if a.revenue_growth > 25:
            score += 25
            positives.append(f"Strong revenue growth ({a.revenue_growth}%)")
        elif a.revenue_growth > 10:
            score += 15
            positives.append(f"Decent revenue growth ({a.revenue_growth}%)")
        elif a.revenue_growth > 0:
            score += 5
        else:
            negatives.append(f"Revenue declining ({a.revenue_growth}%)")
        
        # Margins (0-20)
        if a.gross_margin > 60:
            score += 10
            positives.append(f"High gross margin ({a.gross_margin}%)")
        elif a.gross_margin > 40:
            score += 5
        
        if a.operating_margin > 20:
            score += 10
            positives.append(f"Strong operating margin ({a.operating_margin}%)")
        elif a.operating_margin > 10:
            score += 5
        elif a.operating_margin < 0:
            negatives.append(f"Negative operating margin ({a.operating_margin}%)")
        
        # Cash flow (0-20)
        if a.free_cash_flow > 0:
            score += 10
            if a.fcf_margin > 15:
                score += 10
                positives.append(f"Strong FCF margin ({a.fcf_margin}%)")
            elif a.fcf_margin > 5:
                score += 5
        else:
            negatives.append("Negative free cash flow")
        
        # Balance sheet (0-15)
        if a.debt_to_equity < 0.5:
            score += 10
            positives.append("Low debt")
        elif a.debt_to_equity < 1:
            score += 5
        elif a.debt_to_equity > 2:
            negatives.append(f"High debt ({a.debt_to_equity}x D/E)")
        
        if a.current_ratio > 1.5:
            score += 5
        elif a.current_ratio < 1:
            negatives.append("Weak liquidity")
        
        # Insider ownership (0-10)
        if a.insider_ownership > 15:
            score += 10
            positives.append(f"High insider ownership ({a.insider_ownership}%)")
        elif a.insider_ownership > 5:
            score += 5
        
        # Valuation (0-10)
        if a.ps_ratio and a.ps_ratio < 3:
            score += 10
            positives.append(f"Reasonable valuation ({a.ps_ratio}x P/S)")
        elif a.ps_ratio and a.ps_ratio < 5:
            score += 5
        elif a.ps_ratio and a.ps_ratio > 15:
            negatives.append(f"Expensive ({a.ps_ratio}x P/S)")
        
        return min(score, 100), positives, negatives
    
    def format_report(self) -> str:
        """Format analysis as readable report."""
        if not self.analysis:
            self.analyze()
        
        a = self.analysis
        score, positives, negatives = self.get_quality_score()
        
        lines = [
            "═" * 60,
            f"📊 FUNDAMENTAL ANALYSIS: {a.ticker}",
            f"   {a.name}",
            "═" * 60,
            "",
            f"Quality Score: {score}/100",
            "",
            "─" * 60,
            "COMPANY OVERVIEW",
            "─" * 60,
            f"Sector: {a.sector}",
            f"Industry: {a.industry}",
            f"Market Cap: ${a.market_cap}B",
            f"Enterprise Value: ${a.enterprise_value}B",
            "",
            "─" * 60,
            "VALUATION",
            "─" * 60,
        ]
        
        if a.pe_ratio:
            lines.append(f"P/E (TTM): {a.pe_ratio}x")
        if a.forward_pe:
            lines.append(f"P/E (Forward): {a.forward_pe}x")
        if a.ps_ratio:
            lines.append(f"P/S: {a.ps_ratio}x")
        if a.pb_ratio:
            lines.append(f"P/B: {a.pb_ratio}x")
        if a.ev_ebitda:
            lines.append(f"EV/EBITDA: {a.ev_ebitda}x")
        
        lines.extend([
            "",
            "─" * 60,
            "GROWTH",
            "─" * 60,
            f"Revenue Growth (YoY): {a.revenue_growth}%",
            f"Earnings Growth (YoY): {a.earnings_growth}%",
        ])
        
        if a.revenue_3yr_cagr:
            lines.append(f"Revenue 3Y CAGR: {a.revenue_3yr_cagr}%")
        
        if a.revenue_history:
            lines.append("")
            lines.append("Revenue History (billions):")
            for h in a.revenue_history[:4]:
                lines.append(f"  {h['year']}: ${h['revenue']:.2f}B")
        
        lines.extend([
            "",
            "─" * 60,
            "PROFITABILITY",
            "─" * 60,
            f"Gross Margin: {a.gross_margin}%",
            f"Operating Margin: {a.operating_margin}%",
            f"Net Margin: {a.net_margin}%",
            f"ROE: {a.roe}%",
            f"ROA: {a.roa}%",
            "",
            "─" * 60,
            "CASH FLOW",
            "─" * 60,
            f"Free Cash Flow: ${a.free_cash_flow}B",
            f"FCF Margin: {a.fcf_margin}%",
            f"Operating Cash Flow: ${a.operating_cash_flow}B",
            "",
            "─" * 60,
            "BALANCE SHEET",
            "─" * 60,
            f"Cash: ${a.total_cash}B",
            f"Debt: ${a.total_debt}B",
            f"Debt/Equity: {a.debt_to_equity}x",
            f"Current Ratio: {a.current_ratio}x",
            "",
            "─" * 60,
            "OWNERSHIP",
            "─" * 60,
            f"Insider Ownership: {a.insider_ownership}%",
            f"Institutional Ownership: {a.institutional_ownership}%",
            f"Short Interest: {a.short_percent}%",
            "",
            "─" * 60,
            "QUALITY ASSESSMENT",
            "─" * 60,
        ])
        
        if positives:
            lines.append("✅ Strengths:")
            for p in positives:
                lines.append(f"   • {p}")
        
        if negatives:
            lines.append("⚠️ Concerns:")
            for n in negatives:
                lines.append(f"   • {n}")
        
        lines.extend([
            "",
            "═" * 60,
        ])
        
        return "\n".join(lines)


def analyze_fundamentals(ticker: str) -> FundamentalAnalysis:
    """Run fundamental analysis on a ticker."""
    analyzer = FundamentalAnalyzer(ticker)
    analysis = analyzer.analyze()
    print(analyzer.format_report())
    return analysis


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "DOCN"
    analyze_fundamentals(ticker)

