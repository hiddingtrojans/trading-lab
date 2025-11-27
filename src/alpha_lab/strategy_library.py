#!/usr/bin/env python3
"""
Strategy Library
================

Collection of institutional-grade trading strategies.
Each strategy returns specific Entry, Stop, and Target levels.

Strategies:
1. Gap & Go (Trend)
2. RSI Mean Reversion (Counter-Trend)
3. TTM Squeeze (Volatility Breakout)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

class StrategyLibrary:
    
    @staticmethod
    def gap_and_go(df: pd.DataFrame, prev_close: float) -> Optional[Dict]:
        """
        Classic Momentum: Gap > 2%, hold above VWAP.
        """
        if len(df) < 12: return None
        
        open_price = df['open'].iloc[0]
        gap_pct = (open_price - prev_close) / prev_close * 100
        
        # Filter: Gap must be significant but not exhaustion
        if not (2.0 < gap_pct < 10.0):
            return None
            
        # Setup: First 30m High
        orb_high = df.iloc[:6]['high'].max()
        
        # Entry: Breakout of ORB High
        entry_price = orb_high + 0.05
        stop_loss = df.iloc[:6]['low'].min()
        target = entry_price + 2 * (entry_price - stop_loss)
        
        return {
            'strategy': 'Gap & Go',
            'action': 'BUY_STOP',
            'entry': entry_price,
            'stop': stop_loss,
            'target': target,
            'setup_valid': True
        }

    @staticmethod
    def rsi_reversion(df: pd.DataFrame, prev_close: float) -> Optional[Dict]:
        """
        Mean Reversion: Buy dip in uptrend or oversold bounce.
        Uses daily RSI (approximated) or intraday RSI.
        """
        # Calculate simple intraday RSI-14 on 5m bars
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Setup: Oversold < 30
        if current_rsi < 30:
            # Entry: Market on Open of next bar (simulated as current close for signal)
            # Real entry: Break above previous bar high
            trigger_price = df['high'].iloc[-1] + 0.05
            atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
            
            return {
                'strategy': 'RSI Reversion',
                'action': 'BUY_STOP',
                'entry': trigger_price,
                'stop': trigger_price - (2 * atr),
                'target': trigger_price + (3 * atr),
                'setup_valid': True
            }
        return None

    @staticmethod
    def volatility_squeeze(df: pd.DataFrame) -> Optional[Dict]:
        """
        TTM Squeeze: Bollinger Bands inside Keltner Channels.
        Explosive move imminent.
        """
        if len(df) < 20: return None
        
        # Calculate BB (20, 2.0)
        sma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        bb_upper = sma20 + 2.0 * std20
        bb_lower = sma20 - 2.0 * std20
        
        # Calculate KC (20, 1.5) - Approx
        atr = (df['high'] - df['low']).rolling(20).mean()
        kc_upper = sma20 + 1.5 * atr
        kc_lower = sma20 - 1.5 * atr
        
        last = -1
        
        # Squeeze On: BB inside KC
        squeeze_on = (bb_upper.iloc[last] < kc_upper.iloc[last]) and (bb_lower.iloc[last] > kc_lower.iloc[last])
        
        if squeeze_on:
            # Entry: Breakout of recent 20-bar high
            high_20 = df['high'].iloc[-20:].max()
            
            return {
                'strategy': 'Vol Squeeze',
                'action': 'BUY_STOP',
                'entry': high_20 + 0.05,
                'stop': sma20.iloc[last], # Trail stop at MA
                'target': high_20 + (2 * atr.iloc[last]), # 2 ATR target
                'setup_valid': True
            }
        return None

