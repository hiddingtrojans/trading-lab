#!/usr/bin/env python3
"""
Options Greeks Display
======================

Shows key options metrics for LEAPS recommendations:
- Delta: Direction exposure
- Theta: Time decay per day
- IV Percentile: Current IV vs historical
- IV Rank: Current IV position in range

Usage:
    from alpha_lab.options_greeks import OptionsGreeksAnalyzer
    
    greeks = OptionsGreeksAnalyzer()
    data = greeks.analyze_leaps('NVDA')
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import math


class OptionsGreeksAnalyzer:
    """
    Analyzes options Greeks and IV metrics for LEAPS.
    """
    
    def __init__(self):
        self._iv_history_cache: Dict[str, pd.Series] = {}
    
    def _get_option_chain(self, ticker: str) -> Optional[Dict]:
        """Fetch option chain data."""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            # Get expiration dates
            expirations = stock.options
            if not expirations:
                return None
            
            # Filter for LEAPS (>6 months out)
            today = datetime.now()
            leaps_expirations = [
                exp for exp in expirations
                if (datetime.strptime(exp, '%Y-%m-%d') - today).days > 180
            ]
            
            if not leaps_expirations:
                return None
            
            # Get current price
            info = stock.info
            current_price = info.get('currentPrice') or info.get('previousClose', 0)
            
            # Get chain for first LEAPS expiration
            first_leaps = leaps_expirations[0]
            chain = stock.option_chain(first_leaps)
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'expiration': first_leaps,
                'days_to_expiry': (datetime.strptime(first_leaps, '%Y-%m-%d') - today).days,
                'calls': chain.calls,
                'puts': chain.puts,
                'all_expirations': leaps_expirations
            }
            
        except Exception as e:
            print(f"  Error fetching options for {ticker}: {e}")
            return None
    
    def _calculate_iv_percentile(self, ticker: str, current_iv: float) -> Dict:
        """
        Calculate IV percentile and rank.
        
        IV Percentile: % of days IV was lower than current
        IV Rank: (Current - Low) / (High - Low)
        """
        try:
            import yfinance as yf
            
            # Get historical data for IV proxy
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                return {'iv_percentile': 50, 'iv_rank': 50}
            
            # Calculate historical volatility as IV proxy
            returns = hist['Close'].pct_change().dropna()
            rolling_vol = returns.rolling(20).std() * np.sqrt(252) * 100  # Annualized
            rolling_vol = rolling_vol.dropna()
            
            if len(rolling_vol) < 20:
                return {'iv_percentile': 50, 'iv_rank': 50}
            
            # IV Percentile: % of observations below current
            percentile = (rolling_vol < current_iv).sum() / len(rolling_vol) * 100
            
            # IV Rank
            iv_low = rolling_vol.min()
            iv_high = rolling_vol.max()
            iv_range = iv_high - iv_low
            
            if iv_range > 0:
                rank = (current_iv - iv_low) / iv_range * 100
            else:
                rank = 50
            
            return {
                'iv_percentile': percentile,
                'iv_rank': rank,
                'iv_low': iv_low,
                'iv_high': iv_high,
                'iv_current': current_iv
            }
            
        except Exception as e:
            print(f"  Error calculating IV metrics: {e}")
            return {'iv_percentile': 50, 'iv_rank': 50}
    
    def _estimate_greeks(self, option_row: pd.Series, current_price: float, 
                         days_to_expiry: int, is_call: bool) -> Dict:
        """
        Estimate Greeks from option data.
        
        Note: These are approximations. Real Greeks require Black-Scholes model.
        yfinance provides impliedVolatility which we can use.
        """
        strike = option_row['strike']
        iv = option_row.get('impliedVolatility', 0.3) * 100  # Convert to %
        bid = option_row.get('bid', 0)
        ask = option_row.get('ask', 0)
        mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else option_row.get('lastPrice', 0)
        
        # Moneyness
        if is_call:
            moneyness = current_price / strike
            itm = current_price > strike
        else:
            moneyness = strike / current_price
            itm = current_price < strike
        
        # Delta estimation (simplified)
        # ATM options have ~0.50 delta
        # ITM options approach 1.0, OTM approach 0
        if is_call:
            if current_price > strike * 1.1:  # Deep ITM
                delta = 0.85 + (moneyness - 1.1) * 0.5
            elif current_price > strike:  # ITM
                delta = 0.55 + (moneyness - 1.0) * 3
            elif current_price > strike * 0.95:  # Near ATM
                delta = 0.45 + (moneyness - 0.95) * 2
            else:  # OTM
                delta = max(0.05, 0.45 - (0.95 - moneyness) * 2)
        else:
            if current_price < strike * 0.9:  # Deep ITM put
                delta = -0.85 - (1/moneyness - 1.1) * 0.5
            elif current_price < strike:  # ITM put
                delta = -0.55 - (1.0 - 1/moneyness) * 3
            else:  # OTM put
                delta = max(-0.45, -0.05 - (moneyness - 1.0) * 2)
        
        delta = np.clip(delta, -1.0, 1.0)
        
        # Theta estimation (time decay per day)
        # Higher for ATM, lower for ITM/OTM
        # Increases as expiration approaches
        time_factor = 365 / max(days_to_expiry, 1)
        atm_factor = 1 - abs(moneyness - 1.0) * 2
        atm_factor = max(0.2, atm_factor)
        
        # Rough theta estimate
        theta_annual = mid_price * (iv / 100) * atm_factor * 0.5
        theta_daily = -theta_annual / 365
        
        # Gamma (change in delta)
        # Highest for ATM options
        gamma = atm_factor * 0.05 / max(days_to_expiry / 365, 0.1)
        
        # Vega (sensitivity to IV)
        # Higher for longer-dated options
        vega = mid_price * 0.01 * (days_to_expiry / 365) ** 0.5
        
        return {
            'strike': strike,
            'mid_price': round(mid_price, 2),
            'bid': bid,
            'ask': ask,
            'iv': round(iv, 1),
            'delta': round(delta, 2),
            'theta': round(theta_daily, 3),
            'gamma': round(gamma, 4),
            'vega': round(vega, 3),
            'moneyness': round(moneyness, 3),
            'itm': itm,
            'volume': option_row.get('volume', 0),
            'open_interest': option_row.get('openInterest', 0)
        }
    
    def analyze_leaps(self, ticker: str, num_strikes: int = 5) -> Dict:
        """
        Analyze LEAPS options with Greeks.
        
        Args:
            ticker: Stock symbol
            num_strikes: Number of strikes to show around ATM
        
        Returns:
            Dict with Greeks analysis for calls and puts
        """
        chain = self._get_option_chain(ticker)
        
        if chain is None:
            return {'error': 'No LEAPS available', 'ticker': ticker}
        
        current_price = chain['current_price']
        days_to_expiry = chain['days_to_expiry']
        
        # Find ATM strikes
        calls = chain['calls']
        puts = chain['puts']
        
        # Get strikes around ATM
        all_strikes = sorted(calls['strike'].unique())
        atm_idx = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - current_price))
        
        start_idx = max(0, atm_idx - num_strikes // 2)
        end_idx = min(len(all_strikes), start_idx + num_strikes)
        selected_strikes = all_strikes[start_idx:end_idx]
        
        # Analyze calls
        call_greeks = []
        for strike in selected_strikes:
            row = calls[calls['strike'] == strike].iloc[0]
            greeks = self._estimate_greeks(row, current_price, days_to_expiry, is_call=True)
            call_greeks.append(greeks)
        
        # Analyze puts
        put_greeks = []
        for strike in selected_strikes:
            row = puts[puts['strike'] == strike].iloc[0]
            greeks = self._estimate_greeks(row, current_price, days_to_expiry, is_call=False)
            put_greeks.append(greeks)
        
        # Get ATM IV for percentile calculation
        atm_call = calls.iloc[(calls['strike'] - current_price).abs().argmin()]
        atm_iv = atm_call.get('impliedVolatility', 0.3) * 100
        
        iv_metrics = self._calculate_iv_percentile(ticker, atm_iv)
        
        return {
            'ticker': ticker,
            'current_price': current_price,
            'expiration': chain['expiration'],
            'days_to_expiry': days_to_expiry,
            'all_expirations': chain['all_expirations'],
            'atm_iv': round(atm_iv, 1),
            'iv_percentile': round(iv_metrics['iv_percentile'], 1),
            'iv_rank': round(iv_metrics['iv_rank'], 1),
            'iv_low': round(iv_metrics.get('iv_low', 0), 1),
            'iv_high': round(iv_metrics.get('iv_high', 0), 1),
            'calls': call_greeks,
            'puts': put_greeks
        }
    
    def get_recommended_strike(self, analysis: Dict, strategy: str = "moderate") -> Dict:
        """
        Get recommended strike based on strategy.
        
        Strategies:
            - conservative: 0.70-0.80 delta (deep ITM)
            - moderate: 0.50-0.70 delta (ATM to slight ITM)
            - aggressive: 0.30-0.50 delta (OTM)
        """
        if 'error' in analysis:
            return analysis
        
        calls = analysis['calls']
        
        delta_ranges = {
            'conservative': (0.70, 0.90),
            'moderate': (0.50, 0.70),
            'aggressive': (0.30, 0.50)
        }
        
        target_range = delta_ranges.get(strategy, delta_ranges['moderate'])
        
        # Find best match
        best_match = None
        for call in calls:
            if target_range[0] <= call['delta'] <= target_range[1]:
                if best_match is None or abs(call['delta'] - sum(target_range)/2) < abs(best_match['delta'] - sum(target_range)/2):
                    best_match = call
        
        if best_match is None:
            # Fallback to closest
            best_match = min(calls, key=lambda c: abs(c['delta'] - sum(target_range)/2))
        
        return {
            'strategy': strategy,
            'recommended': best_match,
            'reasoning': f"Delta {best_match['delta']:.2f} in {strategy} range {target_range}"
        }
    
    def print_analysis(self, ticker: str):
        """Print formatted Greeks analysis."""
        analysis = self.analyze_leaps(ticker)
        
        if 'error' in analysis:
            print(f"\n{analysis['error']}")
            return
        
        print(f"\n{'='*80}")
        print(f"OPTIONS GREEKS ANALYSIS: {ticker}")
        print('='*80)
        
        print(f"\nStock Price: ${analysis['current_price']:.2f}")
        print(f"LEAPS Expiration: {analysis['expiration']} ({analysis['days_to_expiry']} days)")
        print(f"Available LEAPS: {len(analysis['all_expirations'])} expirations")
        
        print(f"\nIMPLIED VOLATILITY:")
        print(f"  Current IV: {analysis['atm_iv']:.1f}%")
        print(f"  IV Percentile: {analysis['iv_percentile']:.0f}% (higher = more expensive)")
        print(f"  IV Rank: {analysis['iv_rank']:.0f}%")
        print(f"  52-Week Range: {analysis['iv_low']:.1f}% - {analysis['iv_high']:.1f}%")
        
        # Calls
        print(f"\nCALLS (Strike/Price/IV/Delta/Theta/OI):")
        print("-"*70)
        for c in analysis['calls']:
            itm_marker = "ITM" if c['itm'] else "OTM"
            print(f"  ${c['strike']:>7.2f} | ${c['mid_price']:>6.2f} | {c['iv']:>5.1f}% | "
                  f"Δ{c['delta']:>+5.2f} | θ{c['theta']:>6.3f} | {c['open_interest']:>6} | {itm_marker}")
        
        # Puts
        print(f"\nPUTS (Strike/Price/IV/Delta/Theta/OI):")
        print("-"*70)
        for p in analysis['puts']:
            itm_marker = "ITM" if p['itm'] else "OTM"
            print(f"  ${p['strike']:>7.2f} | ${p['mid_price']:>6.2f} | {p['iv']:>5.1f}% | "
                  f"Δ{p['delta']:>+5.2f} | θ{p['theta']:>6.3f} | {p['open_interest']:>6} | {itm_marker}")
        
        # Recommendations
        print(f"\nRECOMMENDED STRIKES:")
        for strat in ['conservative', 'moderate', 'aggressive']:
            rec = self.get_recommended_strike(analysis, strat)
            call = rec['recommended']
            print(f"  {strat.capitalize():12}: ${call['strike']:.2f} (Δ{call['delta']:.2f}, ${call['mid_price']:.2f})")
        
        print('='*80)


if __name__ == "__main__":
    import sys
    
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    
    analyzer = OptionsGreeksAnalyzer()
    analyzer.print_analysis(ticker)

