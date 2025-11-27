#!/usr/bin/env python3
"""
Macro Features
==============

Macro economic surprise indicators.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf


def build_macro_features(cfg: dict) -> pd.DataFrame:
    """
    Build macro features.
    
    Args:
        cfg: Config dict
        
    Returns:
        DataFrame with multi-index (date, asset) and macro features
    """
    # For now, build simple macro indicators
    # In production: would use FRED, Bloomberg, etc.
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=750)
    
    # Download macro proxies
    try:
        vix = yf.download('^VIX', start=start_date, end=end_date, progress=False)['Close']
    except:
        vix = pd.Series(dtype=float)
    
    try:
        dxy_data = yf.download('DX-Y.NYB', start=start_date, end=end_date, progress=False)
        dxy = dxy_data['Close'] if not dxy_data.empty else pd.Series(dtype=float)
    except:
        dxy = pd.Series(dtype=float)
    
    # Create macro features (broadcast to all assets)
    macro_df = pd.DataFrame(index=vix.index if not vix.empty else pd.DatetimeIndex([]))
    macro_df['vix_level'] = vix if not vix.empty else np.nan
    macro_df['vix_change'] = vix.pct_change(5) if not vix.empty else np.nan
    macro_df['dxy_change'] = dxy.pct_change(20) if not dxy.empty else np.nan
    
    # Replicate for each asset in universe
    universe = cfg['universe']
    
    all_macro = []
    for asset in universe:
        asset_macro = macro_df.copy()
        asset_macro['asset'] = asset
        all_macro.append(asset_macro)
    
    combined = pd.concat(all_macro)
    combined = combined.reset_index().rename(columns={'Date': 'date'})
    combined = combined.set_index(['date', 'asset'])
    
    return combined
