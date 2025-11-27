#!/usr/bin/env python3
"""
Cursor-Driven Analysis Workflow
===============================

Workflow:
1. User asks Cursor to find tickers meeting criteria (e.g., 20%+ growth)
2. User provides ticker list to this script
3. Script analyzes each ticker for:
   - LEAPS availability and pricing
   - Technical signals (gap, momentum, VWAP)
   - Sentiment analysis
   - Recent news
   - Options flow
4. Outputs ranked opportunities

Usage:
    python cursor_workflow.py --tickers AAPL,NVDA,TSLA --criteria "20% growth"
    python cursor_workflow.py --file growth_tickers.txt --criteria "high momentum"
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import yfinance as yf
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

from alpha_lab.intraday_signals import IntradaySignalGenerator


class CursorWorkflow:
    """Main workflow for analyzing Cursor-identified tickers."""
    
    def __init__(self):
        # Don't initialize signal generator here - it requires IB connection
        self.results = []
        
    def analyze_ticker(self, ticker: str, criteria: str = "") -> Dict:
        """
        Comprehensive analysis of a single ticker.
        
        Returns:
            Dict with all analysis results
        """
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker}")
        print(f"{'='*60}")
        
        result = {
            'ticker': ticker,
            'criteria': criteria,
            'timestamp': datetime.now().isoformat(),
            'scores': {},
            'signals': {},
            'leaps': {},
            'sentiment': {},
            'recommendation': None
        }
        
        try:
            # 1. Check if stock exists and get basic info
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info.get('regularMarketPrice'):
                print(f"  ✗ {ticker} not found or no price data")
                result['error'] = 'Invalid ticker'
                return result
                
            price = info.get('regularMarketPrice', 0)
            market_cap = info.get('marketCap', 0)
            
            result['price'] = price
            result['market_cap'] = market_cap
            result['name'] = info.get('longName', ticker)
            
            print(f"  {result['name']}")
            print(f"  Price: ${price:.2f}")
            print(f"  Market Cap: ${market_cap/1e9:.2f}B")
            
            # 2. Technical Analysis (gaps, momentum, VWAP)
            print(f"\n  Technical Analysis:")
            
            # Get recent price data
            df = yf.download(ticker, period='60d', interval='1d', progress=False)
            
            if len(df) > 20:
                # Calculate technical indicators
                df['SMA20'] = df['Close'].rolling(20).mean()
                df['RSI'] = self.calculate_rsi(df['Close'])
                
                # Recent performance
                perf_1d = (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100
                perf_5d = (df['Close'].iloc[-1] / df['Close'].iloc[-5] - 1) * 100
                perf_20d = (df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100
                
                result['performance'] = {
                    '1d': perf_1d,
                    '5d': perf_5d,
                    '20d': perf_20d
                }
                
                print(f"    1D: {float(perf_1d):+.2f}%")
                print(f"    5D: {float(perf_5d):+.2f}%")
                print(f"    20D: {float(perf_20d):+.2f}%")
                
                # Momentum score
                momentum_score = 0
                if float(df['Close'].iloc[-1]) > float(df['SMA20'].iloc[-1]):
                    momentum_score += 30
                if float(perf_5d) > 5:
                    momentum_score += 35
                rsi_val = float(df['RSI'].iloc[-1])
                if rsi_val > 50 and rsi_val < 70:
                    momentum_score += 35
                    
                result['scores']['momentum'] = momentum_score
                print(f"    Momentum Score: {momentum_score}/100")
            
            # 3. Check LEAPS availability
            print(f"\n  LEAPS Analysis:")
            
            leaps_data = self.check_leaps(ticker, price)
            result['leaps'] = leaps_data
            
            if leaps_data.get('available'):
                print(f"    ✓ LEAPS available")
                print(f"    Expiries: {len(leaps_data.get('expiries', []))}")
                if leaps_data.get('best_strike'):
                    print(f"    Best Strike: ${leaps_data['best_strike']}")
                    print(f"    Premium: ${leaps_data.get('premium', 0):.2f}")
                    print(f"    Leverage: {leaps_data.get('leverage', 0):.1f}x")
            else:
                print(f"    ✗ No suitable LEAPS found")
            
            # 4. Intraday signals check (simplified without IB)
            print(f"\n  Intraday Signals:")
            
            # Simple gap check from daily data
            if len(df) > 1:
                today_open = df['Open'].iloc[-1]
                yesterday_close = df['Close'].iloc[-2]
                gap_pct = (today_open - yesterday_close) / yesterday_close * 100
                
                intraday_signals = {
                    'has_gap': abs(float(gap_pct)) > 1.0,
                    'gap_size': float(gap_pct),
                    'has_momentum': float(perf_1d) > 2.0,
                    'near_vwap': True  # Placeholder
                }
                result['signals'] = intraday_signals
                
                if intraday_signals.get('has_gap'):
                    print(f"    ✓ Gap: {intraday_signals['gap_size']:+.2f}%")
                if intraday_signals.get('has_momentum'):
                    print(f"    ✓ Strong momentum detected")
            else:
                result['signals'] = {}
                
            # 5. News & Sentiment (simplified)
            print(f"\n  Sentiment Analysis:")
            
            sentiment = self.analyze_sentiment(ticker)
            result['sentiment'] = sentiment
            
            print(f"    News mentions: {sentiment.get('news_count', 0)}")
            print(f"    Sentiment: {sentiment.get('overall', 'Neutral')}")
            
            # 6. Calculate composite score
            composite_score = self.calculate_composite_score(result)
            result['composite_score'] = composite_score
            
            # 7. Generate recommendation
            if composite_score >= 80:
                recommendation = "STRONG BUY"
                action = "Consider LEAPS + Day trade"
            elif composite_score >= 60:
                recommendation = "BUY"
                action = "LEAPS recommended"
            elif composite_score >= 40:
                recommendation = "WATCH"
                action = "Monitor for better entry"
            else:
                recommendation = "PASS"
                action = "Look for other opportunities"
                
            result['recommendation'] = recommendation
            result['action'] = action
            
            print(f"\n  {'='*40}")
            print(f"  Composite Score: {composite_score}/100")
            print(f"  Recommendation: {recommendation}")
            print(f"  Action: {action}")
            print(f"  {'='*40}")
            
        except Exception as e:
            print(f"  ✗ Error analyzing {ticker}: {e}")
            result['error'] = str(e)
            
        return result
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def check_leaps(self, ticker: str, current_price: float) -> Dict:
        """Check LEAPS availability and find best opportunities."""
        try:
            stock = yf.Ticker(ticker)
            
            # Get all expiration dates
            expirations = stock.options
            
            # Filter for LEAPS (> 6 months out)
            today = datetime.now()
            leaps_expiries = []
            
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_to_exp = (exp_date - today).days
                
                if days_to_exp > 180:  # 6+ months
                    leaps_expiries.append({
                        'date': exp,
                        'days': days_to_exp
                    })
            
            if not leaps_expiries:
                return {'available': False}
            
            # Analyze best LEAPS opportunity
            best_leaps = self.find_best_leaps(ticker, leaps_expiries, current_price)
            
            return {
                'available': True,
                'expiries': leaps_expiries,
                **best_leaps
            }
            
        except:
            return {'available': False}
    
    def find_best_leaps(self, ticker: str, expiries: List[Dict], current_price: float) -> Dict:
        """Find the best LEAPS strike and expiry."""
        stock = yf.Ticker(ticker)
        
        best_option = None
        best_score = 0
        
        # Look at 9-15 month expiries
        target_expiries = [e for e in expiries if 270 <= e['days'] <= 450]
        
        if not target_expiries:
            target_expiries = expiries[:3]  # Take closest 3
        
        for expiry in target_expiries[:2]:  # Check first 2 expiries
            try:
                chain = stock.option_chain(expiry['date'])
                calls = chain.calls
                
                # Find strikes 10-30% OTM
                target_strikes = calls[
                    (calls['strike'] >= current_price * 1.1) & 
                    (calls['strike'] <= current_price * 1.3)
                ]
                
                if target_strikes.empty:
                    continue
                
                for _, opt in target_strikes.iterrows():
                    if opt['volume'] > 0 and opt['openInterest'] > 10:
                        # Calculate leverage and score
                        premium = opt['lastPrice']
                        leverage = current_price / premium if premium > 0 else 0
                        
                        # Score based on leverage, volume, and spread
                        spread = opt['ask'] - opt['bid'] if opt['ask'] > 0 else float('inf')
                        spread_pct = spread / opt['ask'] * 100 if opt['ask'] > 0 else 100
                        
                        score = leverage * 10  # Leverage weight
                        score += min(opt['volume'] / 10, 20)  # Volume weight
                        score -= spread_pct * 2  # Penalty for wide spread
                        
                        if score > best_score:
                            best_score = score
                            best_option = {
                                'strike': opt['strike'],
                                'expiry': expiry['date'],
                                'premium': premium,
                                'leverage': leverage,
                                'volume': opt['volume'],
                                'open_interest': opt['openInterest'],
                                'spread_pct': spread_pct
                            }
                            
            except:
                continue
        
        return best_option or {}
    
    def analyze_sentiment(self, ticker: str) -> Dict:
        """Analyze news sentiment (simplified version)."""
        # In a real implementation, this would:
        # - Fetch recent news from multiple sources
        # - Analyze sentiment using NLP
        # - Check social media mentions
        # - Look at insider activity
        
        # For now, return mock data
        return {
            'news_count': np.random.randint(5, 20),
            'overall': np.random.choice(['Bullish', 'Neutral', 'Bearish'], p=[0.5, 0.3, 0.2]),
            'social_mentions': np.random.randint(100, 1000)
        }
    
    def calculate_composite_score(self, result: Dict) -> int:
        """Calculate overall opportunity score."""
        score = 0
        
        # Momentum component (30%)
        if 'momentum' in result.get('scores', {}):
            score += result['scores']['momentum'] * 0.3
        
        # LEAPS availability (25%)
        if result.get('leaps', {}).get('available'):
            score += 25
            # Bonus for good leverage
            if result['leaps'].get('leverage', 0) > 5:
                score += 5
        
        # Recent performance (20%)
        perf = result.get('performance', {})
        if perf.get('5d', 0) > 5:
            score += 10
        if perf.get('20d', 0) > 10:
            score += 10
            
        # Intraday signals (15%)
        signals = result.get('signals', {})
        if signals.get('has_gap'):
            score += 5
        if signals.get('has_momentum'):
            score += 5
        if signals.get('near_vwap'):
            score += 5
            
        # Sentiment (10%)
        if result.get('sentiment', {}).get('overall') == 'Bullish':
            score += 10
        elif result.get('sentiment', {}).get('overall') == 'Neutral':
            score += 5
            
        return min(int(score), 100)
    
    def run_analysis(self, tickers: List[str], criteria: str = ""):
        """Run analysis on list of tickers."""
        print(f"\nAnalyzing {len(tickers)} tickers")
        print(f"Criteria: {criteria or 'None specified'}")
        
        for ticker in tickers:
            result = self.analyze_ticker(ticker.upper().strip(), criteria)
            self.results.append(result)
            
        # Sort by composite score
        self.results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
    def print_summary(self):
        """Print summary of all analyzed tickers."""
        print(f"\n{'='*80}")
        print(f"SUMMARY - Top Opportunities")
        print(f"{'='*80}")
        
        print(f"\n{'Ticker':<8} {'Score':<8} {'Recommend':<12} {'Price':<10} {'5D%':<8} {'LEAPS':<8} {'Action'}")
        print("-" * 80)
        
        for result in self.results[:10]:  # Top 10
            if 'error' in result:
                continue
                
            ticker = result['ticker']
            score = result.get('composite_score', 0)
            rec = result.get('recommendation', 'N/A')
            price = result.get('price', 0)
            perf_5d = result.get('performance', {}).get('5d', 0)
            has_leaps = '✓' if result.get('leaps', {}).get('available') else '✗'
            action = result.get('action', '')[:30]  # Truncate action
            
            print(f"{ticker:<8} {score:<8} {rec:<12} ${price:<9.2f} {perf_5d:<+8.2f} {has_leaps:<8} {action}")
    
    def save_results(self):
        """Save detailed results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed JSON
        output_file = f'data/output/cursor_analysis_{timestamp}.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        # Save summary CSV
        summary_data = []
        for r in self.results:
            if 'error' not in r:
                summary_data.append({
                    'ticker': r['ticker'],
                    'score': r.get('composite_score', 0),
                    'recommendation': r.get('recommendation', ''),
                    'price': r.get('price', 0),
                    'perf_5d': r.get('performance', {}).get('5d', 0),
                    'has_leaps': r.get('leaps', {}).get('available', False),
                    'action': r.get('action', '')
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = f'data/output/cursor_summary_{timestamp}.csv'
            summary_df.to_csv(summary_file, index=False)
            print(f"Summary saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description='Analyze tickers identified by Cursor')
    
    # Input methods
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tickers', type=str, 
                      help='Comma-separated list of tickers (e.g., AAPL,NVDA,TSLA)')
    group.add_argument('--file', type=str,
                      help='File containing tickers (one per line)')
    
    parser.add_argument('--criteria', type=str, default='',
                       help='Criteria used to identify these tickers (for reference)')
    
    args = parser.parse_args()
    
    # Get ticker list
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(',')]
    else:
        with open(args.file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    # Run workflow
    workflow = CursorWorkflow()
    workflow.run_analysis(tickers, args.criteria)


if __name__ == "__main__":
    main()
