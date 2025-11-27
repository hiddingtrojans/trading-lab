#!/usr/bin/env python3
"""
Flow Features
=============

ETF flow and volume-based features.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf


def build_flow_features(cfg: dict) -> pd.DataFrame:
    """
    Build flow features (volume, turnover, etc).
    
    Args:
        cfg: Config dict
        
    Returns:
        DataFrame with multi-index (date, asset) and flow features
    """
    universe = cfg['universe']
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=750)
    
    all_flows = []
    
    for symbol in universe:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                continue
            
            # Flatten columns
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            data.columns = [col.lower() for col in data.columns]
            
            # Flow features
            df = pd.DataFrame(index=data.index)
            
            # Volume metrics
            df['volume_ma_20'] = data['volume'].rolling(20).mean()
            df['volume_ratio'] = data['volume'] / df['volume_ma_20']
            df['volume_zscore'] = ((data['volume'] - df['volume_ma_20']) /
                                   data['volume'].rolling(20).std())
            
            # Dollar volume
            df['dollar_volume'] = data['close'] * data['volume']
            df['dollar_volume_ma'] = df['dollar_volume'].rolling(20).mean()
            
            # OBV (On-Balance Volume)
            obv = (np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum()
            df['obv'] = obv
            df['obv_ma'] = obv.rolling(20).mean()
            df['obv_signal'] = np.where(obv > df['obv_ma'], 1, -1)
            
            # Add asset label
            df['asset'] = symbol
            
            all_flows.append(df)
            
        except Exception as e:
            print(f"⚠️  Error building flows for {symbol}: {e}")
            continue
    
    if not all_flows:
        return pd.DataFrame()
    
    combined = pd.concat(all_flows)
    combined = combined.reset_index().rename(columns={'Date': 'date'})
    combined = combined.set_index(['date', 'asset'])
    
    return combined

