#!/usr/bin/env python3
"""
Intraday Breakout Signals Using IBKR Real-Time Data
====================================================

Uses patterns that work on shorter timeframes:
- Opening gap continuation/fade
- VWAP reversion
- Momentum after volume spikes
- Previous day high/low breaks

Target: 30-min to 4-hour holding periods
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from ib_insync import IB, Stock, util
import yfinance as yf
from typing import List, Dict


class IntradaySignalGenerator:
    """Generate intraday breakout signals using IBKR data."""
    
    def __init__(self, ib: IB):
        self.ib = ib
        
    def get_intraday_bars(self, symbol: str, duration: str = '2 D', bar_size: str = '5 mins') -> pd.DataFrame:
        """
        Get intraday bars from IBKR.
        
        Args:
            symbol: Stock symbol
            duration: How far back (e.g. '2 D', '1 W')
            bar_size: Bar size (e.g. '1 min', '5 mins', '15 mins')
            
        Returns:
            DataFrame with OHLCV data
        """
        contract = Stock(symbol, 'SMART', 'USD')
        
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=True,  # Regular trading hours only
            formatDate=1
        )
        
        if not bars:
            return pd.DataFrame()
        
        df = util.df(bars)
        df = df.set_index('date')
        
        return df
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP (Volume Weighted Average Price)."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
    
    def detect_opening_gap(self, symbol: str) -> Dict:
        """
        Detect opening gap and predict continuation/fade.
        
        Gap continuation works when:
        - Large gap (>2%)
        - High volume on open
        - Gap direction = prior day trend
        """
        try:
            # Get 2 days of 5-min bars
            df = self.get_intraday_bars(symbol, duration='2 D', bar_size='5 mins')
            
            if df.empty or len(df) < 80:  # Need at least 1 day of bars
                return None
            
            # Get today's data (last ~78 bars = 1 trading day)
            today = df.tail(78)
            yesterday = df.iloc[-156:-78] if len(df) >= 156 else df.head(78)
            
            if len(today) < 10 or len(yesterday) < 10:
                return None
            
            # Calculate gap
            yesterday_close = yesterday['close'].iloc[-1]
            today_open = today['open'].iloc[0]
            gap_pct = (today_open - yesterday_close) / yesterday_close
            
            if abs(gap_pct) < 0.01:  # Only care about >1% gaps
                return None
            
            # Calculate VWAP
            today['vwap'] = self.calculate_vwap(today)
            
            # Current price vs VWAP
            current_price = today['close'].iloc[-1]
            current_vwap = today['vwap'].iloc[-1]
            
            # Volume analysis
            current_volume = today['volume'].iloc[-10:].mean()  # Last 10 bars avg
            normal_volume = yesterday['volume'].mean()
            volume_ratio = current_volume / normal_volume if normal_volume > 0 else 1
            
            # Yesterday's trend
            yesterday_trend = (yesterday['close'].iloc[-1] - yesterday['open'].iloc[0]) / yesterday['open'].iloc[0]
            
            # Signal logic
            gap_with_trend = np.sign(gap_pct) == np.sign(yesterday_trend)
            high_volume = volume_ratio > 1.2
            price_holding = (current_price - today_open) * np.sign(gap_pct) > 0
            
            # Continuation signal
            if gap_with_trend and high_volume and price_holding:
                signal = 'GAP_CONTINUATION'
                confidence = min(abs(gap_pct) * 100 * volume_ratio, 100)
            # Fade signal
            elif abs(current_price - yesterday_close) / yesterday_close < abs(gap_pct) * 0.5:
                signal = 'GAP_FADE'
                confidence = min((1 - price_holding) * 50, 100)
            else:
                signal = 'NEUTRAL'
                confidence = 0
            
            return {
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'gap_pct': gap_pct,
                'price': current_price,
                'vwap': current_vwap,
                'volume_ratio': volume_ratio,
                'gap_with_trend': gap_with_trend
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def detect_momentum_breakout(self, symbol: str) -> Dict:
        """
        Detect intraday momentum breakouts.
        
        Works when:
        - Volume spike (>2x normal)
        - Breaking previous day high/low
        - Sustained move (not just a spike)
        """
        try:
            df = self.get_intraday_bars(symbol, duration='2 D', bar_size='5 mins')
            
            if df.empty or len(df) < 80:
                return None
            
            today = df.tail(78)
            yesterday = df.iloc[-156:-78] if len(df) >= 156 else df.head(78)
            
            if len(today) < 20:
                return None
            
            # Previous day high/low
            prev_high = yesterday['high'].max()
            prev_low = yesterday['low'].min()
            
            # Current status
            current_price = today['close'].iloc[-1]
            current_high = today['high'].max()
            current_low = today['low'].min()
            
            # Volume surge
            recent_volume = today['volume'].iloc[-6:].mean()  # Last 30 mins
            avg_volume = today['volume'].mean()
            volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Price momentum
            price_change_30min = (current_price - today['close'].iloc[-7]) / today['close'].iloc[-7]
            
            # Detect breakout
            breaking_high = current_high > prev_high
            breaking_low = current_low < prev_low
            strong_volume = volume_surge > 1.5
            sustained = abs(price_change_30min) > 0.01  # >1% move in 30 min
            
            if breaking_high and strong_volume and sustained and price_change_30min > 0:
                signal = 'MOMENTUM_BREAKOUT_LONG'
                confidence = min(volume_surge * abs(price_change_30min) * 500, 100)
            elif breaking_low and strong_volume and sustained and price_change_30min < 0:
                signal = 'MOMENTUM_BREAKOUT_SHORT'
                confidence = min(volume_surge * abs(price_change_30min) * 500, 100)
            else:
                signal = 'NO_BREAKOUT'
                confidence = 0
            
            return {
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'price': current_price,
                'volume_surge': volume_surge,
                'price_change_30min': price_change_30min,
                'breaking_high': breaking_high,
                'breaking_low': breaking_low
            }
            
        except Exception as e:
            print(f"Error in momentum detection for {symbol}: {e}")
            return None
    
    def detect_vwap_reversion(self, symbol: str) -> Dict:
        """
        Detect mean reversion opportunities around VWAP.
        
        Works when price deviates significantly from VWAP
        and shows signs of reverting.
        """
        try:
            df = self.get_intraday_bars(symbol, duration='1 D', bar_size='5 mins')
            
            if df.empty or len(df) < 20:
                return None
            
            # Calculate VWAP
            df['vwap'] = self.calculate_vwap(df)
            
            current_price = df['close'].iloc[-1]
            current_vwap = df['vwap'].iloc[-1]
            
            # Deviation from VWAP
            deviation_pct = (current_price - current_vwap) / current_vwap
            
            # Standard deviation of price from VWAP
            df['vwap_dev'] = (df['close'] - df['vwap']) / df['vwap']
            std_dev = df['vwap_dev'].std()
            
            # Z-score
            z_score = deviation_pct / std_dev if std_dev > 0 else 0
            
            # Reversal signal
            price_momentum = df['close'].pct_change(3).iloc[-1]  # 15-min momentum
            
            # Signal when >2 std devs away and momentum reversing
            if z_score > 2 and price_momentum < 0:
                signal = 'VWAP_REVERSION_SHORT'
                confidence = min(abs(z_score) * 30, 100)
            elif z_score < -2 and price_momentum > 0:
                signal = 'VWAP_REVERSION_LONG'
                confidence = min(abs(z_score) * 30, 100)
            else:
                signal = 'NO_REVERSION'
                confidence = 0
            
            return {
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'price': current_price,
                'vwap': current_vwap,
                'deviation_pct': deviation_pct,
                'z_score': z_score
            }
            
        except Exception as e:
            print(f"Error in VWAP reversion for {symbol}: {e}")
            return None
    
    def scan_universe(self, symbols: List[str]) -> pd.DataFrame:
        """
        Scan entire universe for intraday signals.
        
        Returns DataFrame with all signals ranked by confidence.
        """
        print(f"Scanning {len(symbols)} symbols for intraday opportunities...")
        
        all_signals = []
        
        for i, symbol in enumerate(symbols):
            if (i + 1) % 10 == 0:
                print(f"  Scanned {i+1}/{len(symbols)}...")
            
            try:
                # Run all detectors
                gap_signal = self.detect_opening_gap(symbol)
                momentum_signal = self.detect_momentum_breakout(symbol)
                vwap_signal = self.detect_vwap_reversion(symbol)
                
                # Combine signals
                signals = [gap_signal, momentum_signal, vwap_signal]
                signals = [s for s in signals if s is not None and s.get('confidence', 0) > 0]
                
                if signals:
                    # Pick highest confidence signal
                    best_signal = max(signals, key=lambda x: x['confidence'])
                    all_signals.append(best_signal)
                    
            except Exception as e:
                print(f"  Warning: {symbol} failed: {e}")
                continue
        
        if not all_signals:
            print("No signals found")
            return pd.DataFrame()
        
        signals_df = pd.DataFrame(all_signals)
        signals_df = signals_df.sort_values('confidence', ascending=False)
        
        print(f"\nFound {len(signals_df)} intraday signals")
        
        return signals_df


print("Intraday Signals Module - Loaded")
