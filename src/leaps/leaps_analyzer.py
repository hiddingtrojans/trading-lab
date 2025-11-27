#!/usr/bin/env python3
"""
LEAPS Analyzer - Find the BEST LEAPS options with pricing analysis and arbitrage detection
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time
import argparse

from ib_insync import IB, Stock, Option
from tabulate import tabulate


class LEAPSAnalyzer:
    """Analyzes LEAPS options for best opportunities and arbitrage."""
    
    def __init__(self):
        self.ib = IB()
        logging.basicConfig(level=logging.WARNING)
        
        # Analysis criteria
        self.min_days_to_expiry = 270
        self.min_delta = 0.50
        self.max_delta = 0.90
        self.max_spread_pct = 30.0
        self.min_oi = 5
        
    def connect(self) -> bool:
        """Connect to IBKR Gateway."""
        try:
            print("🔌 Connecting to IBKR Gateway...")
            self.ib.connect('127.0.0.1', 4001, clientId=7)
            print("✅ Connected!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
    
    def get_stock_price(self, stock: Stock) -> float:
        """Get current stock price."""
        try:
            self.ib.reqMktData(stock, '', True, False)
            self.ib.sleep(1)
            ticker = self.ib.ticker(stock)
            self.ib.cancelMktData(stock)
            
            if ticker.last and ticker.last > 0:
                return ticker.last
            elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                return (ticker.bid + ticker.ask) / 2
            return 0
        except:
            return 0
    
    def get_option_data(self, option: Option) -> dict:
        """Get comprehensive option data."""
        try:
            # Get market data
            self.ib.reqMktData(option, '', False, False)  # Back to original working method
            self.ib.sleep(2)  # Wait longer for Greeks
            ticker = self.ib.ticker(option)
            self.ib.cancelMktData(option)
            
            # Extract basic data
            bid = ticker.bid if ticker.bid == ticker.bid else 0
            ask = ticker.ask if ticker.ask == ticker.ask else 0
            last = ticker.last if ticker.last == ticker.last else 0
            mid = (bid + ask) / 2 if bid > 0 and ask > 0 else last
            volume = getattr(ticker, 'volume', 0) or 0
            
            # Extract Greeks
            delta = np.nan
            gamma = np.nan
            theta = np.nan
            vega = np.nan
            iv = np.nan
            
            if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks:
                delta = getattr(ticker.modelGreeks, 'delta', np.nan)
                gamma = getattr(ticker.modelGreeks, 'gamma', np.nan)
                theta = getattr(ticker.modelGreeks, 'theta', np.nan)
                vega = getattr(ticker.modelGreeks, 'vega', np.nan)
                iv = getattr(ticker.modelGreeks, 'impliedVol', np.nan)
            
            # Get contract details for OI
            oi = 0
            try:
                details = self.ib.reqContractDetails(option)
                if details:
                    oi = getattr(details[0].contract, 'openInterest', 0) or 0
            except:
                pass
            
            return {
                'bid': bid,
                'ask': ask,
                'last': last,
                'mid': mid,
                'volume': volume,
                'open_interest': oi,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'iv': iv
            }
        except Exception as e:
            print(f"   ⚠️ Error getting option data: {e}")
            return {}
    
    def calculate_metrics(self, option_data: dict, spot_price: float, strike: float, days_to_expiry: int) -> dict:
        """Calculate all option metrics."""
        try:
            mid = option_data.get('mid', 0)
            bid = option_data.get('bid', 0)
            ask = option_data.get('ask', 0)
            delta = option_data.get('delta', np.nan)
            iv = option_data.get('iv', np.nan)
            theta = option_data.get('theta', np.nan)
            
            # Basic calculations
            spread = ask - bid if ask > bid else 0
            spread_pct = (spread / mid * 100) if mid > 0 else 999
            
            intrinsic = max(0, spot_price - strike)
            time_value = max(0, mid - intrinsic)
            
            breakeven = strike + mid
            upside_to_breakeven = ((breakeven - spot_price) / spot_price * 100) if spot_price > 0 else 999
            
            # Annualized metrics
            years_to_expiry = days_to_expiry / 365.25
            theta_annualized = theta * 365.25 if not np.isnan(theta) else np.nan
            time_decay_pct = (abs(theta) / mid * 100) if mid > 0 and not np.isnan(theta) else np.nan
            
            # Value metrics
            moneyness = spot_price / strike if strike > 0 else 0
            time_value_pct = (time_value / spot_price * 100) if spot_price > 0 else 0
            
            return {
                'spread': spread,
                'spread_pct': spread_pct,
                'intrinsic': intrinsic,
                'time_value': time_value,
                'time_value_pct': time_value_pct,
                'breakeven': breakeven,
                'upside_to_breakeven': upside_to_breakeven,
                'moneyness': moneyness,
                'theta_annualized': theta_annualized,
                'time_decay_pct': time_decay_pct,
                'years_to_expiry': years_to_expiry
            }
        except Exception as e:
            print(f"   ⚠️ Error calculating metrics: {e}")
            return {}
    
    def score_option(self, option_data: dict, metrics: dict) -> float:
        """Score option attractiveness (higher = better)."""
        try:
            delta = option_data.get('delta', 0)
            iv = option_data.get('iv', 0)
            spread_pct = metrics.get('spread_pct', 999)
            time_value_pct = metrics.get('time_value_pct', 0)
            upside_to_breakeven = metrics.get('upside_to_breakeven', 999)
            oi = option_data.get('open_interest', 0)
            
            # Scoring components (0-1 scale)
            delta_score = 1 - abs(delta - 0.70) / 0.30 if not np.isnan(delta) else 0  # Prefer ~0.70 delta
            delta_score = max(0, min(1, delta_score))
            
            liquidity_score = min(1, oi / 100) if oi > 0 else 0  # Normalize OI
            
            spread_score = max(0, 1 - spread_pct / 30) if spread_pct < 999 else 0  # Penalize wide spreads
            
            upside_score = max(0, 1 - upside_to_breakeven / 50) if upside_to_breakeven < 999 else 0  # Prefer lower upside needed
            
            iv_score = min(1, iv * 2) if not np.isnan(iv) and iv > 0 else 0  # Higher IV is better (up to 50%)
            
            time_value_score = min(1, time_value_pct / 10) if time_value_pct > 0 else 0  # Prefer decent time value
            
            # Weighted composite score
            score = (
                3.0 * delta_score +      # Delta fit most important
                2.0 * liquidity_score +  # Liquidity very important  
                2.0 * spread_score +     # Tight spreads important
                1.5 * upside_score +     # Reasonable breakeven
                1.0 * iv_score +         # Higher IV preferred
                0.5 * time_value_score   # Some time value good
            )
            
            return score
            
        except Exception as e:
            print(f"   ⚠️ Error scoring option: {e}")
            return 0
    
    def check_arbitrage(self, options_data: list, symbol: str) -> list:
        """Check for arbitrage opportunities."""
        violations = []
        
        try:
            # Group by expiry
            by_expiry = {}
            for opt in options_data:
                expiry = opt['expiry']
                if expiry not in by_expiry:
                    by_expiry[expiry] = []
                by_expiry[expiry].append(opt)
            
            # Check each expiry for monotonicity violations
            for expiry, opts in by_expiry.items():
                opts.sort(key=lambda x: x['strike'])
                
                for i in range(len(opts) - 1):
                    opt1, opt2 = opts[i], opts[i + 1]
                    
                    if opt1['mid'] > 0 and opt2['mid'] > 0:
                        # Call spread arbitrage: C(K1) should >= C(K2) for K1 < K2
                        if opt1['mid'] < opt2['mid']:
                            profit = opt2['mid'] - opt1['mid']
                            max_risk = opt2['strike'] - opt1['strike']
                            
                            violations.append({
                                'type': 'Call Spread Arbitrage',
                                'symbol': symbol,
                                'expiry': expiry,
                                'description': f'Buy ${opt1["strike"]} Call (${opt1["mid"]:.2f}), Sell ${opt2["strike"]} Call (${opt2["mid"]:.2f})',
                                'profit': profit,
                                'max_risk': max_risk,
                                'return_pct': (profit / max_risk * 100) if max_risk > 0 else 0
                            })
            
            return violations
            
        except Exception as e:
            print(f"   ⚠️ Error checking arbitrage: {e}")
            return []
    
    def analyze_ticker(self, symbol: str, max_options: int = 10) -> dict:
        """Comprehensive LEAPS analysis for a ticker."""
        symbol = symbol.upper()
        print(f"\n{'='*80}")
        print(f"📈 ANALYZING LEAPS FOR: {symbol}")
        print(f"{'='*80}")
        
        # Get stock
        try:
            stock = Stock(symbol, 'SMART', 'USD')
            qualified_stocks = self.ib.qualifyContracts(stock)
            if not qualified_stocks:
                print(f"❌ {symbol}: Stock not found")
                return {}
            stock = qualified_stocks[0]
        except Exception as e:
            print(f"❌ {symbol}: Error getting stock - {e}")
            return {}
        
        # Get stock price
        # Get current stock price (snapshot for closed market)
        try:
            self.ib.reqMktData(stock, '', False, False)  # Back to original working method
            self.ib.sleep(1.5)
            ticker = self.ib.ticker(stock)
            self.ib.cancelMktData(stock)
            
            spot_price = 0
            if ticker.last and ticker.last > 0:
                spot_price = ticker.last
            elif ticker.close and ticker.close > 0:
                spot_price = ticker.close  # Use close price when market closed
            elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                spot_price = (ticker.bid + ticker.ask) / 2
                
            if spot_price <= 0:
                print(f"❌ {symbol}: No price data")
                return {}
        except Exception as e:
            print(f"❌ {symbol}: Price error - {e}")
            return {}
        
        print(f"💰 Current Price: ${spot_price:.2f}")
        
        # Get option chains
        try:
            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                print(f"❌ {symbol}: No option chains")
                return {}
        except Exception as e:
            print(f"❌ {symbol}: Error getting chains - {e}")
            return {}
        
        # Find LEAPS expiries
        min_expiry_date = datetime.now() + timedelta(days=self.min_days_to_expiry)
        leaps_expiries = []
        
        for chain in chains[:3]:  # Check first 3 exchanges
            for expiry in chain.expirations:
                expiry_date = datetime.strptime(expiry, '%Y%m%d')
                if expiry_date >= min_expiry_date:
                    days_out = (expiry_date - datetime.now()).days
                    leaps_expiries.append({
                        'expiry': expiry,
                        'days_out': days_out,
                        'strikes': chain.strikes,
                        'exchange': chain.exchange
                    })
                    break  # One LEAPS per exchange
        
        if not leaps_expiries:
            print(f"❌ {symbol}: No LEAPS found")
            return {}
        
        print(f"⏰ Found {len(leaps_expiries)} LEAPS expiries")
        
        # Analyze options
        all_options = []
        arbitrage_opportunities = []
        
        for leap in leaps_expiries[:2]:  # Max 2 expiries
            expiry = leap['expiry']
            days_out = leap['days_out']
            exchange = leap['exchange']
            
            print(f"\n📅 Analyzing {expiry} ({days_out} days)...")
            
            # Focus on reasonable strikes
            relevant_strikes = [
                s for s in leap['strikes'] 
                if 0.7 * spot_price <= s <= 1.4 * spot_price
            ][:8]  # Max 8 strikes per expiry
            
            expiry_options = []
            
            for strike in relevant_strikes:
                try:
                    # Use the actual exchange from the chain data
                    option = Option(symbol, expiry, strike, 'C', exchange)
                    qualified = self.ib.qualifyContracts(option)
                    
                    if not qualified:
                        continue
                    
                    option = qualified[0]
                    
                    print(f"   Analyzing ${strike} call...", end=' ')
                    
                    # Get option data
                    option_data = self.get_option_data(option)
                    if not option_data or option_data.get('mid', 0) <= 0:
                        print("❌")
                        continue
                    
                    # Calculate metrics
                    metrics = self.calculate_metrics(option_data, spot_price, strike, days_out)
                    if not metrics:
                        print("❌")
                        continue
                    
                    # Score option
                    score = self.score_option(option_data, metrics)
                    
                    # Combine all data
                    full_option = {
                        'symbol': symbol,
                        'expiry': expiry,
                        'strike': strike,
                        'days_out': days_out,
                        'spot_price': spot_price,
                        'score': score,
                        **option_data,
                        **metrics
                    }
                    
                    all_options.append(full_option)
                    expiry_options.append(full_option)
                    
                    print(f"✅ Score: {score:.1f}")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    continue
            
            # Check for arbitrage in this expiry
            if len(expiry_options) >= 2:
                arb_ops = self.check_arbitrage(expiry_options, symbol)
                arbitrage_opportunities.extend(arb_ops)
        
        # Sort by score
        all_options.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'symbol': symbol,
            'spot_price': spot_price,
            'options': all_options[:max_options],
            'arbitrage': arbitrage_opportunities
        }
    
    def display_results(self, results: dict):
        """Display analysis results."""
        if not results:
            return
        
        symbol = results['symbol']
        spot_price = results['spot_price']
        options = results['options']
        arbitrage = results['arbitrage']
        
        print(f"\n🎯 TOP LEAPS OPTIONS FOR {symbol}")
        print("=" * 120)
        
        if options:
            headers = ['Strike', 'Expiry', 'Days', 'Premium', 'Delta', 'IV', 'Spread%', 'OI', 'Breakeven', 'Upside%', 'Score']
            rows = []
            
            for opt in options[:10]:
                rows.append([
                    f"${opt['strike']:.0f}",
                    opt['expiry'][:6],
                    opt['days_out'],
                    f"${opt['mid']:.2f}",
                    f"{opt['delta']:.2f}" if not np.isnan(opt['delta']) else 'N/A',
                    f"{opt['iv']:.0%}" if not np.isnan(opt['iv']) else 'N/A',
                    f"{opt['spread_pct']:.1f}%",
                    int(opt['open_interest']),
                    f"${opt['breakeven']:.2f}",
                    f"{opt['upside_to_breakeven']:.0f}%",
                    f"{opt['score']:.1f}"
                ])
            
            print(tabulate(rows, headers=headers, tablefmt='grid'))
        
        if arbitrage:
            print(f"\n🚨 ARBITRAGE OPPORTUNITIES")
            print("=" * 80)
            
            for arb in arbitrage:
                print(f"💰 {arb['type']}: {arb['description']}")
                print(f"   Profit: ${arb['profit']:.2f}, Max Risk: ${arb['max_risk']:.2f}, Return: {arb['return_pct']:.1f}%")
        
        # Best Option Summary
        if options:
            best = options[0]
            print(f"\n🏆 BEST LEAPS OPTION SUMMARY")
            print("=" * 60)
            
            # Format expiry nicely
            expiry_str = f"{best['expiry'][:4]}-{best['expiry'][4:6]}-{best['expiry'][6:]}"
            expiry_readable = datetime.strptime(best['expiry'], '%Y%m%d').strftime('%B %Y')
            
            print(f"Best Option: ${best['strike']:.0f} strike ({expiry_readable}) - Score {best['score']:.1f}")
            print(f"Premium: ${best['mid']:.2f}, Delta: {best['delta']:.2f}, IV: {best['iv']:.0%}" if not np.isnan(best['delta']) and not np.isnan(best['iv']) else f"Premium: ${best['mid']:.2f}")
            
            # Breakeven analysis
            upside_needed = best['upside_to_breakeven']
            if upside_needed < 15:
                print(f"Only needs {upside_needed:.0f}% upside to breakeven 🟢")
            elif upside_needed < 30:
                print(f"Needs {upside_needed:.0f}% upside to breakeven 🟡")
            else:
                print(f"Needs {upside_needed:.0f}% upside to breakeven 🔴")
            
            # Spread analysis
            spread = best['spread_pct']
            if spread < 5:
                print(f"Tight {spread:.1f}% bid-ask spread 🟢")
            elif spread < 15:
                print(f"Moderate {spread:.1f}% bid-ask spread 🟡")
            else:
                print(f"Wide {spread:.1f}% bid-ask spread 🔴")
            
            # Delta analysis
            delta = best['delta']
            if not np.isnan(delta):
                if delta > 0.75:
                    print(f"High delta ({delta:.2f}) = excellent leverage 🟢")
                elif delta > 0.60:
                    print(f"Good delta ({delta:.2f}) = solid leverage 🟡")
                else:
                    print(f"Moderate delta ({delta:.2f}) = limited leverage 🔴")
            
            # Open Interest
            oi = best['open_interest']
            if oi > 100:
                print(f"Good liquidity: {oi:.0f} open interest 🟢")
            elif oi > 10:
                print(f"Moderate liquidity: {oi:.0f} open interest 🟡")
            else:
                print(f"Low liquidity: {oi:.0f} open interest 🔴")
            
            # Time value analysis
            time_val_pct = best['time_value_pct']
            if time_val_pct > 5:
                print(f"Rich time value: {time_val_pct:.1f}% of stock price 🟡")
            else:
                print(f"Reasonable time value: {time_val_pct:.1f}% of stock price 🟢")
            
            print("=" * 60)
        
        print("=" * 120)


def batch_scan_tickers(tickers: list, min_score: float = 7.0):
    """Scan multiple tickers using the same logic as individual analysis."""
    analyzer = LEAPSAnalyzer()
    
    if not analyzer.connect():
        return
    
    excellent_options = []
    
    try:
        print(f"\n🎯 SCANNING {len(tickers)} TICKERS FOR EXCELLENT LEAPS (Score ≥ {min_score})")
        print("=" * 80)
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i:2d}/{len(tickers)}] 🔍 {ticker}...", end=' ', flush=True)
            
            try:
                results = analyzer.analyze_ticker(ticker, max_options=5)  # Limit options for speed
                
                if results and results.get('options'):
                    # Find options that meet the score threshold
                    good_options = [opt for opt in results['options'] if opt['score'] >= min_score]
                    
                    if good_options:
                        excellent_options.extend(good_options)
                        print(f"✅ Found {len(good_options)} excellent option(s)")
                    else:
                        print("❌ No excellent options")
                else:
                    print("❌ No options found")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
            
            # Small delay between tickers
            time.sleep(0.1)
        
        # Display results
        if excellent_options:
            # Sort by score
            excellent_options.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"\n🏆 EXCELLENT LEAPS OPTIONS FOUND (Score ≥ {min_score})")
            print("=" * 120)
            
            headers = ['Symbol', 'Strike', 'Expiry', 'Days', 'Premium', 'Contract Cost', 'Delta', 'IV', 'Spread%', 'Upside%', 'Score']
            rows = []
            
            for opt in excellent_options:
                contract_cost = opt['mid'] * 100
                rows.append([
                    opt['symbol'],
                    f"${opt['strike']:.0f}",
                    opt['expiry'][:6],
                    opt['days_out'],
                    f"${opt['mid']:.2f}",
                    f"${contract_cost:.0f}",
                    f"{opt['delta']:.2f}" if not np.isnan(opt['delta']) else 'N/A',
                    f"{opt['iv']:.0%}" if not np.isnan(opt['iv']) else 'N/A',
                    f"{opt['spread_pct']:.1f}%",
                    f"{opt['upside_to_breakeven']:.0f}%",
                    f"{opt['score']:.1f}"
                ])
            
            print(tabulate(rows, headers=headers, tablefmt='grid'))
            
            # Show TOP 5 CHOICES
            top_5 = excellent_options[:5]
            print(f"\n🏆 TOP {len(top_5)} EXCELLENT CHOICES:")
            print("=" * 80)
            
            for i, opt in enumerate(top_5, 1):
                contract_cost = opt['mid'] * 100
                expiry_readable = datetime.strptime(opt['expiry'], '%Y%m%d').strftime('%b %Y')
                
                # Color coding for upside needed
                upside = opt['upside_to_breakeven']
                if upside < 15:
                    upside_color = "🟢"
                elif upside < 30:
                    upside_color = "🟡"
                else:
                    upside_color = "🔴"
                
                # Color coding for contract cost
                if contract_cost < 500:
                    cost_color = "🟢"
                elif contract_cost < 2000:
                    cost_color = "🟡"
                else:
                    cost_color = "🔴"
                
                print(f"{i}. **{opt['symbol']} ${opt['strike']:.2f} {expiry_readable}** - Score {opt['score']:.1f}")
                print(f"   Contract Cost: ${contract_cost:.0f} {cost_color} | Delta: {opt['delta']:.2f} | Upside: {upside:.0f}% {upside_color}")
                print(f"   EXACT: Strike ${opt['strike']:.2f} | Bid ${opt['bid']:.2f} / Ask ${opt['ask']:.2f} | Breakeven: ${opt['breakeven']:.2f}")
                print(f"   Premium: ${opt['mid']:.2f} | Spread: {opt['spread_pct']:.1f}% | IV: {opt['iv']:.0%}" if not np.isnan(opt['iv']) else f"   Premium: ${opt['mid']:.2f} | Spread: {opt['spread_pct']:.1f}%")
                print()
            
            print("=" * 80)
            
            # Save to CSV
            df = pd.DataFrame(excellent_options)
            df.to_csv('output/excellent_leaps.csv', index=False)
            print(f"\n💾 Saved {len(excellent_options)} excellent options to output/excellent_leaps.csv")
            
        else:
            print(f"\n❌ NO EXCELLENT LEAPS FOUND (Score ≥ {min_score})")
            print("Try lowering the score threshold")
        
        print("=" * 120)
        
    finally:
        analyzer.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Analyze LEAPS options for best opportunities')
    parser.add_argument('ticker', nargs='?', help='Ticker symbol to analyze')
    parser.add_argument('--max-options', '-n', type=int, default=10, help='Max options to analyze')
    parser.add_argument('--batch', nargs='*', help='Batch scan multiple tickers')
    parser.add_argument('--from-csv', action='store_true', help='Scan all tickers from CSV')
    parser.add_argument('--min-score', type=float, default=7.0, help='Minimum score for batch scan')
    args = parser.parse_args()
    
    if args.from_csv:
        # Load from CSV and batch scan
        universe_df = pd.read_csv('leaps_universe_ibkr.csv')
        tickers = universe_df['Ticker'].tolist()
        print(f"📁 Loaded {len(tickers)} tickers from universe CSV")
        batch_scan_tickers(tickers, args.min_score)
        
    elif args.batch is not None:
        # Batch scan specified tickers
        tickers = [t.upper() for t in args.batch] if args.batch else []
        if not tickers:
            print("Usage: python leaps_analyzer.py --batch TICKER1 TICKER2 TICKER3")
            return
        batch_scan_tickers(tickers, args.min_score)
        
    elif args.ticker:
        # Single ticker analysis
        analyzer = LEAPSAnalyzer()
        
        if not analyzer.connect():
            return
        
        try:
            results = analyzer.analyze_ticker(args.ticker, args.max_options)
            analyzer.display_results(results)
            
        except KeyboardInterrupt:
            print("\n⏹️ Analysis interrupted")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            analyzer.disconnect()
            
    else:
        print("Usage:")
        print("  python leaps_analyzer.py TICKER              # Analyze single ticker")
        print("  python leaps_analyzer.py --batch TICK1 TICK2 # Batch scan specific tickers")
        print("  python leaps_analyzer.py --from-csv          # Scan entire universe")
        print("  python leaps_analyzer.py --from-csv --min-score 6.5  # Lower threshold")


if __name__ == "__main__":
    main()
