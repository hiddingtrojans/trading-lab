#!/usr/bin/env python3
"""
Enhanced Stock Screener
=======================

Advanced screening with custom criteria:
- Growth stocks approaching profitability
- Profitable growth companies
- Custom fundamental filters
- Technical + fundamental combinations

Usage:
    python enhanced_screener.py --filter "growth>20 AND not_profitable AND improving"
    python enhanced_screener.py --filter "profitable AND growth>15 AND margin>30"
    python enhanced_screener.py --preset growth_to_profit
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
from typing import List, Dict, Callable
import warnings
warnings.filterwarnings('ignore')


class EnhancedScreener:
    """Advanced stock screener with custom criteria support."""
    
    def __init__(self):
        self.results = []
        
    def get_universe(self, universe_name: str = 'liquid') -> List[str]:
        """Get list of tickers to screen."""
        if universe_name == 'liquid':
            return [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 
                'NFLX', 'COIN', 'PLTR', 'SNOW', 'CRWD', 'ZS', 'DDOG', 'NET',
                'GME', 'AMC', 'SOFI', 'HOOD', 'RIVN', 'LCID', 'XOM', 'CVX',
                'SLB', 'HAL', 'OXY', 'MPC', 'MRNA', 'BNTX', 'NVAX', 'REGN',
                'ADBE', 'CRM', 'ORCL', 'NOW', 'SHOP', 'SQ', 'RBLX', 'ABNB',
                'UBER', 'LYFT', 'DASH', 'SPOT', 'ROKU', 'PYPL', 'V', 'MA'
            ]
        elif universe_name == 'russell1000':
            russell_path = 'data/russell1000_tickers.csv'
            if os.path.exists(russell_path):
                return pd.read_csv(russell_path)['ticker'].tolist()
        elif universe_name == 'russell2000':
            russell_path = 'data/russell2000_tickers.csv'
            if os.path.exists(russell_path):
                return pd.read_csv(russell_path)['ticker'].tolist()
        
        return self.get_universe('liquid')  # Default
    
    def analyze_fundamentals(self, ticker: str) -> Dict:
        """Get comprehensive fundamental data for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get financial data
            financials = stock.financials
            quarterly_financials = stock.quarterly_financials
            
            # Calculate metrics
            current_price = info.get('currentPrice', 0)
            
            # Revenue metrics
            if not financials.empty and 'Total Revenue' in financials.index:
                revenues = financials.loc['Total Revenue']
                current_revenue = revenues.iloc[0] if len(revenues) > 0 else 0
                prev_revenue = revenues.iloc[1] if len(revenues) > 1 else 0
                revenue_growth = (current_revenue - prev_revenue) / prev_revenue if prev_revenue > 0 else 0
            else:
                revenue_growth = info.get('revenueGrowth', 0)
            
            # Earnings metrics
            if not financials.empty and 'Net Income' in financials.index:
                net_income = financials.loc['Net Income']
                current_earnings = net_income.iloc[0] if len(net_income) > 0 else 0
                prev_earnings = net_income.iloc[1] if len(net_income) > 1 else 0
                
                # Check if approaching profitability
                is_profitable = current_earnings > 0
                was_profitable = prev_earnings > 0
                approaching_profitability = (not was_profitable and is_profitable) or \
                                          (not is_profitable and current_earnings > prev_earnings and current_earnings > -100000000)
                
                earnings_growth = (current_earnings - prev_earnings) / abs(prev_earnings) if prev_earnings != 0 else 0
            else:
                is_profitable = info.get('trailingEps', 0) > 0
                approaching_profitability = False
                earnings_growth = info.get('earningsGrowth', 0)
            
            # Margin metrics
            gross_margin = info.get('grossMargins', 0)
            operating_margin = info.get('operatingMargins', 0)
            profit_margin = info.get('profitMargins', 0)
            
            # Quarterly trend - check if margins improving
            improving_margins = False
            if not quarterly_financials.empty:
                if 'Gross Profit' in quarterly_financials.index and 'Total Revenue' in quarterly_financials.index:
                    quarterly_margins = quarterly_financials.loc['Gross Profit'] / quarterly_financials.loc['Total Revenue']
                    if len(quarterly_margins) >= 4:
                        recent_margin = quarterly_margins.iloc[:2].mean()
                        older_margin = quarterly_margins.iloc[2:4].mean()
                        improving_margins = recent_margin > older_margin
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'current_price': current_price,
                'revenue_growth': revenue_growth,
                'earnings_growth': earnings_growth,
                'is_profitable': is_profitable,
                'approaching_profitability': approaching_profitability,
                'gross_margin': gross_margin,
                'operating_margin': operating_margin,
                'profit_margin': profit_margin,
                'improving_margins': improving_margins,
                'pe_ratio': info.get('forwardPE', info.get('trailingPE', 0)),
                'peg_ratio': info.get('pegRatio', 0),
                'price_to_sales': info.get('priceToSalesTrailing12Months', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'analyst_target': info.get('targetMeanPrice', 0),
                'analyst_upside': ((info.get('targetMeanPrice', 0) - current_price) / current_price * 100) if current_price > 0 else 0
            }
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {str(e)}")
            return {'ticker': ticker, 'error': str(e)}
    
    def screen_growth_to_profitability(self, min_growth: float = 0.2) -> pd.DataFrame:
        """Screen for growth stocks approaching profitability."""
        print(f"\nScreening for growth stocks (>{min_growth*100}% growth) approaching profitability...")
        
        universe = self.get_universe('russell1000')
        results = []
        
        for i, ticker in enumerate(universe[:100]):  # Limit for speed
            if i % 10 == 0:
                print(f"  Progress: {i}/{min(100, len(universe))} tickers...")
            
            data = self.analyze_fundamentals(ticker)
            
            if 'error' not in data:
                # Filter criteria
                if (data['revenue_growth'] > min_growth and 
                    not data['is_profitable'] and
                    (data['approaching_profitability'] or data['improving_margins'])):
                    
                    results.append({
                        'ticker': ticker,
                        'company': data['company_name'],
                        'revenue_growth': f"{data['revenue_growth']*100:.1f}%",
                        'earnings_trend': 'Improving' if data['approaching_profitability'] else 'Negative',
                        'gross_margin': f"{data['gross_margin']*100:.1f}%",
                        'margin_trend': 'Improving' if data['improving_margins'] else 'Stable',
                        'market_cap_B': f"${data['market_cap']/1e9:.1f}B",
                        'analyst_upside': f"{data['analyst_upside']:.1f}%"
                    })
        
        return pd.DataFrame(results)
    
    def screen_profitable_growth(self, min_growth: float = 0.15, min_margin: float = 0.2) -> pd.DataFrame:
        """Screen for profitable companies with strong growth."""
        print(f"\nScreening for profitable growth stocks (>{min_growth*100}% growth, >{min_margin*100}% margin)...")
        
        universe = self.get_universe('russell1000')
        results = []
        
        for i, ticker in enumerate(universe[:100]):  # Limit for speed
            if i % 10 == 0:
                print(f"  Progress: {i}/{min(100, len(universe))} tickers...")
            
            data = self.analyze_fundamentals(ticker)
            
            if 'error' not in data:
                # Filter criteria
                if (data['revenue_growth'] > min_growth and 
                    data['is_profitable'] and
                    data['gross_margin'] > min_margin):
                    
                    results.append({
                        'ticker': ticker,
                        'company': data['company_name'],
                        'revenue_growth': f"{data['revenue_growth']*100:.1f}%",
                        'earnings_growth': f"{data['earnings_growth']*100:.1f}%",
                        'gross_margin': f"{data['gross_margin']*100:.1f}%",
                        'pe_ratio': f"{data['pe_ratio']:.1f}" if data['pe_ratio'] > 0 else 'N/A',
                        'market_cap_B': f"${data['market_cap']/1e9:.1f}B",
                        'analyst_upside': f"{data['analyst_upside']:.1f}%"
                    })
        
        return pd.DataFrame(results).sort_values('revenue_growth', ascending=False)
    
    def screen_custom(self, filter_func: Callable[[Dict], bool], universe: str = 'liquid') -> pd.DataFrame:
        """Screen with custom filter function."""
        print(f"\nRunning custom screen on {universe} universe...")
        
        tickers = self.get_universe(universe)
        results = []
        
        for i, ticker in enumerate(tickers[:100]):  # Limit for speed
            if i % 10 == 0:
                print(f"  Progress: {i}/{min(100, len(tickers))} tickers...")
            
            data = self.analyze_fundamentals(ticker)
            
            if 'error' not in data and filter_func(data):
                results.append({
                    'ticker': ticker,
                    'company': data['company_name'],
                    'revenue_growth': f"{data['revenue_growth']*100:.1f}%",
                    'gross_margin': f"{data['gross_margin']*100:.1f}%",
                    'pe_ratio': f"{data['pe_ratio']:.1f}" if data['pe_ratio'] > 0 else 'N/A',
                    'market_cap_B': f"${data['market_cap']/1e9:.1f}B",
                    'analyst_upside': f"{data['analyst_upside']:.1f}%"
                })
        
        return pd.DataFrame(results)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enhanced Stock Screener - Find stocks matching specific criteria',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Growth stocks approaching profitability (20%+ growth)
    python enhanced_screener.py --preset growth_to_profit --min-growth 0.2
    
    # Profitable companies with 15%+ growth and 30%+ margins
    python enhanced_screener.py --preset profitable_growth --min-growth 0.15 --min-margin 0.3
    
    # Custom criteria (example: tech stocks with improving margins)
    python enhanced_screener.py --custom "sector=='Technology' and improving_margins"
    
Presets:
    growth_to_profit: High growth companies approaching profitability
    profitable_growth: Already profitable with strong growth
        """
    )
    
    parser.add_argument('--preset', choices=['growth_to_profit', 'profitable_growth'],
                       help='Use predefined screening criteria')
    parser.add_argument('--custom', help='Custom filter expression using data fields')
    parser.add_argument('--universe', choices=['liquid', 'russell1000', 'russell2000'],
                       default='russell1000', help='Universe to screen')
    parser.add_argument('--min-growth', type=float, default=0.2,
                       help='Minimum revenue growth rate (default: 0.2 = 20%)')
    parser.add_argument('--min-margin', type=float, default=0.2,
                       help='Minimum gross margin (default: 0.2 = 20%)')
    parser.add_argument('--save', action='store_true', help='Save results to CSV')
    parser.add_argument('--top', type=int, default=20, help='Number of results to show')
    
    args = parser.parse_args()
    
    screener = EnhancedScreener()
    
    # Run appropriate screen
    if args.preset == 'growth_to_profit':
        results = screener.screen_growth_to_profitability(args.min_growth)
    elif args.preset == 'profitable_growth':
        results = screener.screen_profitable_growth(args.min_growth, args.min_margin)
    elif args.custom:
        # Create custom filter function
        def custom_filter(data):
            try:
                # Create safe eval environment with data fields
                return eval(args.custom, {"__builtins__": {}}, data)
            except:
                return False
        results = screener.screen_custom(custom_filter, args.universe)
    else:
        parser.error("Must specify --preset or --custom")
    
    # Display results
    if not results.empty:
        print(f"\nTop {min(args.top, len(results))} Results:")
        print("=" * 100)
        print(results.head(args.top).to_string(index=False))
        print(f"\nTotal matches: {len(results)}")
        
        # Save if requested
        if args.save:
            filename = f"screen_results_{args.preset or 'custom'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path = f"data/output/{filename}"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            results.to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")
    else:
        print("\nNo stocks found matching criteria.")


if __name__ == "__main__":
    main()
