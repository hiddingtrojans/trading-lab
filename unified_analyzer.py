#!/usr/bin/env python3
"""
Unified Investment Analyzer
===========================

Single script that combines all analysis functionality:
- Stock screening (growth, value, momentum)
- LEAPS options analysis  
- Intraday signals (gap/momentum/VWAP)
- Day trading suitability
- Comprehensive backtesting
- Results output in clean format

Usage:
    python unified_analyzer.py --ticker NVDA
    python unified_analyzer.py --tickers NVDA,TSLA,PLTR
    python unified_analyzer.py --screen growth --top 10
    python unified_analyzer.py --file tickers.txt
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
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# Import analysis modules
from alpha_lab.intraday_signals import IntradaySignalGenerator
from leaps.complete_leaps_system import CompleteLEAPSSystem
from utils.data_fetcher import DataFetcher
from alpha_lab.sector_rotation import SectorRotationAnalyzer
from alpha_lab.market_regime import MarketRegimeAnalyzer
from alpha_lab.earnings_volatility import EarningsVolatilityAnalyzer
from alpha_lab.whale_detector import WhaleDetector
from alpha_lab.options_flow import OptionsFlowScanner
from alpha_lab.strategy_library import StrategyLibrary
from alpha_lab.portfolio.sizer import PositionSizer


class UnifiedAnalyzer:
    """Single analyzer for all investment strategies."""
    
    def __init__(self):
        self.results = []
        self.leaps_system = None
        self.signal_generator = None
        self.fetcher = DataFetcher(None) # Use fallback-capable fetcher
        self.sector_analyzer = SectorRotationAnalyzer(self.fetcher)
        self.regime_analyzer = MarketRegimeAnalyzer(self.fetcher)
        self.earnings_analyzer = EarningsVolatilityAnalyzer(self.fetcher)
        self.whale_detector = WhaleDetector(self.fetcher)
        self.flow_scanner = OptionsFlowScanner()
        self.sizer = PositionSizer(account_equity=100000) # Default $100k
        self._regime_cache = None
        
    def analyze_ticker(self, ticker: str, analysis_types: List[str] = None) -> Dict:
        """
        Run comprehensive analysis on a single ticker.
        
        Args:
            ticker: Stock symbol
            analysis_types: List of ['fundamentals', 'leaps', 'intraday', 'day_trade']
                          If None, runs all analyses
        
        Returns:
            Dictionary with all analysis results
        """
        if analysis_types is None:
            analysis_types = ['fundamentals', 'leaps', 'intraday', 'day_trade']
            
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker}")
        print('='*60)
        
        results = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'analyses': {}
        }
        
        # Get basic stock info
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            is_etf = info.get('quoteType', '').upper() == 'ETF' or 'ETF' in info.get('longName', '').upper()
            
            # Use DataFetcher for intraday history to ensure robustness and caching
            # Get 30 days of 5-min data
            hist = self.fetcher.get_intraday_data(ticker, days=30)
            
            if hist.empty:
                # Try yfinance history fallback for longer term if intraday failed or for daily view?
                # Stick to yf.Ticker for daily candles if needed, but intraday is key for signals
                # Let's fallback to yf.Ticker daily history if intraday missing
                daily_hist = stock.history(period="1mo")
                if daily_hist.empty:
                    print(f"  ✗ No data found for {ticker}")
                    return results
                
                # Normalize columns to match DataFetcher output for compatibility
                daily_hist = daily_hist.reset_index()
                daily_hist.columns = [c.lower() for c in daily_hist.columns]
                if 'date' in daily_hist.columns:
                     daily_hist['date'] = daily_hist['date'].dt.tz_localize(None) # Remove timezone
                
                hist = daily_hist
                current_price = hist['close'].iloc[-1]
            else:
                 current_price = hist['close'].iloc[-1]

            results['current_price'] = current_price
            results['company_name'] = info.get('longName', ticker)
            results['market_cap'] = info.get('marketCap', 0)
            results['sector'] = info.get('sector', 'Unknown')
            results['is_etf'] = is_etf
            
            if is_etf:
                print(f"  MACRO REPORT: {results['company_name']}")
            else:
                print(f"  {results['company_name']}")
                
            print(f"  Price: ${current_price:.2f}")
            print(f"  Market Cap: ${results['market_cap']/1e9:.2f}B")
            
            # Market Regime
            regime = self._get_market_regime()
            results['market_regime'] = regime
            print(f"  Market Regime: {regime['status']} (Score: {regime['score']})")
            print(f"  Action: {regime['action']}")
            
            # Sector Analysis
            sector_status = self._analyze_sector_status(results['sector'])
            results['analyses']['sector_rotation'] = sector_status
            print(f"  Sector: {results['sector']} ({sector_status.get('ticker', 'SPY')})")
            print(f"  Sector Status: {sector_status.get('status', 'Unknown')} (Score: {sector_status.get('score', 0)})")
            
            # Earnings Volatility (Skip for ETFs as they don't have earnings)
            if not is_etf:
                try:
                    earnings_vol = self.earnings_analyzer.analyze_earnings(ticker, current_price)
                    results['analyses']['earnings_volatility'] = earnings_vol
                    if earnings_vol.get('implied_move', 0) > 0:
                        print(f"  Implied Earnings Move: +/- {earnings_vol['implied_move']}% (Hist: {earnings_vol['historical_avg_move']}%)")
                        # Only print verdict if meaningful
                        if earnings_vol['verdict'] != "NEUTRAL":
                            print(f"  Volatility Edge: {earnings_vol['verdict']}")
                except Exception:
                    pass
            
        except Exception as e:
            print(f"  ✗ Error fetching data: {str(e)}")
            import traceback
            traceback.print_exc()
            return results
        
        # 1. Fundamental Analysis (Skip for ETFs)
        if 'fundamentals' in analysis_types and not is_etf:
            print("\n  Fundamental Analysis:")
            try:
                fundamentals = self._analyze_fundamentals(ticker, info, hist)
                results['analyses']['fundamentals'] = fundamentals
                
                # Print key metrics
                print(f"    Revenue Growth: {fundamentals.get('revenue_growth', 'N/A')}")
                print(f"    Earnings Growth: {fundamentals.get('earnings_growth', 'N/A')}")
                print(f"    P/E Ratio: {fundamentals.get('pe_ratio', 'N/A')}")
                print(f"    Gross Margin: {fundamentals.get('gross_margin', 'N/A')}")
                print(f"    ROE: {fundamentals.get('roe', 'N/A')}")
                print(f"    Debt/Equity: {fundamentals.get('debt_to_equity', 'N/A')}")
                print(f"    Score: {fundamentals.get('score', 0)}/100")
                
                # Show score breakdown
                breakdown = fundamentals.get('score_breakdown', {})
                if breakdown:
                    print(f"    Score Breakdown:")
                    print(f"      Revenue Growth: {breakdown.get('revenue_growth', 0)}/25")
                    print(f"      Earnings: {breakdown.get('earnings', 0)}/25")
                    print(f"      Quality/Margins: {breakdown.get('quality', 0)}/20")
                    print(f"      Valuation: {breakdown.get('valuation', 0)}/15")
                    print(f"      Financial Health: {breakdown.get('financial_health', 0)}/10")
                    print(f"      Analyst View: {breakdown.get('analyst_view', 0)}/5")
                
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                results['analyses']['fundamentals'] = {'error': str(e)}
        
        # Options Flow (Short Term)
        if 'leaps' in analysis_types:
             print("\n  Options Flow Analysis:")
             try:
                 flow_data = self.flow_scanner.scan_flow(ticker)
                 results['analyses']['options_flow'] = flow_data
                 
                 if flow_data.get('status') != 'ERROR':
                     print(f"    🌊 Sentiment: {flow_data['status']} (P/C Ratio: {flow_data.get('pc_ratio')})")
                     if flow_data.get('alerts'):
                         for alert in flow_data['alerts']:
                             print(f"    🚨 {alert['type']}: {alert['desc']} ({alert['expiry']} ${alert['strike']})")
                 else:
                     print("    No flow data available")
             except Exception:
                 pass

        # 2. LEAPS Analysis
        if 'leaps' in analysis_types:
            print("\n  LEAPS Analysis:")
            try:
                if self.leaps_system is None:
                    self.leaps_system = CompleteLEAPSSystem(
                        use_gpt=True,  # Enable GPT for comprehensive analysis
                        try_ibkr=True,  # Enable IBKR for real option data
                        use_finbert=True  # Enable FinBERT for sentiment analysis
                    )
                
                leaps_results = self.leaps_system.complete_systematic_analysis(ticker)
                results['analyses']['leaps'] = self._parse_leaps_results(leaps_results)
                
                leaps_data = results['analyses']['leaps']
                if leaps_data.get('available'):
                    print("    ✓ LEAPS available")
                    print(f"    Expiries: {leaps_data.get('expiry_count', 0)}")
                    if not is_etf:
                        print(f"    Score: {leaps_data.get('score', 0)}/100")
                        print(f"    Recommendation: {leaps_data.get('recommendation', 'N/A')}")
                    else:
                        print(f"    Liquidity: Excellent (ETF)")
                    
                    if leaps_data.get('optimal_strike'):
                        print(f"    Optimal Strike: ${leaps_data.get('optimal_strike')}")
                        print(f"    Optimal Expiry: {leaps_data.get('optimal_expiry')}")
                        if leaps_data.get('expected_return') and not is_etf:
                            print(f"    Expected Return: {leaps_data.get('expected_return')}%")
                else:
                    print("    ✗ No LEAPS available")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                results['analyses']['leaps'] = {'error': str(e)}
        
        # 3. Intraday Signals
        if 'intraday' in analysis_types:
            print("\n  Intraday Signals:")
            try:
                signals = self._analyze_intraday(ticker, hist)
                results['analyses']['intraday'] = signals
                
                if signals.get('has_signal'):
                    print(f"    ✓ {signals['signal_type']} signal detected")
                    print(f"    Strength: {signals['strength']}")
                else:
                    print("    No strong signals")
                
                # Whale Detector
                whale_data = self.whale_detector.detect_whales(ticker)
                results['analyses']['whale_alert'] = whale_data
                
                if whale_data['status'] not in ["NEUTRAL", "UNKNOWN"]:
                     print(f"    🐋 Whale Alert: {whale_data['status']} ({whale_data['confidence']} confidence)")
                     print(f"    Details: {whale_data['details']}")
                
                if whale_data.get('historical_alert'):
                     print(f"    🏛️  {whale_data['historical_alert']}")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                results['analyses']['intraday'] = {'error': str(e)}
        
        # 4. Day Trading Suitability
        if 'day_trade' in analysis_types:
            print("\n  Day Trading Analysis:")
            try:
                day_trade = self._analyze_day_trading(ticker, info, hist)
                results['analyses']['day_trade'] = day_trade
                
                if day_trade['suitable']:
                    print("    ✓ Suitable for day trading")
                    print(f"    ATR: ${day_trade['atr']:.2f}")
                    print(f"    Avg Volume: {day_trade['avg_volume']/1e6:.1f}M")
                else:
                    print("    ✗ Not suitable for day trading")
                    print(f"    Reason: {day_trade['reason']}")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                results['analyses']['day_trade'] = {'error': str(e)}
        
        # Tactical Plan
        plan = self._generate_tactical_plan(ticker, hist)
        results['tactical_plan'] = plan
        print(f"\n📝 TACTICAL PLAN ({plan.get('strategy', 'WAIT')})")
        if 'entry' in plan:
            print(f"   • Action: {plan['action']}")
            print(f"   • Entry: ${plan['entry']:.2f}")
            print(f"   • Stop:  ${plan['stop']:.2f}")
            print(f"   • Target: ${plan['target']:.2f}")
        else:
            print(f"   • {plan.get('reason', 'No setup')}")

        # Calculate overall recommendation
        results['recommendation'] = self._calculate_recommendation(results)
        
        return results
    
    def _analyze_fundamentals(self, ticker: str, info: Dict, hist: pd.DataFrame) -> Dict:
        """Analyze fundamental metrics."""
        fundamentals = {
            'revenue_growth': info.get('revenueGrowth', 0),
            'earnings_growth': info.get('earningsGrowth', 0),
            'gross_margin': info.get('grossMargins', 0),
            'pe_ratio': info.get('forwardPE', info.get('trailingPE', 0)),
            'peg_ratio': info.get('pegRatio', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'roe': info.get('returnOnEquity', 0),
            'free_cash_flow': info.get('freeCashflow', 0),
            'analyst_target': info.get('targetMeanPrice', 0),
            'analyst_upside': 0
        }
        
        # Calculate upside
        current_price = hist['close'].iloc[-1]
        if fundamentals['analyst_target'] > 0:
            fundamentals['analyst_upside'] = (
                (fundamentals['analyst_target'] - current_price) / current_price * 100
            )
        
        # Calculate score (0-100) with improved weighting and nuance
        score = 0
        score_breakdown = {}
        
        # 1. Revenue Growth (0-25 points) - Graduated scoring
        rev_growth = fundamentals['revenue_growth']
        if rev_growth < -0.1:  # Declining revenue
            rev_score = 0
        elif rev_growth < 0:  # Slight decline
            rev_score = 5
        elif rev_growth < 0.1:  # Low growth
            rev_score = 10
        elif rev_growth < 0.2:  # Moderate growth
            rev_score = 15
        elif rev_growth < 0.4:  # Good growth
            rev_score = 20
        else:  # Excellent growth (40%+)
            rev_score = min(25, 20 + (rev_growth - 0.4) * 12.5)
        score += rev_score
        score_breakdown['revenue_growth'] = rev_score
        
        # 2. Earnings/Profitability (0-25 points) - Heavy penalty for losses
        earn_growth = fundamentals['earnings_growth']
        pe_ratio = fundamentals['pe_ratio']
        
        if pe_ratio is None: pe_ratio = 0 # Handle None

        if pe_ratio < 0 or pe_ratio == 0:  # Unprofitable
            if earn_growth > 0:  # Improving losses
                earn_score = 5
            else:  # Worsening losses
                earn_score = 0
        elif earn_growth < -0.5:  # Severe earnings decline
            earn_score = 0
        elif earn_growth < -0.2:  # Moderate earnings decline
            earn_score = 5
        elif earn_growth < 0:  # Slight earnings decline
            earn_score = 10
        elif earn_growth < 0.15:  # Moderate earnings growth
            earn_score = 15
        elif earn_growth < 0.3:  # Good earnings growth
            earn_score = 20
        else:  # Excellent earnings growth
            earn_score = 25
        score += earn_score
        score_breakdown['earnings'] = earn_score
        
        # 3. Margins & Quality (0-20 points)
        margin_score = 0
        gm = fundamentals['gross_margin']
        
        # Gross margin scoring (0-10)
        if gm > 0.7:  # Software-like margins
            margin_score += 10
        elif gm > 0.5:  # High margin business
            margin_score += 8
        elif gm > 0.35:  # Decent margins
            margin_score += 6
        elif gm > 0.25:  # Acceptable margins
            margin_score += 4
        elif gm > 0.15:  # Low margins
            margin_score += 2
        
        # ROE scoring (0-10)
        roe = fundamentals['roe']
        if roe is None: roe = 0
        
        if roe > 0.25:  # Excellent ROE
            margin_score += 10
        elif roe > 0.15:  # Good ROE
            margin_score += 7
        elif roe > 0.08:  # Acceptable ROE
            margin_score += 4
        elif roe > 0:  # Positive ROE
            margin_score += 2
        
        score += margin_score
        score_breakdown['quality'] = margin_score
        
        # 4. Valuation (0-15 points) - Context-aware
        val_score = 0
        if 0 < pe_ratio < 15:  # Value territory
            val_score = 15
        elif 15 <= pe_ratio < 25:  # Fair value
            val_score = 12
        elif 25 <= pe_ratio < 35:  # Growth premium
            if rev_growth > 0.25:  # Justified if high growth
                val_score = 10
            else:
                val_score = 5
        elif 35 <= pe_ratio < 50:  # Expensive
            if rev_growth > 0.4:  # Only justified if very high growth
                val_score = 5
            else:
                val_score = 0
        else:  # Very expensive or unprofitable
            val_score = 0
        
        # PEG adjustment
        peg = fundamentals['peg_ratio']
        if peg is not None and 0 < peg < 1 and val_score > 0:
            val_score = min(15, val_score + 3)  # Bonus for good PEG
        
        score += val_score
        score_breakdown['valuation'] = val_score
        
        # 5. Financial Health (0-10 points)
        health_score = 0
        debt_eq = fundamentals['debt_to_equity']
        fcf = fundamentals['free_cash_flow']
        
        if debt_eq is None: debt_eq = 100 # Assume high debt if unknown

        # Debt scoring (0-5)
        if debt_eq < 0.3:  # Low debt
            health_score += 5
        elif debt_eq < 0.6:  # Moderate debt
            health_score += 3
        elif debt_eq < 1.0:  # Acceptable debt
            health_score += 1
        
        # Cash flow scoring (0-5)
        if fcf is not None:
            if fcf > 0:
                health_score += 5
            elif fcf > -100000000:  # Small cash burn
                health_score += 2
        
        score += health_score
        score_breakdown['financial_health'] = health_score
        
        # 6. Analyst Sentiment (0-5 points)
        upside = fundamentals['analyst_upside']
        if upside > 50:
            analyst_score = 5
        elif upside > 30:
            analyst_score = 4
        elif upside > 15:
            analyst_score = 3
        elif upside > 5:
            analyst_score = 1
        else:
            analyst_score = 0
        score += analyst_score
        score_breakdown['analyst_view'] = analyst_score
        
        # Store breakdown for transparency
        fundamentals['score'] = min(100, score)  # Cap at 100
        fundamentals['score_breakdown'] = score_breakdown
        
        return fundamentals
    
    def _analyze_intraday(self, ticker: str, hist: pd.DataFrame) -> Dict:
        """Analyze intraday trading signals."""
        # Simple signal detection based on recent price action
        signals = {
            'has_signal': False,
            'signal_type': None,
            'strength': 'weak'
        }
        
        if len(hist) < 5:
            return signals
        
        # Ensure we use lowercase columns (DataFetcher standard)
        # Check for gap
        today_open = hist['open'].iloc[-1]
        yesterday_close = hist['close'].iloc[-2]
        gap_pct = (today_open - yesterday_close) / yesterday_close * 100
        
        # Check for momentum
        five_day_return = (hist['close'].iloc[-1] - hist['close'].iloc[-5]) / hist['close'].iloc[-5] * 100
        
        # Check volume surge
        recent_volume = hist['volume'].iloc[-5:].mean()
        avg_volume = hist['volume'].iloc[:-5].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Detect signals
        if abs(gap_pct) > 2 and volume_ratio > 1.5:
            signals['has_signal'] = True
            signals['signal_type'] = 'Gap continuation' if gap_pct > 0 else 'Gap fade'
            signals['strength'] = 'strong' if abs(gap_pct) > 4 else 'moderate'
            signals['gap_pct'] = gap_pct
            
        elif abs(five_day_return) > 10 and volume_ratio > 1.2:
            signals['has_signal'] = True
            signals['signal_type'] = 'Momentum' if five_day_return > 0 else 'Reversal'
            signals['strength'] = 'strong' if abs(five_day_return) > 15 else 'moderate'
            signals['momentum_pct'] = five_day_return
        
        signals['volume_ratio'] = volume_ratio
        
        return signals
    
    def _analyze_day_trading(self, ticker: str, info: Dict, hist: pd.DataFrame) -> Dict:
        """Analyze day trading suitability."""
        # Calculate ATR
        high_low = hist['high'] - hist['low']
        high_close = np.abs(hist['high'] - hist['close'].shift())
        low_close = np.abs(hist['low'] - hist['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        # Average volume
        avg_volume = hist['volume'].rolling(20).mean().iloc[-1]
        
        # Float
        shares_float = info.get('floatShares', info.get('sharesOutstanding', 0))
        
        # Determine suitability
        suitable = False
        reason = []
        
        if avg_volume < 1_000_000:
            reason.append("Low volume")
        if atr < 0.5:
            reason.append("Low volatility")
        if shares_float > 1_000_000_000:
            reason.append("Large float")
        
        if not reason:
            suitable = True
        
        return {
            'suitable': suitable,
            'atr': atr,
            'avg_volume': avg_volume,
            'float': shares_float,
            'reason': ', '.join(reason) if reason else 'All criteria met'
        }
    
    def _parse_leaps_results(self, leaps_output: Dict) -> Dict:
        """Parse LEAPS analysis output dictionary."""
        results = {
            'available': False,
            'expiry_count': 0,
            'recommendation': 'N/A',
            'score': 0,
            'optimal_strike': None,
            'optimal_expiry': None,
            'expected_return': None
        }
        
        if not leaps_output:
            return results
        
        # Check if LEAPS are available
        option_chain = leaps_output.get('option_chain', {})
        if option_chain.get('leaps_available'):
            results['available'] = True
            results['expiry_count'] = option_chain.get('total_leaps_expiries', 0)
        
        # Extract score
        results['score'] = leaps_output.get('systematic_score', 0)
        
        # Extract recommendation
        verdict = leaps_output.get('verdict', '')
        if 'BUY' in verdict:
            results['recommendation'] = 'BUY'
        elif 'HOLD' in verdict:
            results['recommendation'] = 'HOLD'
        elif 'AVOID' in verdict or 'SELL' in verdict:
            results['recommendation'] = 'AVOID'
        
        # Extract enhanced strategy details
        enhanced_strategy = leaps_output.get('enhanced_strategy', {})
        results['optimal_strike'] = enhanced_strategy.get('strike')
        results['optimal_expiry'] = enhanced_strategy.get('expiry')
        results['expected_return'] = enhanced_strategy.get('expected_return')
        
        return results
    
    def _calculate_recommendation(self, results: Dict) -> Dict:
        """Calculate overall recommendation based on all analyses."""
        rec = {
            'action': 'HOLD',
            'confidence': 'low',
            'strategy': 'none',
            'reasoning': []
        }
        
        analyses = results.get('analyses', {})
        
        # Check fundamentals
        fund_score = analyses.get('fundamentals', {}).get('score', 0)
        if fund_score >= 70:
            rec['reasoning'].append(f"Strong fundamentals (score: {fund_score})")
        elif fund_score <= 30:
            rec['reasoning'].append(f"Weak fundamentals (score: {fund_score})")
        
        # Check LEAPS
        if analyses.get('leaps', {}).get('available') and analyses.get('leaps', {}).get('recommendation') == 'BUY':
            rec['reasoning'].append("LEAPS opportunity identified")
            rec['strategy'] = 'leaps'
        
        # Check intraday signals
        if analyses.get('intraday', {}).get('has_signal'):
            signal_type = analyses.get('intraday', {}).get('signal_type')
            rec['reasoning'].append(f"Intraday {signal_type} signal")
            if rec['strategy'] == 'none':
                rec['strategy'] = 'intraday'
        
        # Check day trading
        if analyses.get('day_trade', {}).get('suitable'):
            rec['reasoning'].append("Suitable for day trading")
            if rec['strategy'] == 'none':
                rec['strategy'] = 'day_trade'
        
        # Check Sector
        sector_score = analyses.get('sector_rotation', {}).get('score', 0)
        sector_status = analyses.get('sector_rotation', {}).get('status', '')
        
        if sector_status == 'LEADING' or sector_score > 80:
             rec['reasoning'].append(f"Sector is {sector_status} ({sector_score})")
        
        # Check Whale Flow
        whale_status = analyses.get('whale_alert', {}).get('status', '')
        if whale_status == 'ACCUMULATION' or whale_status == 'BULLISH FLOW':
             rec['reasoning'].append("Institutional Accumulation detected")

        # Determine action and confidence
        positive_factors = sum([
            fund_score >= 70,
            analyses.get('leaps', {}).get('recommendation') == 'BUY',
            analyses.get('intraday', {}).get('has_signal', False),
            analyses.get('day_trade', {}).get('suitable', False),
            sector_score > 80,
            whale_status in ['ACCUMULATION', 'BULLISH FLOW']
        ])
        
        if positive_factors >= 3:
            rec['action'] = 'BUY'
            rec['confidence'] = 'high'
        elif positive_factors == 2:
            rec['action'] = 'BUY'
            rec['confidence'] = 'medium'
        elif positive_factors == 1:
            rec['action'] = 'HOLD'
            rec['confidence'] = 'medium'
        else:
            rec['action'] = 'AVOID'
            rec['confidence'] = 'high'
        
        return rec
    
    def screen_stocks(self, screen_type: str = 'growth', universe: List[str] = None) -> pd.DataFrame:
        """
        Screen stocks based on criteria.
        
        Args:
            screen_type: One of ['growth', 'value', 'momentum', 'leaps', 'day_trade']
            universe: List of tickers to screen (if None, uses predefined universe)
        
        Returns:
            DataFrame with screening results
        """
        # Define default universe if not provided
        if universe is None:
            # Use liquid universe as default
            universe = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 
                'NFLX', 'COIN', 'PLTR', 'SNOW', 'CRWD', 'ZS', 'DDOG', 'NET',
                'GME', 'AMC', 'SOFI', 'HOOD', 'RIVN', 'LCID', 'XOM', 'CVX',
                'SLB', 'HAL', 'OXY', 'MPC', 'MRNA', 'BNTX', 'NVAX', 'REGN'
            ]
        
        print(f"\nScreening {len(universe)} stocks for {screen_type} opportunities...")
        
        results = []
        for ticker in universe:
            try:
                # Run appropriate analysis based on screen type
                if screen_type in ['growth', 'value']:
                    analysis = self.analyze_ticker(ticker, ['fundamentals'])
                elif screen_type == 'momentum':
                    analysis = self.analyze_ticker(ticker, ['intraday'])
                elif screen_type == 'leaps':
                    analysis = self.analyze_ticker(ticker, ['fundamentals', 'leaps'])
                elif screen_type == 'day_trade':
                    analysis = self.analyze_ticker(ticker, ['intraday', 'day_trade'])
                else:
                    analysis = self.analyze_ticker(ticker)  # Run all
                
                # Extract key metrics for screening
                result = {
                    'ticker': ticker,
                    'company': analysis.get('company_name', ticker),
                    'price': analysis.get('current_price', 0),
                    'market_cap': analysis.get('market_cap', 0) / 1e9,  # In billions
                }
                
                # Add screen-specific metrics
                if screen_type == 'growth':
                    fund = analysis['analyses'].get('fundamentals', {})
                    result['revenue_growth'] = fund.get('revenue_growth', 0) * 100
                    result['earnings_growth'] = fund.get('earnings_growth', 0) * 100
                    result['score'] = fund.get('score', 0)
                    
                elif screen_type == 'value':
                    fund = analysis['analyses'].get('fundamentals', {})
                    result['pe_ratio'] = fund.get('pe_ratio', 0)
                    result['peg_ratio'] = fund.get('peg_ratio', 0)
                    result['analyst_upside'] = fund.get('analyst_upside', 0)
                    result['score'] = fund.get('score', 0)
                    
                elif screen_type == 'momentum':
                    intra = analysis['analyses'].get('intraday', {})
                    result['has_signal'] = intra.get('has_signal', False)
                    result['signal_type'] = intra.get('signal_type', 'None')
                    result['strength'] = intra.get('strength', 'None')
                    
                elif screen_type == 'leaps':
                    leaps = analysis['analyses'].get('leaps', {})
                    result['leaps_available'] = leaps.get('available', False)
                    result['leaps_recommendation'] = leaps.get('recommendation', 'N/A')
                    result['fundamental_score'] = analysis['analyses'].get('fundamentals', {}).get('score', 0)
                    
                elif screen_type == 'day_trade':
                    dt = analysis['analyses'].get('day_trade', {})
                    intra = analysis['analyses'].get('intraday', {})
                    result['suitable'] = dt.get('suitable', False)
                    result['atr'] = dt.get('atr', 0)
                    result['has_signal'] = intra.get('has_signal', False)
                
                results.append(result)
                
            except Exception as e:
                print(f"  Error analyzing {ticker}: {str(e)}")
                continue
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(results)
        
        # Sort based on screen type
        if screen_type == 'growth':
            df = df.sort_values('score', ascending=False)
        elif screen_type == 'value':
            df = df[df['pe_ratio'] > 0].sort_values('analyst_upside', ascending=False)
        elif screen_type == 'momentum':
            df = df[df['has_signal'] == True].sort_values('ticker')
        elif screen_type == 'leaps':
            df = df[df['leaps_available'] == True].sort_values('fundamental_score', ascending=False)
        elif screen_type == 'day_trade':
            df = df[df['suitable'] == True].sort_values('atr', ascending=False)
        
        return df
    
    def _get_sector_etf(self, sector_name: str) -> str:
        """Map Yahoo Finance sector name to ETF ticker."""
        mapping = {
            'Technology': 'XLK',
            'Financial Services': 'XLF',
            'Financials': 'XLF',
            'Healthcare': 'XLV',
            'Consumer Cyclical': 'XLY',
            'Consumer Defensive': 'XLP',
            'Energy': 'XLE',
            'Industrials': 'XLI',
            'Communication Services': 'XLC',
            'Basic Materials': 'XLB',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE'
        }
        # Handle minor variations or return SPY as fallback
        return mapping.get(sector_name, 'SPY')

    def _analyze_sector_status(self, sector_name: str) -> Dict:
        """Check if the sector is leading or lagging."""
        etf = self._get_sector_etf(sector_name)
        if etf == 'SPY':
            return {'status': 'Neutral', 'score': 50, 'etf': etf}
            
        # Run analysis (cache result in instance)
        if not hasattr(self, '_sector_results'):
            # print("  Analyzing sector rotation...")
            self._sector_results = self.sector_analyzer.analyze_sectors()
            
        # Find our sector in rankings
        for rank in self._sector_results.get('rankings', []):
            if rank['ticker'] == etf:
                return rank
                
        return {'status': 'Unknown', 'score': 50, 'etf': etf}

    def _get_market_regime(self) -> Dict:
        """Get cached market regime."""
        if not self._regime_cache:
            # print("  Analyzing market regime...")
            self._regime_cache = self.regime_analyzer.analyze_regime()
        return self._regime_cache

    def _generate_tactical_plan(self, ticker: str, hist: pd.DataFrame) -> Dict:
        """Generate specific trade levels for the next session."""
        if hist.empty or len(hist) < 20:
            return {}
            
        # Prepare Data
        hist = hist.copy()
        hist['date'] = pd.to_datetime(hist['date'])
        hist['trading_day'] = hist['date'].dt.date
        trading_days = sorted(hist['trading_day'].unique())
        
        if len(trading_days) < 2:
            return {}
            
        today = trading_days[-1]
        yesterday = trading_days[-2]
        
        today_data = hist[hist['trading_day'] == today]
        yesterday_data = hist[hist['trading_day'] == yesterday]
        prev_close = yesterday_data['close'].iloc[-1]
        
        # Run Strategies
        plans = []
        
        # 1. Volatility Squeeze (High Quality Breakout)
        sqz = StrategyLibrary.volatility_squeeze(today_data)
        if sqz: plans.append(sqz)
        
        # 2. Gap & Go (Trend)
        gap = StrategyLibrary.gap_and_go(today_data, prev_close)
        if gap: plans.append(gap)
        
        # 3. RSI Reversion (Counter-Trend)
        rsi = StrategyLibrary.rsi_reversion(today_data, prev_close)
        if rsi: plans.append(rsi)
        
        if not plans:
            return {'action': 'WAIT', 'reason': 'No valid technical setup currently'}
            
        # Return the first valid plan found (Priority: Squeeze > Gap > RSI)
        return plans[0]

    def save_results(self, results: List[Dict], filename: str = None):
        """Save analysis results to JSON file."""
        if filename is None:
            filename = f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = f"data/output/{filename}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_path}")
        
        # Also save summary CSV
        summary_data = []
        for r in results:
            summary = {
                'ticker': r['ticker'],
                'company': r.get('company_name', ''),
                'price': r.get('current_price', 0),
                'recommendation': r.get('recommendation', {}).get('action', ''),
                'strategy': r.get('recommendation', {}).get('strategy', ''),
                'confidence': r.get('recommendation', {}).get('confidence', '')
            }
        
        summary_df = pd.DataFrame(summary_data)
        csv_path = output_path.replace('.json', '_summary.csv')
        summary_df.to_csv(csv_path, index=False)
        print(f"Summary saved to: {csv_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Unified Investment Analyzer - All strategies in one place',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze single ticker
    python unified_analyzer.py --ticker NVDA
    
    # Analyze multiple tickers
    python unified_analyzer.py --tickers NVDA,TSLA,PLTR
    
    # Screen for growth stocks
    python unified_analyzer.py --screen growth --top 10
    
    # Screen for LEAPS opportunities
    python unified_analyzer.py --screen leaps --universe russell1000
    
    # Analyze tickers from file
    python unified_analyzer.py --file tickers.txt
    
    # Run specific analysis types
    python unified_analyzer.py --ticker AAPL --types fundamentals,leaps
        """
    )
    
    # Input options
    parser.add_argument('--ticker', help='Single ticker to analyze')
    parser.add_argument('--tickers', help='Comma-separated list of tickers')
    parser.add_argument('--file', help='File containing list of tickers (one per line)')
    parser.add_argument('--screen', choices=['growth', 'value', 'momentum', 'leaps', 'day_trade'],
                       help='Run stock screener')
    
    # Analysis options
    parser.add_argument('--types', help='Comma-separated analysis types: fundamentals,leaps,intraday,day_trade')
    parser.add_argument('--universe', choices=['liquid', 'russell1000', 'russell2000', 'custom'],
                       default='liquid', help='Universe for screening')
    parser.add_argument('--top', type=int, default=10, help='Number of top results to show')
    
    # Output options
    parser.add_argument('--save', action='store_true', help='Save results to file')
    parser.add_argument('--output', help='Output filename (default: auto-generated)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not any([args.ticker, args.tickers, args.file, args.screen]):
        parser.error('Must specify --ticker, --tickers, --file, or --screen')
    
    # Initialize analyzer
    analyzer = UnifiedAnalyzer()
    
    # Determine tickers to analyze
    tickers_to_analyze = []
    
    if args.ticker:
        tickers_to_analyze = [args.ticker.upper()]
    elif args.tickers:
        tickers_to_analyze = [t.strip().upper() for t in args.tickers.split(',')]
    elif args.file:
        with open(args.file, 'r') as f:
            tickers_to_analyze = [line.strip().upper() for line in f if line.strip()]
    
    # Parse analysis types
    analysis_types = None
    if args.types:
        if args.types.strip().lower() == 'all':
            analysis_types = ['fundamentals', 'leaps', 'intraday', 'day_trade']
        else:
            analysis_types = [t.strip() for t in args.types.split(',')]
    
    # Run analysis or screening
    if args.screen:
        # Load appropriate universe
        universe = None
        if args.universe == 'russell1000':
            russell_path = 'data/russell1000_tickers.csv'
            if os.path.exists(russell_path):
                universe = pd.read_csv(russell_path)['ticker'].tolist()
        elif args.universe == 'russell2000':
            russell_path = 'data/russell2000_tickers.csv'
            if os.path.exists(russell_path):
                universe = pd.read_csv(russell_path)['ticker'].tolist()
        elif args.universe == 'custom':
            custom_path = 'data/custom_universe.csv'
            if os.path.exists(custom_path):
                universe = pd.read_csv(custom_path)['ticker'].tolist()
        
        # Run screening
        results_df = analyzer.screen_stocks(args.screen, universe)
        
        # Display top results
        print(f"\nTop {args.top} {args.screen} opportunities:")
        print("=" * 80)
        print(results_df.head(args.top).to_string(index=False))
        
        if args.save:
            output_file = args.output or f"screen_{args.screen}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path = f"data/output/{output_file}"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            results_df.to_csv(output_path, index=False)
            print(f"\nScreening results saved to: {output_path}")
    
    else:
        # Run individual ticker analysis
        all_results = []
        
        for ticker in tickers_to_analyze:
            results = analyzer.analyze_ticker(ticker, analysis_types)
            all_results.append(results)
            
            # Print recommendation
            rec = results.get('recommendation', {})
            print(f"\n{'='*60}")
            print(f"RECOMMENDATION: {rec.get('action', 'HOLD')} "
            f"(Confidence: {rec.get('confidence', 'low')})")
            if rec.get('strategy') != 'none':
                print(f"Strategy: {rec.get('strategy').upper()}")
            if rec.get('reasoning'):
                print(f"Reasoning: {', '.join(rec['reasoning'])}")
            print('='*60)
        
        # Save results if requested
        if args.save:
            analyzer.save_results(all_results, args.output)
        
        # Print summary if multiple tickers
        if len(all_results) > 1:
            print(f"\n{'='*80}")
            print("SUMMARY - All Tickers")
            print('='*80)
            print(f"{'Ticker':<10} {'Action':<10} {'Strategy':<15} {'Confidence':<10} {'Price':<10}")
            print('-'*80)
            
            for r in all_results:
                rec = r.get('recommendation', {})
                print(f"{r['ticker']:<10} {rec.get('action', 'HOLD'):<10} "
                      f"{rec.get('strategy', 'none'):<15} {rec.get('confidence', 'low'):<10} "
                      f"${r.get('current_price', 0):<10.2f}")


if __name__ == "__main__":
    main()
