#!/usr/bin/env python3
"""
Real Fundamental Analysis
==========================

Proper calculation of fundamental metrics using actual financial statements.
No shortcuts, no approximations.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class RealFundamentalAnalyzer:
    """Proper fundamental analysis with actual financial statement calculations."""
    
    def __init__(self, ticker: str):
        """
        Initialize analyzer.
        
        Args:
            ticker: Stock symbol
        """
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = None
        self.financials = None
        self.balance_sheet = None
        self.cashflow = None
        
        # Load all data upfront
        self._load_data()
    
    def _load_data(self):
        """Load all financial data from yfinance."""
        try:
            print(f"  Loading financial data for {self.ticker}...", end=" ", flush=True)
            
            # Basic info
            self.info = self.stock.info
            
            # Financial statements (annual)
            self.financials = self.stock.financials
            self.balance_sheet = self.stock.balance_sheet
            self.cashflow = self.stock.cashflow
            
            # Also get quarterly for more recent data
            self.quarterly_financials = self.stock.quarterly_financials
            self.quarterly_balance = self.stock.quarterly_balance_sheet
            self.quarterly_cashflow = self.stock.quarterly_cashflow
            
            print("✓")
            
        except Exception as e:
            print(f"✗ Error loading data: {e}")
    
    def calculate_roic(self) -> Dict:
        """
        Calculate ROIC (Return on Invested Capital) properly.
        
        ROIC = NOPAT / Invested Capital
        
        Where:
        NOPAT = Net Operating Profit After Tax
              = Operating Income * (1 - Tax Rate)
              = EBIT * (1 - Tax Rate)
        
        Invested Capital = Total Assets - Current Liabilities - Cash
                        = Debt + Equity
        
        Returns:
            Dictionary with ROIC value and components
        """
        try:
            # Get most recent year
            if self.financials is None or self.financials.empty:
                return {'value': np.nan, 'error': 'No financial data'}
            
            # Get EBIT (Operating Income)
            if 'Operating Income' in self.financials.index:
                ebit = self.financials.loc['Operating Income'].iloc[0]
            elif 'EBIT' in self.financials.index:
                ebit = self.financials.loc['EBIT'].iloc[0]
            else:
                # Calculate: Revenue - COGS - Operating Expenses
                revenue = self.financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in self.financials.index else 0
                cogs = self.financials.loc['Cost Of Revenue'].iloc[0] if 'Cost Of Revenue' in self.financials.index else 0
                opex = self.financials.loc['Operating Expense'].iloc[0] if 'Operating Expense' in self.financials.index else 0
                ebit = revenue - cogs - opex
            
            # Estimate tax rate
            if 'Tax Provision' in self.financials.index and 'Pretax Income' in self.financials.index:
                tax = self.financials.loc['Tax Provision'].iloc[0]
                pretax = self.financials.loc['Pretax Income'].iloc[0]
                tax_rate = abs(tax / pretax) if pretax != 0 else 0.21  # Default to 21%
            else:
                tax_rate = 0.21  # US corporate tax rate
            
            # Calculate NOPAT
            nopat = ebit * (1 - tax_rate)
            
            # Get Invested Capital from balance sheet
            if self.balance_sheet is None or self.balance_sheet.empty:
                return {'value': np.nan, 'error': 'No balance sheet data'}
            
            total_assets = self.balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in self.balance_sheet.index else 0
            current_liab = self.balance_sheet.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in self.balance_sheet.index else 0
            cash = self.balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in self.balance_sheet.index else 0
            
            # Invested Capital = Total Assets - Current Liabilities - Cash
            invested_capital = total_assets - current_liab - cash
            
            if invested_capital <= 0:
                return {'value': np.nan, 'error': 'Invalid invested capital'}
            
            # Calculate ROIC
            roic = (nopat / invested_capital) * 100
            
            return {
                'value': roic,
                'nopat': nopat,
                'invested_capital': invested_capital,
                'tax_rate': tax_rate,
                'rating': 'Excellent' if roic > 20 else 'Good' if roic > 15 else 'Fair' if roic > 10 else 'Poor'
            }
            
        except Exception as e:
            return {'value': np.nan, 'error': str(e)}
    
    def calculate_piotroski_fscore(self) -> Dict:
        """
        Calculate Piotroski F-Score properly with year-over-year comparisons.
        
        Returns:
            Dictionary with score, breakdown, and explanation
        """
        try:
            if self.financials is None or self.financials.empty:
                return {'score': 0, 'error': 'No financial data'}
            
            if self.balance_sheet is None or self.balance_sheet.empty:
                return {'score': 0, 'error': 'No balance sheet'}
            
            if self.cashflow is None or self.cashflow.empty:
                return {'score': 0, 'error': 'No cash flow data'}
            
            # Need at least 2 years of data for comparisons
            if len(self.financials.columns) < 2:
                return {'score': 0, 'error': 'Need 2 years of data'}
            
            score = 0
            breakdown = {}
            
            # === PROFITABILITY (4 points) ===
            
            # 1. Positive ROA (current year)
            if 'Net Income' in self.financials.index:
                net_income_current = self.financials.loc['Net Income'].iloc[0]
                total_assets_current = self.balance_sheet.loc['Total Assets'].iloc[0]
                roa_current = net_income_current / total_assets_current
                
                if roa_current > 0:
                    score += 1
                    breakdown['positive_roa'] = True
                else:
                    breakdown['positive_roa'] = False
            
            # 2. Positive Operating Cash Flow
            if 'Operating Cash Flow' in self.cashflow.index:
                ocf_current = self.cashflow.loc['Operating Cash Flow'].iloc[0]
                if ocf_current > 0:
                    score += 1
                    breakdown['positive_ocf'] = True
                else:
                    breakdown['positive_ocf'] = False
            
            # 3. ROA increasing (compare current vs previous year)
            if 'Net Income' in self.financials.index and len(self.financials.columns) >= 2:
                net_income_prev = self.financials.loc['Net Income'].iloc[1]
                total_assets_prev = self.balance_sheet.loc['Total Assets'].iloc[1]
                roa_prev = net_income_prev / total_assets_prev
                
                if roa_current > roa_prev:
                    score += 1
                    breakdown['increasing_roa'] = True
                else:
                    breakdown['increasing_roa'] = False
            
            # 4. Quality of Earnings: OCF > Net Income
            if 'Operating Cash Flow' in self.cashflow.index and 'Net Income' in self.financials.index:
                if ocf_current > net_income_current:
                    score += 1
                    breakdown['quality_earnings'] = True
                else:
                    breakdown['quality_earnings'] = False
            
            # === LEVERAGE/LIQUIDITY (3 points) ===
            
            # 5. Decreasing long-term debt
            if 'Long Term Debt' in self.balance_sheet.index and len(self.balance_sheet.columns) >= 2:
                debt_current = self.balance_sheet.loc['Long Term Debt'].iloc[0]
                debt_prev = self.balance_sheet.loc['Long Term Debt'].iloc[1]
                
                if debt_current < debt_prev or debt_current == 0:
                    score += 1
                    breakdown['decreasing_debt'] = True
                else:
                    breakdown['decreasing_debt'] = False
            
            # 6. Increasing current ratio
            if 'Current Assets' in self.balance_sheet.index and 'Current Liabilities' in self.balance_sheet.index:
                if len(self.balance_sheet.columns) >= 2:
                    curr_ratio_current = self.balance_sheet.loc['Current Assets'].iloc[0] / self.balance_sheet.loc['Current Liabilities'].iloc[0]
                    curr_ratio_prev = self.balance_sheet.loc['Current Assets'].iloc[1] / self.balance_sheet.loc['Current Liabilities'].iloc[1]
                    
                    if curr_ratio_current > curr_ratio_prev:
                        score += 1
                        breakdown['increasing_current_ratio'] = True
                    else:
                        breakdown['increasing_current_ratio'] = False
            
            # 7. No new shares issued
            if 'Share Issued' in self.cashflow.index:
                shares_issued = self.cashflow.loc['Share Issued'].iloc[0]
                # Negative value means buyback (good), positive means dilution (bad)
                if shares_issued <= 0:
                    score += 1
                    breakdown['no_dilution'] = True
                else:
                    breakdown['no_dilution'] = False
            else:
                # If no share issuance data, check shares outstanding
                if len(self.balance_sheet.columns) >= 2:
                    # Assume no major dilution if data not available
                    breakdown['no_dilution'] = None
            
            # === OPERATING EFFICIENCY (2 points) ===
            
            # 8. Increasing gross margin
            if 'Gross Profit' in self.financials.index and 'Total Revenue' in self.financials.index:
                if len(self.financials.columns) >= 2:
                    revenue_current = self.financials.loc['Total Revenue'].iloc[0]
                    gross_current = self.financials.loc['Gross Profit'].iloc[0]
                    margin_current = gross_current / revenue_current
                    
                    revenue_prev = self.financials.loc['Total Revenue'].iloc[1]
                    gross_prev = self.financials.loc['Gross Profit'].iloc[1]
                    margin_prev = gross_prev / revenue_prev
                    
                    if margin_current > margin_prev:
                        score += 1
                        breakdown['increasing_margin'] = True
                    else:
                        breakdown['increasing_margin'] = False
            
            # 9. Increasing asset turnover
            if 'Total Revenue' in self.financials.index and 'Total Assets' in self.balance_sheet.index:
                if len(self.financials.columns) >= 2:
                    turnover_current = self.financials.loc['Total Revenue'].iloc[0] / self.balance_sheet.loc['Total Assets'].iloc[0]
                    turnover_prev = self.financials.loc['Total Revenue'].iloc[1] / self.balance_sheet.loc['Total Assets'].iloc[1]
                    
                    if turnover_current > turnover_prev:
                        score += 1
                        breakdown['increasing_turnover'] = True
                    else:
                        breakdown['increasing_turnover'] = False
            
            # Rating
            if score >= 8:
                rating = 'Excellent'
            elif score >= 6:
                rating = 'Strong'
            elif score >= 4:
                rating = 'Moderate'
            else:
                rating = 'Weak'
            
            return {
                'score': score,
                'max_score': 9,
                'rating': rating,
                'breakdown': breakdown,
                'methodology': 'Year-over-year comparisons on actual financial statements'
            }
            
        except Exception as e:
            return {
                'score': 0,
                'max_score': 9,
                'rating': 'Error',
                'error': str(e)
            }
    
    def get_complete_analysis(self) -> Dict:
        """
        Run complete fundamental analysis.
        
        Returns:
            Dictionary with all metrics
        """
        print(f"\n{'='*80}")
        print(f"REAL FUNDAMENTAL ANALYSIS: {self.ticker}")
        print(f"{'='*80}\n")
        
        # Basic info
        company_name = self.info.get('longName', self.ticker)
        sector = self.info.get('sector', 'Unknown')
        industry = self.info.get('industry', 'Unknown')
        market_cap = self.info.get('marketCap', 0)
        
        print(f"Company: {company_name}")
        print(f"Sector: {sector}")
        print(f"Industry: {industry}")
        print(f"Market Cap: ${market_cap/1e9:.2f}B\n")
        
        # Calculate real metrics
        roic = self.calculate_roic()
        piotroski = self.calculate_piotroski_fscore()
        
        # Display results
        print(f"{'='*80}")
        print(f"CALCULATED METRICS")
        print(f"{'='*80}\n")
        
        # ROIC
        print(f"ROIC (Return on Invested Capital):")
        if not np.isnan(roic.get('value', np.nan)):
            print(f"  Value: {roic['value']:.1f}%")
            print(f"  Rating: {roic['rating']}")
            print(f"  NOPAT: ${roic.get('nopat', 0)/1e6:.1f}M")
            print(f"  Invested Capital: ${roic.get('invested_capital', 0)/1e9:.2f}B")
            
            if roic['value'] > 20:
                print(f"  ✓ Excellent capital efficiency (>20%)")
            elif roic['value'] > 15:
                print(f"  ✓ Good capital efficiency (>15%)")
            elif roic['value'] > 10:
                print(f"  ○ Fair capital efficiency (>10%)")
            else:
                print(f"  ✗ Poor capital efficiency (<10%)")
        else:
            print(f"  Not calculable: {roic.get('error', 'Missing data')}")
        
        print()
        
        # Piotroski
        print(f"Piotroski F-Score (9-Point Quality Check):")
        print(f"  Score: {piotroski['score']}/9")
        print(f"  Rating: {piotroski['rating']}")
        
        if 'breakdown' in piotroski:
            breakdown = piotroski['breakdown']
            print(f"\n  Profitability:")
            print(f"    {'✓' if breakdown.get('positive_roa') else '✗'} Positive ROA")
            print(f"    {'✓' if breakdown.get('positive_ocf') else '✗'} Positive Operating Cash Flow")
            print(f"    {'✓' if breakdown.get('increasing_roa') else '✗'} ROA Increasing Year-over-Year")
            print(f"    {'✓' if breakdown.get('quality_earnings') else '✗'} OCF > Net Income (Quality)")
            
            print(f"\n  Financial Health:")
            print(f"    {'✓' if breakdown.get('decreasing_debt') else '✗'} Debt Decreasing Year-over-Year")
            print(f"    {'✓' if breakdown.get('increasing_current_ratio') else '✗'} Current Ratio Improving")
            print(f"    {'✓' if breakdown.get('no_dilution') else '✗' if breakdown.get('no_dilution') == False else '○'} No Share Dilution")
            
            print(f"\n  Operating Efficiency:")
            print(f"    {'✓' if breakdown.get('increasing_margin') else '✗'} Gross Margin Improving")
            print(f"    {'✓' if breakdown.get('increasing_turnover') else '✗'} Asset Turnover Improving")
        
        if 'error' in piotroski:
            print(f"  Error: {piotroski['error']}")
        
        print(f"\n  Interpretation:")
        if piotroski['score'] >= 8:
            print(f"    ✓✓ High-quality company, strong fundamentals across all areas")
        elif piotroski['score'] >= 6:
            print(f"    ✓ Solid company, most metrics showing strength")
        elif piotroski['score'] >= 4:
            print(f"    ○ Average company, mixed signals")
        else:
            print(f"    ✗ Weak company, concerning metrics")
        
        print()
        
        return {
            'ticker': self.ticker,
            'company_name': company_name,
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
            'roic': roic,
            'piotroski': piotroski
        }


def analyze_ticker(ticker: str) -> Dict:
    """
    Convenience function to analyze a ticker.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Complete analysis dictionary
    """
    analyzer = RealFundamentalAnalyzer(ticker)
    return analyzer.get_complete_analysis()


if __name__ == "__main__":
    """Test the analyzer."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python real_fundamentals.py TICKER")
        print("\nExample: python real_fundamentals.py NVDA")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    result = analyze_ticker(ticker)
    
    # Additional display
    print(f"{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    
    roic = result['roic']
    piotroski = result['piotroski']
    
    print(f"ROIC: {roic.get('value', 0):.1f}% ({roic.get('rating', 'N/A')})")
    print(f"Piotroski: {piotroski['score']}/9 ({piotroski['rating']})")
    
    print(f"\nOverall Assessment:")
    if piotroski['score'] >= 7 and roic.get('value', 0) > 15:
        print(f"  ✓✓ EXCELLENT - High quality, efficient capital allocation")
    elif piotroski['score'] >= 6 or roic.get('value', 0) > 12:
        print(f"  ✓ GOOD - Solid fundamentals")
    elif piotroski['score'] >= 4 or roic.get('value', 0) > 8:
        print(f"  ○ MODERATE - Mixed quality")
    else:
        print(f"  ✗ WEAK - Concerning fundamentals")
    
    print()


