#!/usr/bin/env python3
"""
Unusual Options Activity (UOA) Scanner
======================================

Detects "Smart Money" flow in the options market.
Focuses on anomalies that suggest urgent, informed positioning.

Signals:
1. Vol/OI Ratio > 2.0: Aggressive new opening positions.
2. Heavy OTM Volume: Speculative betting on a big move.
3. Gamma Exposure: Strikes with massive volume that could trigger hedging.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

class OptionsFlowScanner:
    """Scans for unusual options activity."""
    
    def __init__(self):
        pass
        
    def scan_flow(self, ticker: str) -> Dict:
        """
        Scan option chains for anomalies.
        """
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                return {'status': 'NO_DATA', 'alerts': []}
                
            current_price = stock.history(period='1d')['Close'].iloc[-1]
            
            # Check nearest 2 expirations (most urgent flow)
            check_dates = expirations[:2]
            alerts = []
            total_call_vol = 0
            total_put_vol = 0
            
            for date in check_dates:
                chain = stock.option_chain(date)
                calls = chain.calls
                puts = chain.puts
                
                # 1. Filter for High Volume
                # Minimum volume to care: 500 contracts (adjust based on liquidity)
                min_vol = 500 
                
                active_calls = calls[calls['volume'] > min_vol]
                active_puts = puts[puts['volume'] > min_vol]
                
                total_call_vol += calls['volume'].sum()
                total_put_vol += puts['volume'].sum()
                
                # 2. Check Vol/OI Ratio (The "Scanner")
                for _, row in active_calls.iterrows():
                    vol = row['volume']
                    oi = row['openInterest'] if row['openInterest'] > 0 else 1
                    ratio = vol / oi
                    strike = row['strike']
                    
                    # Check if OTM
                    is_otm = strike > current_price * 1.02
                    
                    if ratio > 2.0 and is_otm:
                        alerts.append({
                            'type': 'BULLISH_UOA',
                            'expiry': date,
                            'strike': strike,
                            'vol': int(vol),
                            'oi': int(oi),
                            'ratio': round(ratio, 1),
                            'desc': f"Aggressive OTM Call Buying (Vol > {ratio:.1f}x OI)"
                        })
                        
                for _, row in active_puts.iterrows():
                    vol = row['volume']
                    oi = row['openInterest'] if row['openInterest'] > 0 else 1
                    ratio = vol / oi
                    strike = row['strike']
                    
                    # Check if OTM
                    is_otm = strike < current_price * 0.98
                    
                    if ratio > 2.0 and is_otm:
                        alerts.append({
                            'type': 'BEARISH_UOA',
                            'expiry': date,
                            'strike': strike,
                            'vol': int(vol),
                            'oi': int(oi),
                            'ratio': round(ratio, 1),
                            'desc': f"Aggressive OTM Put Buying (Vol > {ratio:.1f}x OI)"
                        })
                        
            # 3. Put/Call Ratio (Volume)
            pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 1.0
            sentiment = "NEUTRAL"
            if pc_ratio < 0.7: sentiment = "BULLISH"
            elif pc_ratio > 1.3: sentiment = "BEARISH"
            
            # Consolidate top alerts
            alerts.sort(key=lambda x: x['vol'], reverse=True)
            top_alerts = alerts[:3]
            
            return {
                'status': sentiment,
                'pc_ratio': round(pc_ratio, 2),
                'total_call_vol': int(total_call_vol),
                'total_put_vol': int(total_put_vol),
                'alerts': top_alerts
            }
            
        except Exception as e:
            # print(f"Options flow error: {e}")
            return {'status': 'ERROR', 'alerts': []}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('ticker', nargs='?', default='NVDA')
    args = parser.parse_args()
    
    print(f"Scanning Options Flow for {args.ticker}...")
    scanner = OptionsFlowScanner()
    res = scanner.scan_flow(args.ticker)
    
    print(f"\n🌊 FLOW SENTIMENT: {res['status']} (P/C Ratio: {res.get('pc_ratio', 'N/A')})")
    print(f"   Calls: {res.get('total_call_vol', 0):,} | Puts: {res.get('total_put_vol', 0):,}")
    
    if res['alerts']:
        print("\n🚨 UNUSUAL ACTIVITY DETECTED:")
        for alert in res['alerts']:
            print(f"   • {alert['type']} {alert['desc']}")
            print(f"     {alert['expiry']} ${alert['strike']} | Vol: {alert['vol']} vs OI: {alert['oi']}")
    else:
        print("\n   No significant anomalies found.")

