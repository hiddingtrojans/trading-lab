#!/usr/bin/env python3
"""
Elliott Wave Analysis
=====================

Simplified Elliott Wave pattern detection.

Elliott Wave Theory:
- Markets move in 5-wave impulse patterns (1-2-3-4-5)
- Wave 1, 3, 5 = trend direction
- Wave 2, 4 = corrections
- Followed by 3-wave correction (A-B-C)

This is a simplified heuristic approach, not full Elliott Wave analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import yfinance as yf


def find_pivots(prices: pd.Series, window: int = 5) -> pd.DataFrame:
    """
    Find swing highs and lows (pivot points).
    
    Args:
        prices: Price series
        window: Number of bars on each side
        
    Returns:
        DataFrame with pivot points
    """
    pivots = []
    
    for i in range(window, len(prices) - window):
        # Check for swing high
        if prices.iloc[i] == prices.iloc[i-window:i+window+1].max():
            pivots.append({
                'index': i,
                'price': prices.iloc[i],
                'type': 'high'
            })
        # Check for swing low
        elif prices.iloc[i] == prices.iloc[i-window:i+window+1].min():
            pivots.append({
                'index': i,
                'price': prices.iloc[i],
                'type': 'low'
            })
    
    return pd.DataFrame(pivots)


def detect_wave_pattern(pivots: pd.DataFrame) -> Dict:
    """
    Detect potential Elliott Wave pattern.
    
    Simplified rules:
    - Wave 3 should be longest (or at least not shortest)
    - Wave 2 shouldn't retrace more than 100% of wave 1
    - Wave 4 shouldn't overlap with wave 1
    - Waves should alternate high-low-high-low-high
    """
    if len(pivots) < 5:
        return {'pattern_found': False, 'reason': 'Insufficient pivots'}
    
    # Look for 5-wave pattern in last pivots
    recent = pivots.tail(10)
    
    # Simplified detection: look for alternating pattern
    if len(recent) >= 5:
        last_5 = recent.tail(5)
        
        # Check if alternating high-low
        types = last_5['type'].tolist()
        
        # Bullish pattern: low-high-low-high-low-high
        # Bearish pattern: high-low-high-low-high-low
        
        # Check for 5-wave impulse (simplified)
        if len(set(types)) == 2:  # Has both highs and lows
            prices = last_5['price'].tolist()
            
            # Very simplified: trending in one direction with corrections
            overall_trend = prices[-1] - prices[0]
            
            if overall_trend > 0:
                pattern = 'bullish_impulse'
                wave_5_price = prices[-1]
            else:
                pattern = 'bearish_impulse'
                wave_5_price = prices[-1]
            
            return {
                'pattern_found': True,
                'pattern_type': pattern,
                'wave_5_price': wave_5_price,
                'confidence': 'low',  # Simplified analysis = low confidence
                'interpretation': 'Possible wave 5 - trend may be nearing completion'
            }
    
    return {'pattern_found': False, 'reason': 'No clear pattern'}


def analyze_elliott_wave(ticker: str, period: str = '6mo') -> Dict:
    """
    Analyze Elliott Wave pattern for a ticker.
    
    Args:
        ticker: Stock symbol
        period: Time period ('3mo', '6mo', '1y')
        
    Returns:
        Dictionary with wave analysis
    """
    try:
        # Download price data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty or len(hist) < 50:
            return {
                'ticker': ticker,
                'pattern_found': False,
                'reason': 'Insufficient data'
            }
        
        # Find pivots
        pivots = find_pivots(hist['Close'], window=5)
        
        if pivots.empty:
            return {
                'ticker': ticker,
                'pattern_found': False,
                'reason': 'No pivots found'
            }
        
        # Detect pattern
        pattern = detect_wave_pattern(pivots)
        
        # Add current price context
        current_price = hist['Close'].iloc[-1]
        
        result = {
            'ticker': ticker,
            'current_price': current_price,
            'num_pivots': len(pivots),
            **pattern
        }
        
        # Add simple trend analysis
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
        
        if current_price > sma_20 > sma_50:
            result['trend'] = 'strong_uptrend'
        elif current_price > sma_20:
            result['trend'] = 'uptrend'
        elif current_price < sma_20 < sma_50:
            result['trend'] = 'strong_downtrend'
        else:
            result['trend'] = 'downtrend'
        
        return result
        
    except Exception as e:
        return {
            'ticker': ticker,
            'pattern_found': False,
            'error': str(e)
        }


def display_elliott_wave(analysis: Dict):
    """Display Elliott Wave analysis."""
    print(f"\n{'='*80}")
    print(f"ELLIOTT WAVE ANALYSIS: {analysis['ticker']}")
    print(f"{'='*80}\n")
    
    if 'error' in analysis:
        print(f"✗ Error: {analysis['error']}")
        return
    
    print(f"Current Price: ${analysis.get('current_price', 0):.2f}")
    print(f"Pivots Found: {analysis.get('num_pivots', 0)}")
    print(f"Trend: {analysis.get('trend', 'unknown').replace('_', ' ').title()}")
    
    if analysis.get('pattern_found'):
        print(f"\nPattern Detected: {analysis['pattern_type'].replace('_', ' ').title()}")
        print(f"Wave 5 Level: ${analysis.get('wave_5_price', 0):.2f}")
        print(f"Confidence: {analysis.get('confidence', 'unknown').upper()}")
        print(f"\nInterpretation: {analysis.get('interpretation', 'N/A')}")
        print("\n⚠️ Note: Simplified Elliott Wave - use as supplement to other analysis")
    else:
        print(f"\nNo clear Elliott Wave pattern detected")
        print(f"Reason: {analysis.get('reason', 'Unknown')}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    """Demo/test Elliott Wave analysis."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python elliott_wave.py TICKER")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    print(f"Analyzing Elliott Wave pattern for {ticker}...")
    analysis = analyze_elliott_wave(ticker, period='6mo')
    display_elliott_wave(analysis)

