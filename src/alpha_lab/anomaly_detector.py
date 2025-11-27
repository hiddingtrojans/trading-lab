#!/usr/bin/env python3
"""
Anomaly-Based Breakout Detector
================================

Instead of predicting all stocks, detect EXTREME anomalies:
- Volume shocks (>5x normal)
- Volatility compression then expansion
- Multi-timeframe momentum alignment
- Sector relative strength extremes
- Post-earnings continuation

Only make predictions for top 5% of anomaly scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from datetime import datetime, timedelta


class AnomalyDetector:
    """Detect extreme anomalies that precede breakouts."""
    
    @staticmethod
    def detect_volume_shock(data: pd.DataFrame) -> pd.Series:
        """
        Detect massive volume spikes.
        Score: 0-100 based on volume vs historical.
        """
        volume = data['Volume']
        volume_ma_60 = volume.rolling(60).mean()
        volume_std_60 = volume.rolling(60).std()
        
        # Z-score of volume
        volume_zscore = (volume - volume_ma_60) / (volume_std_60 + 1e-8)
        
        # Convert to 0-100 score (cap at 5 sigma)
        score = np.clip(volume_zscore / 5.0 * 100, 0, 100)
        
        return score
    
    @staticmethod
    def detect_volatility_squeeze_breakout(data: pd.DataFrame) -> pd.Series:
        """
        Detect volatility compression followed by expansion.
        Bollinger Band squeeze -> breakout pattern.
        """
        close = data['Close']
        
        # Calculate Bollinger Bands
        ma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        
        bb_width = (std_20 * 2) / ma_20
        
        # Historical volatility percentile
        bb_width_pct = bb_width.rolling(120).rank(pct=True)
        
        # Score high when:
        # 1. Recent squeeze (low percentile)
        # 2. Then expansion (price moving)
        recent_squeeze = (1 - bb_width_pct.shift(5))  # Was compressed 5 days ago
        current_move = close.pct_change(5).abs()  # Now moving
        
        score = recent_squeeze * current_move * 1000
        score = np.clip(score, 0, 100)
        
        return score
    
    @staticmethod
    def detect_momentum_alignment(data: pd.DataFrame) -> pd.Series:
        """
        Detect when multiple timeframes all show positive momentum.
        Rare but powerful signal.
        """
        close = data['Close']
        
        # Multiple timeframe returns
        ret_3d = close.pct_change(3) > 0
        ret_7d = close.pct_change(7) > 0
        ret_14d = close.pct_change(14) > 0
        ret_21d = close.pct_change(21) > 0
        
        # Count how many are positive
        alignment = ret_3d.astype(int) + ret_7d.astype(int) + ret_14d.astype(int) + ret_21d.astype(int)
        
        # All 4 positive = 100, none = 0
        score = alignment / 4.0 * 100
        
        return score
    
    @staticmethod
    def detect_relative_strength_extreme(data: pd.DataFrame, sector_etf_data: pd.DataFrame) -> pd.Series:
        """
        Detect extreme outperformance vs sector.
        """
        stock_returns = data['Close'].pct_change(20)
        sector_returns = sector_etf_data['Close'].pct_change(20)
        
        # Align dates
        sector_returns = sector_returns.reindex(stock_returns.index, method='ffill')
        
        # Relative strength
        rs = stock_returns - sector_returns
        
        # Percentile rank over 120 days
        rs_pct = rs.rolling(120).rank(pct=True)
        
        # Score high for top decile
        score = np.where(rs_pct > 0.9, rs_pct * 100, 0)
        
        return pd.Series(score, index=stock_returns.index)
    
    @staticmethod
    def detect_gap_continuation(data: pd.DataFrame) -> pd.Series:
        """
        Detect gaps that continue (not fade).
        """
        close = data['Close']
        open_price = data['Open']
        
        # Gap size
        gap = (open_price - close.shift()) / close.shift()
        
        # Does price continue in gap direction?
        continuation = np.sign(gap) == np.sign(close.pct_change())
        
        # Score based on gap size and continuation
        score = np.where(continuation, np.abs(gap) * 1000, 0)
        score = np.clip(score, 0, 100)
        
        return score
    
    @staticmethod
    def detect_range_breakout(data: pd.DataFrame) -> pd.Series:
        """
        Detect breakouts from consolidation ranges.
        """
        close = data['Close']
        high_20 = close.rolling(20).max()
        low_20 = close.rolling(20).min()
        
        # Is price breaking out of 20-day range?
        breakout = (close > high_20.shift()) | (close < low_20.shift())
        
        # How compressed was the range?
        range_pct = (high_20 - low_20) / close
        range_compression = 1 - range_pct.rolling(60).rank(pct=True)
        
        # Score high for breakouts from compressed ranges
        score = np.where(breakout, range_compression * 100, 0)
        
        return score
    
    def calculate_composite_anomaly_score(self, 
                                         data: pd.DataFrame,
                                         sector_etf_data: pd.DataFrame = None) -> pd.Series:
        """
        Calculate composite anomaly score from all detectors.
        """
        scores = {}
        
        # Volume shock (30% weight - very predictive)
        scores['volume'] = self.detect_volume_shock(data) * 0.30
        
        # Volatility squeeze/breakout (25% weight)
        scores['vol_squeeze'] = self.detect_volatility_squeeze_breakout(data) * 0.25
        
        # Momentum alignment (20% weight)
        scores['momentum'] = self.detect_momentum_alignment(data) * 0.20
        
        # Gap continuation (15% weight)
        scores['gap'] = self.detect_gap_continuation(data) * 0.15
        
        # Range breakout (10% weight)
        scores['range'] = self.detect_range_breakout(data) * 0.10
        
        # Relative strength (if sector data available)
        if sector_etf_data is not None:
            scores['rel_strength'] = self.detect_relative_strength_extreme(data, sector_etf_data) * 0.20
            # Reweight others
            for k in scores:
                if k != 'rel_strength':
                    scores[k] *= 0.8
        
        # Combine
        composite = pd.DataFrame(scores).sum(axis=1)
        
        return composite


def add_anomaly_features(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add anomaly scores to feature DataFrame.
    
    Args:
        features_df: DataFrame with technical features and price data
        
    Returns:
        DataFrame with added anomaly scores
    """
    print("\nCalculating anomaly scores...")
    
    detector = AnomalyDetector()
    
    # Get SPY for relative strength
    import yfinance as yf
    spy_data = yf.download('SPY', 
                          start=datetime.now() - timedelta(days=500),
                          end=datetime.now(),
                          progress=False)
    
    enhanced_rows = []
    symbols = features_df['symbol'].unique()
    
    for i, symbol in enumerate(symbols):
        if (i + 1) % 50 == 0:
            print(f"  Processing anomalies {i+1}/{len(symbols)}...")
        
        try:
            symbol_data = features_df[features_df['symbol'] == symbol].copy()
            
            # Download fresh price data for this symbol
            stock_data = yf.download(symbol,
                                    start=datetime.now() - timedelta(days=500),
                                    end=datetime.now(),
                                    progress=False)
            
            if stock_data.empty:
                enhanced_rows.append(symbol_data)
                continue
            
            # Calculate composite anomaly score
            anomaly_score = detector.calculate_composite_anomaly_score(stock_data, spy_data)
            
            # Align to features_df dates
            symbol_data['anomaly_score'] = anomaly_score.reindex(symbol_data.index, method='ffill')
            
            # Add individual detector scores for analysis
            symbol_data['anomaly_volume'] = detector.detect_volume_shock(stock_data).reindex(symbol_data.index, method='ffill')
            symbol_data['anomaly_vol_squeeze'] = detector.detect_volatility_squeeze_breakout(stock_data).reindex(symbol_data.index, method='ffill')
            symbol_data['anomaly_momentum'] = detector.detect_momentum_alignment(stock_data).reindex(symbol_data.index, method='ffill')
            
            enhanced_rows.append(symbol_data)
            
        except Exception as e:
            print(f"  Warning: {symbol} anomaly detection failed: {e}")
            enhanced_rows.append(symbol_data)
            continue
    
    enhanced_df = pd.concat(enhanced_rows, ignore_index=True)
    
    print(f"Anomaly scores added. Shape: {enhanced_df.shape}")
    
    return enhanced_df


print("Anomaly Detector Module - Loaded")
