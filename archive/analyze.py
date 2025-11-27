#!/usr/bin/env python3
"""
Intelligent Cascading Analysis
================================

Chains existing scripts together intelligently:
1. LEAPS finds fundamentally strong stocks
2. Scanner checks technical setup (gap, momentum, VWAP)
3. Day bot evaluates for gap trading
4. Combined recommendation

Uses existing scripts - no duplication.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import subprocess
import json
import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
from ib_insync import IB, Stock

# Import existing components
from leaps.complete_leaps_system import CompleteLEAPSSystem
from alpha_lab.intraday_signals import IntradaySignalGenerator
from alpha_lab.real_fundamentals import RealFundamentalAnalyzer
from alpha_lab.elliott_wave import analyze_elliott_wave

class IntelligentAnalyzer:
    """Chains existing analysis scripts together."""
    
    def __init__(self):
        self.ib = None
        self.leaps_system = None
        self.scanner = None
        
    def connect_ibkr(self):
        """Connect to IBKR if available."""
        try:
            import yaml
            cfg = yaml.safe_load(open('configs/ibkr.yaml'))
            self.ib = IB()
            self.ib.connect(cfg['host'], cfg['port'], clientId=cfg['client_id']+50, timeout=10)
            print("✓ Connected to IBKR")
            return True
        except Exception as e:
            print(f"⚠ IBKR not available: {e}")
            return False
    
    def analyze_fundamentals(self, ticker):
        """Run LEAPS analysis for fundamental score."""
        print(f"\n{'='*80}")
        print(f"STEP 1/3: FUNDAMENTAL ANALYSIS (LEAPS System)")
        print(f"{'='*80}\n")
        
        try:
            # Use existing LEAPS system
            if not self.leaps_system:
                # Use ALL features: GPT, IBKR, FinBERT
                self.leaps_system = CompleteLEAPSSystem(use_gpt=True, try_ibkr=True, use_finbert=True)
            
            result = self.leaps_system.complete_systematic_analysis(ticker)
            
            # Extract key metrics - use correct keys from result
            fundamental_score = result.get('final_score', 0)
            
            # Get recommendation from GPT analysis or fundamentals
            gpt_analysis = result.get('gpt_analysis', {})
            recommendation = gpt_analysis.get('recommendation', 'UNKNOWN')
            
            # Get price targets from GPT or fundamentals
            fundamentals = result.get('fundamentals', {})
            price_target_12m = fundamentals.get('analyst_target', 0)
            
            # Calculate 24-month target (rough estimate)
            if price_target_12m > 0:
                current_price = fundamentals.get('current_price', 0)
                if current_price > 0:
                    upside_12m = (price_target_12m - current_price) / current_price
                    price_target_24m = current_price * (1 + upside_12m * 1.5)
                else:
                    price_target_24m = price_target_12m * 1.3
            else:
                price_target_24m = 0
            
            print(f"\n✓ Fundamental Score: {fundamental_score}/100")
            print(f"  Recommendation: {recommendation}")
            print(f"  12-Month Target: ${price_target_12m:.2f}")
            if price_target_24m > 0:
                print(f"  24-Month Target: ${price_target_24m:.2f}")
            
            # Show GPT insights if available
            if gpt_analysis and 'key_catalysts' in gpt_analysis:
                catalysts = gpt_analysis.get('key_catalysts', [])
                if catalysts:
                    print(f"\n  Key Catalysts:")
                    for catalyst in catalysts[:3]:
                        print(f"    • {catalyst}")
            
            if gpt_analysis and 'key_risks' in gpt_analysis:
                risks = gpt_analysis.get('key_risks', [])
                if risks:
                    print(f"\n  Key Risks:")
                    for risk in risks[:3]:
                        print(f"    • {risk}")
            
            return {
                'score': fundamental_score,
                'recommendation': recommendation,
                'price_target_12m': price_target_12m,
                'price_target_24m': price_target_24m,
                'strong': fundamental_score >= 65,  # 65+ is strong
                'moderate': 50 <= fundamental_score < 65,
                'weak': fundamental_score < 50,
                'full_result': result
            }
        except Exception as e:
            print(f"✗ Fundamental analysis failed: {e}")
            return {'score': 0, 'strong': False, 'weak': True}
    
    def analyze_technical(self, ticker):
        """Run scanner for technical signals."""
        print(f"\n{'='*80}")
        print(f"STEP 2/3: TECHNICAL ANALYSIS (Intraday Scanner)")
        print(f"{'='*80}\n")
        
        try:
            # Use existing scanner
            if not self.scanner and self.ib:
                self.scanner = IntradaySignalGenerator(self.ib)
            
            if not self.scanner:
                print("⚠ Scanner needs IBKR connection")
                return self._basic_technical(ticker)
            
            # Check for signals
            gap_signal = self.scanner.detect_opening_gap(ticker)
            momentum_signal = self.scanner.detect_momentum_breakout(ticker)
            vwap_signal = self.scanner.detect_vwap_reversion(ticker)
            
            signals = []
            best_confidence = 0
            best_signal = None
            
            if gap_signal and gap_signal.get('confidence', 0) > 0:
                signals.append(gap_signal)
                if gap_signal['confidence'] > best_confidence:
                    best_confidence = gap_signal['confidence']
                    best_signal = gap_signal
            
            if momentum_signal and momentum_signal.get('confidence', 0) > 0:
                signals.append(momentum_signal)
                if momentum_signal['confidence'] > best_confidence:
                    best_confidence = momentum_signal['confidence']
                    best_signal = momentum_signal
            
            if vwap_signal and vwap_signal.get('confidence', 0) > 0:
                signals.append(vwap_signal)
                if vwap_signal['confidence'] > best_confidence:
                    best_confidence = vwap_signal['confidence']
                    best_signal = vwap_signal
            
            if best_signal:
                print(f"\n✓ Technical Signal: {best_signal['signal']}")
                print(f"  Confidence: {best_confidence:.1f}/100")
                print(f"  Price: ${best_signal['price']:.2f}")
            else:
                print("\n○ No strong technical signals")
            
            return {
                'has_signal': len(signals) > 0,
                'best_signal': best_signal,
                'confidence': best_confidence,
                'signals': signals,
                'strong': best_confidence >= 60,
                'weak': best_confidence < 40
            }
        except Exception as e:
            print(f"✗ Technical analysis failed: {e}")
            return self._basic_technical(ticker)
    
    def _basic_technical(self, ticker):
        """Basic technical check without IBKR."""
        try:
            # Use yfinance for basic check
            stock = yf.Ticker(ticker)
            hist = stock.history(period='5d', interval='1d')
            
            if len(hist) < 2:
                return {'has_signal': False, 'strong': False, 'weak': True}
            
            # Check for gap
            prev_close = hist['Close'].iloc[-2]
            today_open = hist['Open'].iloc[-1]
            gap_pct = (today_open - prev_close) / prev_close * 100
            
            # Check momentum
            change_5d = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
            
            print(f"\n○ Basic Technical Check:")
            print(f"  Gap: {gap_pct:+.2f}%")
            print(f"  5-Day Change: {change_5d:+.2f}%")
            
            strong = abs(gap_pct) > 2 or change_5d > 5
            
            return {
                'has_signal': strong,
                'gap_pct': gap_pct,
                'momentum': change_5d,
                'strong': strong,
                'weak': not strong
            }
        except Exception as e:
            print(f"✗ Basic technical failed: {e}")
            return {'has_signal': False, 'strong': False, 'weak': True}
    
    def evaluate_for_daytrading(self, ticker, fundamental, technical):
        """Check if suitable for day trading bot."""
        print(f"\n{'='*80}")
        print(f"STEP 3/3: DAY TRADING EVALUATION")
        print(f"{'='*80}\n")
        
        # Day trading criteria (from day_trading_bot.py config)
        suitable = False
        reasons = []
        
        # Check gap
        has_gap = technical.get('gap_pct', 0) != 0 and abs(technical.get('gap_pct', 0)) >= 1.0
        if has_gap:
            reasons.append(f"✓ Gap: {technical.get('gap_pct', 0):+.2f}%")
        else:
            reasons.append("✗ No significant gap")
        
        # Check if has signal
        has_signal = technical.get('has_signal', False)
        if has_signal:
            reasons.append(f"✓ Technical signal present")
        else:
            reasons.append("✗ No technical setup")
        
        # Check fundamentals (catalyst)
        fund_score = fundamental.get('score', 0)
        has_catalyst = fundamental.get('strong', False) or fundamental.get('moderate', False)
        if fundamental.get('strong', False):
            reasons.append(f"✓ Strong fundamentals (score: {fund_score})")
        elif fundamental.get('moderate', False):
            reasons.append(f"○ Moderate fundamentals (score: {fund_score})")
        else:
            reasons.append(f"✗ Weak fundamentals (score: {fund_score})")
        
        # Decision
        suitable = has_gap and has_signal
        
        print("Day Trading Suitability:")
        for reason in reasons:
            print(f"  {reason}")
        
        if suitable:
            print(f"\n✓✓✓ SUITABLE FOR DAY TRADING")
        else:
            print(f"\n○○○ NOT IDEAL FOR DAY TRADING")
        
        return {
            'suitable': suitable,
            'has_gap': has_gap,
            'has_signal': has_signal,
            'has_catalyst': has_catalyst,
            'reasons': reasons
        }
    
    def generate_recommendation(self, ticker, fundamental, technical, daytrading):
        """Generate final combined recommendation."""
        print(f"\n{'='*80}")
        print(f"COMBINED RECOMMENDATION: {ticker}")
        print(f"{'='*80}\n")
        
        # Determine strategy based on strengths
        strategies = []
        
        # LEAPS recommendation
        if fundamental['strong']:
            strategies.append({
                'strategy': 'LEAPS',
                'timeframe': '12-24 months',
                'reason': f"Strong fundamentals (score: {fundamental['score']}/100)",
                'action': f"Run: python scripts/run_leaps_analysis.py {ticker}"
            })
        
        # Day trading recommendation
        if daytrading['suitable']:
            strategies.append({
                'strategy': 'Day Trading',
                'timeframe': '30 minutes - 4 hours',
                'reason': f"Gap + technical setup",
                'action': f"Add to day bot watchlist, monitor for VWAP entry"
            })
        elif technical['has_signal']:
            strategies.append({
                'strategy': 'Intraday Swing',
                'timeframe': '2-8 hours',
                'reason': f"Technical signal: {technical.get('best_signal', {}).get('signal', 'momentum')}",
                'action': f"Manual entry on scanner signal"
            })
        
        # Combination plays
        strong_fund = fundamental.get('strong', False)
        moderate_fund = fundamental.get('moderate', False)
        strong_tech = technical.get('strong', False)
        
        if strong_fund and strong_tech:
            print("🎯 BEST SETUP: Strong fundamentals + Strong technical")
            print("   Recommended: Day trade for quick profit, hold LEAPS for long-term\n")
        elif (strong_fund or moderate_fund) and not strong_tech:
            print("📊 PATIENT SETUP: Good fundamentals, weak technicals")
            print("   Recommended: Enter LEAPS now, wait for technical entry to day trade\n")
        elif not strong_fund and not moderate_fund and strong_tech:
            print("⚡ QUICK TRADE: Weak fundamentals, strong technicals")
            print("   Recommended: Day trade only, exit by close, no LEAPS\n")
        else:
            print("⏸ PASS: Not compelling on either dimension")
            print("   Recommended: Skip this ticker\n")
        
        # Print strategies
        if strategies:
            print("RECOMMENDED STRATEGIES:\n")
            for i, strat in enumerate(strategies, 1):
                print(f"{i}. {strat['strategy']} ({strat['timeframe']})")
                print(f"   Reason: {strat['reason']}")
                print(f"   Action: {strat['action']}\n")
        else:
            print("NO STRATEGIES RECOMMENDED - SKIP\n")
        
        return strategies
    
    def analyze_advanced_fundamentals(self, ticker):
        """Run REAL advanced fundamental metrics with actual calculations."""
        print(f"\n{'='*80}")
        print(f"STEP 1b: REAL FUNDAMENTAL ANALYSIS (ROIC, Piotroski)")
        print(f"{'='*80}\n")
        
        try:
            # Use real analyzer
            analyzer = RealFundamentalAnalyzer(ticker)
            
            # Calculate ROIC
            roic = analyzer.calculate_roic()
            
            # Calculate Piotroski
            piotroski = analyzer.calculate_piotroski_fscore()
            
            # Display
            print(f"ROIC:")
            if not np.isnan(roic.get('value', np.nan)):
                print(f"  {roic['value']:.1f}% ({roic['rating']})")
                print(f"  {'✓ Excellent' if roic['value'] > 20 else '✓ Good' if roic['value'] > 15 else '○ Fair' if roic['value'] > 10 else '✗ Poor'}")
            else:
                print(f"  Not available ({roic.get('error', 'unknown')})")
            
            print(f"\nPiotroski F-Score:")
            print(f"  {piotroski['score']}/9 ({piotroski['rating']})")
            
            if 'breakdown' in piotroski:
                b = piotroski['breakdown']
                prof_score = sum([b.get('positive_roa', False), 
                                 b.get('positive_ocf', False),
                                 b.get('increasing_roa', False),
                                 b.get('quality_earnings', False)])
                print(f"  Profitability: {prof_score}/4")
                print(f"  Financial Health: {piotroski['score'] - prof_score - 2 if piotroski['score'] > prof_score else 0}/3")
                print(f"  Efficiency: 2 if needed")
            
            # Combined assessment
            strong_quality = piotroski['score'] >= 7 and roic.get('value', 0) > 15
            good_quality = piotroski['score'] >= 6 or roic.get('value', 0) > 12
            
            print(f"\nQuality Assessment:")
            if strong_quality:
                print(f"  ✓✓ EXCELLENT - High quality across metrics")
            elif good_quality:
                print(f"  ✓ GOOD - Solid fundamentals")
            else:
                print(f"  ○ MODERATE - Mixed quality")
            
            return {
                'roic': roic,
                'piotroski': piotroski,
                'quality_rating': 'excellent' if strong_quality else 'good' if good_quality else 'moderate'
            }
            
        except Exception as e:
            print(f"✗ Real fundamental analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def analyze_elliott_wave_pattern(self, ticker):
        """Run Elliott Wave analysis."""
        print(f"\n{'='*80}")
        print(f"BONUS: ELLIOTT WAVE PATTERN")
        print(f"{'='*80}\n")
        
        try:
            wave = analyze_elliott_wave(ticker, period='6mo')
            
            if wave.get('pattern_found'):
                print(f"✓ Pattern: {wave['pattern_type'].replace('_', ' ').title()}")
                print(f"  Wave 5 Price: ${wave.get('wave_5_price', 0):.2f}")
                print(f"  Interpretation: {wave.get('interpretation', 'N/A')}")
            else:
                print(f"○ No clear pattern ({wave.get('reason', 'unknown')})")
            
            print(f"  Trend: {wave.get('trend', 'unknown').replace('_', ' ').title()}")
            
            return wave
            
        except Exception as e:
            print(f"✗ Elliott Wave analysis failed: {e}")
            return {}
    
    def analyze(self, ticker):
        """Run complete cascading analysis."""
        print(f"\n{'#'*80}")
        print(f"INTELLIGENT CASCADING ANALYSIS: {ticker.upper()}")
        print(f"{'#'*80}\n")
        
        # Step 1: Fundamentals (LEAPS)
        fundamental = self.analyze_fundamentals(ticker)
        
        # Step 1b: Advanced Fundamentals (ROIC, Piotroski, etc.)
        advanced_fund = self.analyze_advanced_fundamentals(ticker)
        
        # Step 2: Technical (Scanner)
        technical = self.analyze_technical(ticker)
        
        # Step 2b: Elliott Wave
        elliott = self.analyze_elliott_wave_pattern(ticker)
        
        # Step 3: Day Trading Fit
        daytrading = self.evaluate_for_daytrading(ticker, fundamental, technical)
        
        # Step 4: Combined Recommendation
        strategies = self.generate_recommendation(ticker, fundamental, technical, daytrading)
        
        # Summary
        summary = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'fundamental': fundamental,
            'advanced_fundamentals': advanced_fund,
            'technical': technical,
            'elliott_wave': elliott,
            'daytrading': daytrading,
            'strategies': strategies
        }
        
        # Save to file
        output_dir = 'data/output'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'{output_dir}/analysis_{ticker}_{timestamp}.json'
        
        # Clean summary for JSON serialization
        clean_summary = {}
        for key, value in summary.items():
            if isinstance(value, dict):
                clean_summary[key] = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                                     for k, v in value.items()}
            else:
                clean_summary[key] = str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
        
        with open(output_file, 'w') as f:
            json.dump(clean_summary, f, indent=2, default=str)
        
        print(f"\nAnalysis saved to: {output_file}")
        
        return summary
    
    def batch_analyze(self, tickers):
        """Analyze multiple tickers."""
        results = []
        
        for ticker in tickers:
            try:
                result = self.analyze(ticker)
                results.append(result)
                print("\n" + "="*80 + "\n")
            except KeyboardInterrupt:
                print("\n\nStopped by user")
                break
            except Exception as e:
                print(f"\n✗ Error analyzing {ticker}: {e}\n")
                continue
        
        # Summary table
        if results:
            print("\n" + "#"*80)
            print("BATCH ANALYSIS SUMMARY")
            print("#"*80 + "\n")
            
            summary_data = []
            for r in results:
                summary_data.append({
                    'Ticker': r['ticker'],
                    'Fund Score': f"{r['fundamental']['score']}/100",
                    'Tech Signal': '✓' if r['technical']['has_signal'] else '✗',
                    'Day Trade': '✓' if r['daytrading']['suitable'] else '✗',
                    'Strategies': len(r['strategies'])
                })
            
            df = pd.DataFrame(summary_data)
            print(df.to_string(index=False))
            print()
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Intelligent Cascading Analysis')
    parser.add_argument('tickers', nargs='+', help='Ticker symbols to analyze')
    parser.add_argument('--no-ibkr', action='store_true', help='Skip IBKR connection')
    args = parser.parse_args()
    
    # Initialize
    analyzer = IntelligentAnalyzer()
    
    # Connect to IBKR if available
    if not args.no_ibkr:
        analyzer.connect_ibkr()
    
    # Analyze
    if len(args.tickers) == 1:
        analyzer.analyze(args.tickers[0])
    else:
        analyzer.batch_analyze(args.tickers)
    
    # Cleanup
    if analyzer.ib and analyzer.ib.isConnected():
        analyzer.ib.disconnect()


if __name__ == "__main__":
    main()

