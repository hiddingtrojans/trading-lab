#!/usr/bin/env python3
"""
Advanced Fundamental Metrics
=============================

Additional quality metrics:
- ROIC (Return on Invested Capital)
- Piotroski F-Score
- Magic Formula Rank
- Altman Z-Score (bankruptcy risk)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict


def calculate_roic(ticker_info: dict) -> float:
    """
    Calculate ROIC (Return on Invested Capital).
    
    ROIC = NOPAT / Invested Capital
    Where:
    - NOPAT = Net Operating Profit After Tax
    - Invested Capital = Total Assets - Current Liabilities
    
    Approximation using available data:
    ROIC ≈ (Net Income + Interest Expense * (1 - Tax Rate)) / (Total Assets - Current Liabilities)
    
    Or simpler:
    ROIC ≈ Operating Income / (Total Assets - Current Liabilities)
    """
    try:
        # Get financial data
        ebit = ticker_info.get('ebit', 0)  # Earnings before interest and tax
        total_assets = ticker_info.get('totalAssets', 0)
        current_liabilities = ticker_info.get('totalCurrentLiabilities', 0)
        
        if total_assets == 0 or current_liabilities == 0:
            return np.nan
        
        invested_capital = total_assets - current_liabilities
        
        if invested_capital <= 0:
            return np.nan
        
        roic = (ebit / invested_capital) * 100
        
        return roic
        
    except Exception:
        return np.nan


def calculate_piotroski_fscore(ticker_obj) -> Dict:
    """
    Calculate Piotroski F-Score (0-9).
    
    9 criteria:
    
    PROFITABILITY (4 points):
    1. Positive net income (1 pt)
    2. Positive operating cash flow (1 pt)
    3. Increasing ROA year-over-year (1 pt)
    4. Operating cash flow > Net income (quality of earnings) (1 pt)
    
    LEVERAGE/LIQUIDITY (3 points):
    5. Decreasing long-term debt (1 pt)
    6. Increasing current ratio (1 pt)
    7. No new shares issued (1 pt)
    
    OPERATING EFFICIENCY (2 points):
    8. Increasing gross margin (1 pt)
    9. Increasing asset turnover (1 pt)
    """
    try:
        info = ticker_obj.info
        financials = ticker_obj.financials
        balance_sheet = ticker_obj.balance_sheet
        cashflow = ticker_obj.cashflow
        
        score = 0
        breakdown = {}
        
        # 1. Positive net income
        net_income = info.get('netIncomeToCommon', 0)
        if net_income > 0:
            score += 1
            breakdown['positive_income'] = True
        else:
            breakdown['positive_income'] = False
        
        # 2. Positive operating cash flow
        if not cashflow.empty and 'Operating Cash Flow' in cashflow.index:
            ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
            if ocf > 0:
                score += 1
                breakdown['positive_cashflow'] = True
            else:
                breakdown['positive_cashflow'] = False
        
        # 3. Increasing ROA
        roa_current = info.get('returnOnAssets', 0)
        if roa_current > 0:  # Simplified - would need historical ROA
            score += 1
            breakdown['increasing_roa'] = True
        else:
            breakdown['increasing_roa'] = False
        
        # 4. OCF > Net Income (quality of earnings)
        if not cashflow.empty and 'Operating Cash Flow' in cashflow.index:
            ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
            if net_income > 0 and ocf > net_income:
                score += 1
                breakdown['quality_earnings'] = True
            else:
                breakdown['quality_earnings'] = False
        
        # 5. Decreasing debt
        debt_current = info.get('totalDebt', 0)
        if debt_current == 0:  # No debt is best
            score += 1
            breakdown['decreasing_debt'] = True
        else:
            breakdown['decreasing_debt'] = False
        
        # 6. Increasing current ratio
        current_ratio = info.get('currentRatio', 0)
        if current_ratio > 1.5:  # Simplified - would need historical
            score += 1
            breakdown['good_liquidity'] = True
        else:
            breakdown['good_liquidity'] = False
        
        # 7. No new shares (dilution check)
        shares_outstanding = info.get('sharesOutstanding', 0)
        if shares_outstanding > 0:  # Simplified - would need historical
            score += 1
            breakdown['no_dilution'] = True
        else:
            breakdown['no_dilution'] = False
        
        # 8. Increasing gross margin
        gross_margin = info.get('grossMargins', 0)
        if gross_margin > 0.3:  # Simplified - would need historical
            score += 1
            breakdown['good_margins'] = True
        else:
            breakdown['good_margins'] = False
        
        # 9. Increasing asset turnover
        revenue = info.get('totalRevenue', 0)
        assets = info.get('totalAssets', 1)
        asset_turnover = revenue / assets if assets > 0 else 0
        if asset_turnover > 0.5:  # Simplified
            score += 1
            breakdown['good_efficiency'] = True
        else:
            breakdown['good_efficiency'] = False
        
        return {
            'score': score,
            'max_score': 9,
            'breakdown': breakdown,
            'rating': 'Strong' if score >= 7 else 'Moderate' if score >= 4 else 'Weak'
        }
        
    except Exception as e:
        return {
            'score': 0,
            'max_score': 9,
            'breakdown': {},
            'rating': 'Unknown',
            'error': str(e)
        }


def calculate_magic_formula_rank(ticker_info: dict) -> Dict:
    """
    Joel Greenblatt's Magic Formula.
    
    Ranks stocks by:
    1. Earnings Yield = EBIT / Enterprise Value (higher is better)
    2. Return on Capital = EBIT / (Net Working Capital + Net Fixed Assets)
    
    Combined rank = Average of both ranks
    """
    try:
        ebit = ticker_info.get('ebit', 0)
        enterprise_value = ticker_info.get('enterpriseValue', 0)
        total_assets = ticker_info.get('totalAssets', 0)
        current_liabilities = ticker_info.get('totalCurrentLiabilities', 0)
        
        if enterprise_value == 0 or total_assets == 0:
            return {'score': 0, 'rating': 'Unknown'}
        
        # Earnings Yield
        earnings_yield = (ebit / enterprise_value) * 100 if enterprise_value > 0 else 0
        
        # Return on Capital (simplified)
        invested_capital = total_assets - current_liabilities
        return_on_capital = (ebit / invested_capital) * 100 if invested_capital > 0 else 0
        
        # Score (0-100)
        ey_score = min(earnings_yield * 10, 50)  # Cap at 50 points
        roc_score = min(return_on_capital * 2, 50)  # Cap at 50 points
        
        total_score = ey_score + roc_score
        
        return {
            'score': total_score,
            'earnings_yield': earnings_yield,
            'return_on_capital': return_on_capital,
            'rating': 'Excellent' if total_score >= 80 else 'Good' if total_score >= 60 else 'Fair'
        }
        
    except Exception:
        return {'score': 0, 'rating': 'Unknown'}


def calculate_altman_zscore(ticker_info: dict) -> Dict:
    """
    Altman Z-Score (bankruptcy prediction).
    
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    
    Where:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Sales / Total Assets
    
    Score:
    > 2.99 = Safe
    1.81 - 2.99 = Grey zone
    < 1.81 = Distress
    """
    try:
        total_assets = ticker_info.get('totalAssets', 0)
        current_assets = ticker_info.get('totalCurrentAssets', 0)
        current_liabilities = ticker_info.get('totalCurrentLiabilities', 0)
        retained_earnings = ticker_info.get('retainedEarnings', 0)
        ebit = ticker_info.get('ebit', 0)
        market_cap = ticker_info.get('marketCap', 0)
        total_liabilities = ticker_info.get('totalLiab', 0)
        revenue = ticker_info.get('totalRevenue', 0)
        
        if total_assets == 0:
            return {'score': 0, 'rating': 'Unknown'}
        
        # Calculate components
        x1 = (current_assets - current_liabilities) / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
        x5 = revenue / total_assets
        
        # Altman Z-Score
        z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
        
        # Rating
        if z_score > 2.99:
            rating = 'Safe'
        elif z_score > 1.81:
            rating = 'Grey Zone'
        else:
            rating = 'Distress'
        
        return {
            'score': z_score,
            'rating': rating,
            'bankruptcy_risk': 'Low' if z_score > 2.99 else 'Medium' if z_score > 1.81 else 'High'
        }
        
    except Exception:
        return {'score': 0, 'rating': 'Unknown'}


def get_all_advanced_metrics(ticker: str) -> Dict:
    """Get all advanced fundamental metrics for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Calculate metrics
        roic = calculate_roic(info)
        piotroski = calculate_piotroski_fscore(stock)
        magic_formula = calculate_magic_formula_rank(info)
        altman = calculate_altman_zscore(info)
        
        return {
            'ticker': ticker,
            'roic': {
                'value': roic,
                'rating': 'Excellent' if roic > 15 else 'Good' if roic > 10 else 'Fair' if roic > 5 else 'Poor'
            },
            'piotroski': piotroski,
            'magic_formula': magic_formula,
            'altman_zscore': altman,
            'combined_score': calculate_combined_quality_score(roic, piotroski, magic_formula, altman)
        }
        
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


def calculate_combined_quality_score(roic, piotroski, magic_formula, altman) -> Dict:
    """
    Combine all quality metrics into one score.
    
    Weights:
    - ROIC: 30%
    - Piotroski: 25%
    - Magic Formula: 25%
    - Altman Z: 20%
    """
    try:
        score = 0
        
        # ROIC contribution (0-30 points)
        if not np.isnan(roic):
            roic_points = min(roic * 2, 30)  # Cap at 30
            score += roic_points
        
        # Piotroski contribution (0-25 points)
        piotroski_points = (piotroski['score'] / 9) * 25
        score += piotroski_points
        
        # Magic Formula contribution (0-25 points)
        mf_points = (magic_formula['score'] / 100) * 25
        score += mf_points
        
        # Altman Z contribution (0-20 points)
        if altman['score'] > 2.99:
            altman_points = 20
        elif altman['score'] > 1.81:
            altman_points = 10
        else:
            altman_points = 0
        score += altman_points
        
        return {
            'score': score,
            'max': 100,
            'rating': 'Excellent' if score >= 80 else 'Strong' if score >= 65 else 'Moderate' if score >= 50 else 'Weak'
        }
        
    except:
        return {'score': 0, 'max': 100, 'rating': 'Unknown'}


def display_advanced_metrics(metrics: Dict):
    """Display formatted advanced metrics."""
    print(f"\n{'='*80}")
    print(f"ADVANCED FUNDAMENTAL METRICS: {metrics['ticker']}")
    print(f"{'='*80}\n")
    
    if 'error' in metrics:
        print(f"✗ Error: {metrics['error']}")
        return
    
    # ROIC
    roic = metrics.get('roic', {})
    print(f"ROIC (Return on Invested Capital):")
    if not np.isnan(roic.get('value', np.nan)):
        print(f"  Value: {roic['value']:.1f}%")
        print(f"  Rating: {roic['rating']}")
        print(f"  Interpretation: {'✓ Efficient capital allocation' if roic['value'] > 15 else '○ Moderate efficiency' if roic['value'] > 10 else '✗ Inefficient'}")
    else:
        print(f"  Not available")
    
    # Piotroski
    print(f"\nPiotroski F-Score (Quality):")
    piotroski = metrics.get('piotroski', {})
    print(f"  Score: {piotroski.get('score', 0)}/9")
    print(f"  Rating: {piotroski.get('rating', 'Unknown')}")
    if 'breakdown' in piotroski:
        breakdown = piotroski['breakdown']
        print(f"  Profitability: {'✓' if breakdown.get('positive_income') else '✗'} Income, "
              f"{'✓' if breakdown.get('positive_cashflow') else '✗'} Cash Flow, "
              f"{'✓' if breakdown.get('quality_earnings') else '✗'} Quality")
        print(f"  Financial Health: {'✓' if breakdown.get('decreasing_debt') else '✗'} Debt, "
              f"{'✓' if breakdown.get('good_liquidity') else '✗'} Liquidity")
        print(f"  Efficiency: {'✓' if breakdown.get('good_margins') else '✗'} Margins, "
              f"{'✓' if breakdown.get('good_efficiency') else '✗'} Turnover")
    
    # Magic Formula
    print(f"\nMagic Formula (Greenblatt):")
    mf = metrics.get('magic_formula', {})
    print(f"  Score: {mf.get('score', 0):.1f}/100")
    print(f"  Rating: {mf.get('rating', 'Unknown')}")
    if 'earnings_yield' in mf:
        print(f"  Earnings Yield: {mf['earnings_yield']:.2f}%")
        print(f"  Return on Capital: {mf['return_on_capital']:.2f}%")
    
    # Altman Z-Score
    print(f"\nAltman Z-Score (Bankruptcy Risk):")
    altman = metrics.get('altman_zscore', {})
    print(f"  Score: {altman.get('score', 0):.2f}")
    print(f"  Rating: {altman.get('rating', 'Unknown')}")
    print(f"  Bankruptcy Risk: {altman.get('bankruptcy_risk', 'Unknown')}")
    
    # Combined
    print(f"\n{'='*80}")
    print(f"COMBINED QUALITY SCORE:")
    combined = metrics.get('combined_score', {})
    print(f"  Score: {combined.get('score', 0):.1f}/100")
    print(f"  Rating: {combined.get('rating', 'Unknown')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    """Demo/test the metrics."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fundamental_metrics.py TICKER")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    print(f"Calculating advanced metrics for {ticker}...")
    metrics = get_all_advanced_metrics(ticker)
    display_advanced_metrics(metrics)

