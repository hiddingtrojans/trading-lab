"""
Stock Valuation Calculator

Calculate fair value using multiple methods and compare to current price.

Methods:
1. DCF (Discounted Cash Flow) - Based on free cash flow
2. Graham Number - Classic value investing formula
3. PE-Based - Compare to historical/industry PE
4. Analyst Targets - Wall Street consensus
5. PEG Ratio - Growth-adjusted valuation

Why this matters:
- Know if a stock is overvalued or undervalued
- Multiple methods = more confidence
- GPT can't calculate with real-time data
"""

import os
import sys
from typing import Optional, Dict, List
from dataclasses import dataclass
import yfinance as yf
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class ValuationResult:
    """Result from a single valuation method."""
    method: str
    fair_value: Optional[float]
    upside_pct: Optional[float]  # Positive = undervalued
    confidence: str  # High, Medium, Low
    notes: str


@dataclass
class ValuationSummary:
    """Complete valuation summary for a stock."""
    ticker: str
    company_name: str
    current_price: float
    
    # Individual valuations
    dcf_value: Optional[float]
    graham_value: Optional[float]
    pe_value: Optional[float]
    analyst_target: Optional[float]
    peg_value: Optional[float]
    
    # Consensus
    avg_fair_value: Optional[float]
    upside_pct: Optional[float]
    verdict: str  # "Undervalued", "Fairly Valued", "Overvalued"
    
    # Details
    results: List[ValuationResult]
    
    # Key metrics used
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    price_to_book: Optional[float]
    ev_to_ebitda: Optional[float]


class StockValuation:
    """
    Calculate fair value using multiple methods.
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self.results: List[ValuationResult] = []
    
    def analyze(self) -> ValuationSummary:
        """Run all valuation methods and return summary."""
        
        current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
        company_name = self.info.get('shortName', self.ticker)
        
        # Run each valuation method
        dcf = self._dcf_valuation()
        graham = self._graham_number()
        pe_based = self._pe_based_valuation()
        analyst = self._analyst_target()
        peg = self._peg_based_valuation()
        
        # Collect valid fair values
        fair_values = []
        if dcf: fair_values.append(dcf)
        if graham: fair_values.append(graham)
        if pe_based: fair_values.append(pe_based)
        if analyst: fair_values.append(analyst)
        if peg: fair_values.append(peg)
        
        # Calculate average fair value
        avg_fair_value = None
        upside_pct = None
        verdict = "Unable to Determine"
        
        if fair_values and current_price > 0:
            avg_fair_value = sum(fair_values) / len(fair_values)
            upside_pct = ((avg_fair_value / current_price) - 1) * 100
            
            if upside_pct >= 20:
                verdict = "🟢 UNDERVALUED"
            elif upside_pct >= 5:
                verdict = "🟢 Slightly Undervalued"
            elif upside_pct <= -20:
                verdict = "🔴 OVERVALUED"
            elif upside_pct <= -5:
                verdict = "🔴 Slightly Overvalued"
            else:
                verdict = "🟡 Fairly Valued"
        
        return ValuationSummary(
            ticker=self.ticker,
            company_name=company_name,
            current_price=current_price,
            dcf_value=dcf,
            graham_value=graham,
            pe_value=pe_based,
            analyst_target=analyst,
            peg_value=peg,
            avg_fair_value=avg_fair_value,
            upside_pct=upside_pct,
            verdict=verdict,
            results=self.results,
            pe_ratio=self.info.get('trailingPE'),
            forward_pe=self.info.get('forwardPE'),
            peg_ratio=self.info.get('pegRatio'),
            price_to_book=self.info.get('priceToBook'),
            ev_to_ebitda=self.info.get('enterpriseToEbitda'),
        )
    
    def _dcf_valuation(self) -> Optional[float]:
        """
        Discounted Cash Flow valuation.
        
        Fair Value = Sum of discounted future cash flows + terminal value
        """
        try:
            # Get free cash flow
            fcf = self.info.get('freeCashflow', 0)
            if not fcf or fcf <= 0:
                self.results.append(ValuationResult(
                    method="DCF",
                    fair_value=None,
                    upside_pct=None,
                    confidence="N/A",
                    notes="No positive free cash flow"
                ))
                return None
            
            # Get shares outstanding
            shares = self.info.get('sharesOutstanding', 0)
            if not shares:
                return None
            
            # Assumptions
            growth_rate = min(self.info.get('revenueGrowth', 0.1) or 0.1, 0.25)  # Cap at 25%
            discount_rate = 0.10  # 10% required return
            terminal_growth = 0.03  # 3% perpetual growth
            years = 5
            
            # Project future cash flows
            total_pv = 0
            for year in range(1, years + 1):
                future_fcf = fcf * ((1 + growth_rate) ** year)
                pv = future_fcf / ((1 + discount_rate) ** year)
                total_pv += pv
            
            # Terminal value
            terminal_fcf = fcf * ((1 + growth_rate) ** years) * (1 + terminal_growth)
            terminal_value = terminal_fcf / (discount_rate - terminal_growth)
            terminal_pv = terminal_value / ((1 + discount_rate) ** years)
            
            total_pv += terminal_pv
            
            fair_value = total_pv / shares
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            upside = ((fair_value / current_price) - 1) * 100 if current_price > 0 else None
            
            self.results.append(ValuationResult(
                method="DCF",
                fair_value=fair_value,
                upside_pct=upside,
                confidence="Medium",
                notes=f"Based on {growth_rate*100:.0f}% growth, 10% discount rate"
            ))
            
            return fair_value
            
        except Exception as e:
            return None
    
    def _graham_number(self) -> Optional[float]:
        """
        Benjamin Graham's intrinsic value formula.
        
        Graham Number = √(22.5 × EPS × Book Value per Share)
        """
        try:
            eps = self.info.get('trailingEps', 0)
            book_value = self.info.get('bookValue', 0)
            
            if not eps or eps <= 0 or not book_value or book_value <= 0:
                self.results.append(ValuationResult(
                    method="Graham Number",
                    fair_value=None,
                    upside_pct=None,
                    confidence="N/A",
                    notes="Needs positive EPS and book value"
                ))
                return None
            
            # Graham's formula: √(22.5 × EPS × BVPS)
            graham_value = math.sqrt(22.5 * eps * book_value)
            
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            upside = ((graham_value / current_price) - 1) * 100 if current_price > 0 else None
            
            self.results.append(ValuationResult(
                method="Graham Number",
                fair_value=graham_value,
                upside_pct=upside,
                confidence="Medium",
                notes=f"EPS: ${eps:.2f}, Book: ${book_value:.2f}"
            ))
            
            return graham_value
            
        except Exception as e:
            return None
    
    def _pe_based_valuation(self) -> Optional[float]:
        """
        PE-based fair value.
        
        Compare current PE to historical average or apply reasonable PE to earnings.
        """
        try:
            eps = self.info.get('trailingEps', 0)
            forward_eps = self.info.get('forwardEps', 0)
            current_pe = self.info.get('trailingPE', 0)
            
            if not eps or eps <= 0:
                self.results.append(ValuationResult(
                    method="PE-Based",
                    fair_value=None,
                    upside_pct=None,
                    confidence="N/A",
                    notes="No positive earnings"
                ))
                return None
            
            # Use sector-appropriate PE
            sector = self.info.get('sector', '')
            
            # Reasonable PE by sector
            sector_pe = {
                'Technology': 25,
                'Healthcare': 20,
                'Financial Services': 12,
                'Consumer Cyclical': 18,
                'Consumer Defensive': 20,
                'Energy': 12,
                'Utilities': 15,
                'Real Estate': 18,
                'Industrials': 18,
                'Basic Materials': 15,
                'Communication Services': 20,
            }
            
            target_pe = sector_pe.get(sector, 18)
            
            # Use forward EPS if available, otherwise trailing
            use_eps = forward_eps if forward_eps and forward_eps > 0 else eps
            fair_value = use_eps * target_pe
            
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            upside = ((fair_value / current_price) - 1) * 100 if current_price > 0 else None
            
            eps_type = "forward" if forward_eps and forward_eps > 0 else "trailing"
            
            self.results.append(ValuationResult(
                method="PE-Based",
                fair_value=fair_value,
                upside_pct=upside,
                confidence="Medium",
                notes=f"Target PE: {target_pe}x ({sector}), using {eps_type} EPS"
            ))
            
            return fair_value
            
        except Exception as e:
            return None
    
    def _analyst_target(self) -> Optional[float]:
        """
        Wall Street analyst consensus price target.
        """
        try:
            target = self.info.get('targetMeanPrice', 0)
            target_low = self.info.get('targetLowPrice', 0)
            target_high = self.info.get('targetHighPrice', 0)
            num_analysts = self.info.get('numberOfAnalystOpinions', 0)
            
            if not target or target <= 0:
                self.results.append(ValuationResult(
                    method="Analyst Target",
                    fair_value=None,
                    upside_pct=None,
                    confidence="N/A",
                    notes="No analyst coverage"
                ))
                return None
            
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            upside = ((target / current_price) - 1) * 100 if current_price > 0 else None
            
            confidence = "High" if num_analysts >= 10 else "Medium" if num_analysts >= 5 else "Low"
            
            self.results.append(ValuationResult(
                method="Analyst Target",
                fair_value=target,
                upside_pct=upside,
                confidence=confidence,
                notes=f"{num_analysts} analysts (${target_low:.0f}-${target_high:.0f})"
            ))
            
            return target
            
        except Exception as e:
            return None
    
    def _peg_based_valuation(self) -> Optional[float]:
        """
        PEG ratio based valuation.
        
        Fair PE = Growth Rate (Peter Lynch's rule: PEG of 1 is fair)
        """
        try:
            eps = self.info.get('trailingEps', 0)
            growth_rate = self.info.get('earningsGrowth', 0) or self.info.get('revenueGrowth', 0)
            
            if not eps or eps <= 0 or not growth_rate or growth_rate <= 0:
                self.results.append(ValuationResult(
                    method="PEG-Based",
                    fair_value=None,
                    upside_pct=None,
                    confidence="N/A",
                    notes="Needs positive EPS and growth"
                ))
                return None
            
            # Convert growth to percentage if needed
            if growth_rate < 1:
                growth_pct = growth_rate * 100
            else:
                growth_pct = growth_rate
            
            # Peter Lynch: Fair PE = Growth Rate
            # A 20% grower deserves 20x PE
            fair_pe = min(growth_pct, 30)  # Cap at 30x
            fair_value = eps * fair_pe
            
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            upside = ((fair_value / current_price) - 1) * 100 if current_price > 0 else None
            
            self.results.append(ValuationResult(
                method="PEG-Based",
                fair_value=fair_value,
                upside_pct=upside,
                confidence="Medium",
                notes=f"Growth: {growth_pct:.0f}% → Fair PE: {fair_pe:.0f}x"
            ))
            
            return fair_value
            
        except Exception as e:
            return None
    
    def format_report(self, summary: ValuationSummary) -> str:
        """Format valuation report for display."""
        lines = [
            "═" * 60,
            f"💰 VALUATION ANALYSIS: {summary.ticker}",
            f"   {summary.company_name}",
            "═" * 60,
            "",
        ]
        
        # Current price and verdict
        lines.append(f"📍 Current Price:  ${summary.current_price:.2f}")
        
        if summary.avg_fair_value:
            lines.append(f"🎯 Avg Fair Value: ${summary.avg_fair_value:.2f}")
            
            if summary.upside_pct:
                upside_str = f"{summary.upside_pct:+.1f}%"
                if summary.upside_pct > 0:
                    lines.append(f"📈 Upside:         {upside_str}")
                else:
                    lines.append(f"📉 Downside:       {upside_str}")
            
            lines.append("")
            lines.append(f"Verdict: {summary.verdict}")
        
        lines.append("")
        lines.append("─" * 60)
        lines.append("VALUATION METHODS")
        lines.append("─" * 60)
        
        # Method results table
        for result in summary.results:
            if result.fair_value:
                upside_str = f"({result.upside_pct:+.0f}%)" if result.upside_pct else ""
                lines.append(f"  {result.method:15} ${result.fair_value:>8.2f} {upside_str:>8}")
                lines.append(f"     └─ {result.notes}")
            else:
                lines.append(f"  {result.method:15} {'N/A':>8}    {result.notes}")
            lines.append("")
        
        # Key metrics
        lines.append("─" * 60)
        lines.append("KEY METRICS")
        lines.append("─" * 60)
        
        if summary.pe_ratio:
            lines.append(f"  Trailing P/E:   {summary.pe_ratio:.1f}x")
        if summary.forward_pe:
            lines.append(f"  Forward P/E:    {summary.forward_pe:.1f}x")
        if summary.peg_ratio:
            lines.append(f"  PEG Ratio:      {summary.peg_ratio:.2f}")
        if summary.price_to_book:
            lines.append(f"  Price/Book:     {summary.price_to_book:.2f}x")
        if summary.ev_to_ebitda:
            lines.append(f"  EV/EBITDA:      {summary.ev_to_ebitda:.1f}x")
        
        lines.append("")
        lines.append("═" * 60)
        lines.append("⚠️  Fair value estimates are not guarantees")
        lines.append("   Always do your own due diligence")
        lines.append("═" * 60)
        
        return "\n".join(lines)


def analyze_valuation(ticker: str):
    """Analyze and display valuation for a ticker."""
    valuation = StockValuation(ticker)
    summary = valuation.analyze()
    print(valuation.format_report(summary))
    return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        analyze_valuation(ticker)
    else:
        print("Usage: python valuation.py TICKER")
        print("\nExample: python valuation.py AAPL")
        print("\nCalculates fair value using:")
        print("  - DCF (Discounted Cash Flow)")
        print("  - Graham Number")
        print("  - PE-Based valuation")
        print("  - Analyst price targets")
        print("  - PEG-Based valuation")

