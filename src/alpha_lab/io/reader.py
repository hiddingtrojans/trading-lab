#!/usr/bin/env python3
"""
Data Reader
===========

Read market data, features, and reference files.
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Optional


def load_config(config_path: str) -> Dict:
    """Load YAML config file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def read_features_parquet(date_str: str) -> pd.DataFrame:
    """Read features from versioned Parquet file."""
    path = f"data/features/features_{date_str}.parquet"
    if not Path(path).exists():
        raise FileNotFoundError(f"Features not found: {path}")
    return pd.read_parquet(path)


def read_raw_prices(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Read raw price data."""
    import yfinance as yf
    data = yf.download(symbol, start=start_date, end=end_date, progress=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    data.columns = [col.lower() for col in data.columns]
    return data


def read_close_ref() -> pd.Series:
    """Read reference close prices."""
    path = "data/ref/close_ref.csv"
    if Path(path).exists():
        return pd.read_csv(path, index_col='asset')['close']
    return pd.Series(dtype=float)


def read_nav() -> float:
    """Read current NAV."""
    path = "data/ref/nav.txt"
    if Path(path).exists():
        return float(open(path).read().strip())
    return 100000.0  # Default $100k

