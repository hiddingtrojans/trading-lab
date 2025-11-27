#!/usr/bin/env python3
"""
Price Features
==============

Technical features from OHLCV data.
"""

import pandas as pd
import numpy as np


def build_price_features(cfg: dict) -> pd.DataFrame:
    """
    Build price-based features for universe.
    
    Args:
        cfg: Config dict with universe
        
    Returns:
        DataFrame with multi-index (date, asset) and price features
    """
    import yfinance as yf
    from datetime import datetime, timedelta
    
    universe = cfg['universe']
    
    # Download data for all symbols
    end_date = datetime.now()
    start_date = end_date - timedelta(days=750)  # ~3 years
    
    all_features = []
    
    for symbol in universe:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                continue
            
            # Flatten multi-index columns if needed
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            data.columns = [col.lower() for col in data.columns]
            
            # Calculate features
            df = pd.DataFrame(index=data.index)
            
            # Returns
            df['ret_1d'] = data['close'].pct_change(1)
            df['ret_5d'] = data['close'].pct_change(5)
            df['ret_20d'] = data['close'].pct_change(20)
            
            # Realized volatility
            df['realized_vol_20d'] = df['ret_1d'].rolling(20).std() * np.sqrt(252)
            
            # Moving averages
            df['sma_50'] = data['close'].rolling(50).mean()
            df['sma_200'] = data['close'].rolling(200).mean()
            df['price_vs_sma_50'] = (data['close'] - df['sma_50']) / df['sma_50']
            
            # Momentum
            df['momentum_20d'] = data['close'].pct_change(20)
            df['momentum_60d'] = data['close'].pct_change(60)
            
            # Volume
            df['volume_ratio_20'] = data['volume'] / data['volume'].rolling(20).mean()
            
            # Drawdown flag
            cummax = data['close'].cummax()
            df['drawdown'] = (data['close'] - cummax) / cummax
            df['drawdown_flag'] = (df['drawdown'] < -0.05).astype(int)
            
            # Add asset label
            df['asset'] = symbol
            
            # Add to list
            all_features.append(df)
            
        except Exception as e:
            print(f"⚠️  Error building features for {symbol}: {e}")
            continue
    
    # Combine all symbols
    if not all_features:
        return pd.DataFrame()
    
    combined = pd.concat(all_features)
    combined = combined.reset_index()
    
    # Standardize column names (yfinance uses 'Date' or index name varies)
    if 'Date' in combined.columns:
        combined = combined.rename(columns={'Date': 'date'})
    elif 'index' in combined.columns:
        combined = combined.rename(columns={'index': 'date'})
    
    combined = combined.set_index(['date', 'asset'])
    
    return combined

