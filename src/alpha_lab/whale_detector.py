#!/usr/bin/env python3
"""
Whale Detector (Dark Pool Proxy)
================================

Detects institutional footprint using public intraday data.
True dark pool data is hidden, but we can spot the "shadow" of large orders.

Signals:
1. Volume Spikes: 1-min volume > 10x average.
2. VWAP Divergence: Price trend vs VWAP trend.
3. Volume Nodes: Price levels with massive accumulation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import sys
import os

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.data_fetcher import DataFetcher
from alpha_lab.institutional_memory import InstitutionalMemory

class WhaleDetector:
    """Detects anomalous volume patterns indicating institutional activity."""
    
    def __init__(self, fetcher: DataFetcher = None):
        self.fetcher = fetcher if fetcher else DataFetcher(None)
        self.memory = InstitutionalMemory()
        
    def detect_whales(self, ticker: str) -> Dict:
        """
        Scan for whale activity in recent intraday data.
        """
        # Get high-res data (5 days of 5m bars is robust enough for volume profile)
        # 1m bars for 5 days is better for spike detection
        df = self.fetcher.get_intraday_data(ticker, days=5)
        
        if df.empty or len(df) < 100:
            return {'status': 'UNKNOWN', 'confidence': 0, 'details': 'Insufficient data'}
            
        # 1. Volume Spikes (> 5 standard deviations)
        # We need dynamic average (rolling mean) to account for open/close volume naturally being high
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        df['vol_std'] = df['volume'].rolling(window=20).std()
        
        # Z-Score of volume
        df['vol_z'] = (df['volume'] - df['vol_ma']) / df['vol_std']
        
        # Find significant spikes (z > 5) in the last 2 days
        recent = df.iloc[-156:] # Last ~2 trading days (78 * 2 for 5m bars)
        spikes = recent[recent['vol_z'] > 5]
        
        spike_count = len(spikes)
        last_spike_time = spikes['date'].iloc[-1] if not spikes.empty else None
        
        # 2. Volume Profile (Support/Resistance)
        # Bin prices to find High Volume Node (HVN)
        price_bins = pd.cut(recent['close'], bins=20)
        vol_profile = recent.groupby(price_bins, observed=True)['volume'].sum()
        hvn_price_interval = vol_profile.idxmax() # Interval with max volume
        hvn_price = hvn_price_interval.mid
        
        current_price = recent['close'].iloc[-1]
        
        # 3. VWAP Trend
        # Simple VWAP of the recent period
        vwap = (recent['close'] * recent['volume']).cumsum() / recent['volume'].cumsum()
        current_vwap = vwap.iloc[-1]
        
        # Logic
        status = "NEUTRAL"
        confidence = "low"
        details = []
        
        # Interpret Signals
        if spike_count > 0:
            details.append(f"{spike_count} volume spikes detected")
            
        if current_price > hvn_price:
            # Price is above the huge volume -> The volume is acting as Support -> Accumulation
            if spike_count > 0:
                status = "ACCUMULATION"
                confidence = "high" if current_price > current_vwap else "medium"
                details.append("Price holding above High Volume Node (Institutional Support)")
        elif current_price < hvn_price:
            # Price fell below huge volume -> The volume is acting as Resistance -> Distribution
            if spike_count > 0:
                status = "DISTRIBUTION"
                confidence = "high" if current_price < current_vwap else "medium"
                details.append("Price rejected at High Volume Node (Institutional Resistance)")
                
        # VWAP check
        if status == "NEUTRAL":
            if current_price > current_vwap * 1.01:
                status = "BULLISH FLOW"
                details.append("Strongly holding above VWAP")
            elif current_price < current_vwap * 0.99:
                status = "BEARISH FLOW"
                details.append("Weakness below VWAP")
        
        # Save to Memory if significant
        if status in ['ACCUMULATION', 'DISTRIBUTION']:
            self.memory.save_level(ticker, hvn_price, status, volume_score=spike_count)
            
        # Check Historical Levels (within 2%)
        historical_alerts = self.memory.check_proximity(ticker, current_price, threshold_pct=2.0)
        
        history_msg = ""
        if historical_alerts:
            alert = historical_alerts[0]
            history_msg = f"⚠️ Near Historical {alert['type']} (${alert['price']}) from {alert['date']}"
            details.append(history_msg)
                
        return {
            'status': status,
            'confidence': confidence,
            'spike_count': spike_count,
            'hvn_price': round(hvn_price, 2),
            'last_spike': last_spike_time,
            'historical_alert': history_msg,
            'details': "; ".join(details)
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('ticker', nargs='?', default='NVDA')
    args = parser.parse_args()
    
    print(f"Scanning for Whales in {args.ticker}...")
    detector = WhaleDetector()
    res = detector.detect_whales(args.ticker)
    
    print(f"\n🐋 WHALE ALERT: {res['status']} ({res['confidence']} confidence)")
    print(f"   Details: {res['details']}")
    print(f"   Volume Spikes: {res['spike_count']}")
    print(f"   Institutional Level (HVN): ${res['hvn_price']}")

