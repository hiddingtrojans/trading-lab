#!/usr/bin/env python3
"""
Data Writer
===========

Write features, signals, orders, fills to disk.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path


def write_features_parquet(features: pd.DataFrame, cfg: dict):
    """
    Write features to versioned Parquet file.
    
    Args:
        features: Feature DataFrame (multi-index: date x asset)
        cfg: Config dict
    """
    date_str = datetime.now().strftime('%Y%m%d')
    path = f"data/features/features_{date_str}.parquet"
    
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(path, compression='snappy')
    
    print(f"✅ Features saved: {path}")


def write_signals(signals: pd.DataFrame, date_str: str = None):
    """Write signals to CSV."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    path = f"signals/signals_{date_str}.csv"
    signals.to_csv(path)
    
    # Also save as latest
    signals.to_csv("signals/latest.csv")
    
    print(f"✅ Signals saved: {path}")


def write_orders(orders: pd.DataFrame, date_str: str = None):
    """Write submitted orders."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    path = f"orders/orders_{date_str}.csv"
    orders.to_csv(path, index=False)
    
    print(f"✅ Orders saved: {path}")


def write_fills(fills: pd.DataFrame):
    """Append fills to master file."""
    path = "fills/ibkr_fills.csv"
    
    if Path(path).exists():
        existing = pd.read_csv(path)
        combined = pd.concat([existing, fills], ignore_index=True)
        combined.to_csv(path, index=False)
    else:
        fills.to_csv(path, index=False)
    
    print(f"✅ Fills saved: {path}")


def write_positions(positions: pd.DataFrame):
    """Write current positions snapshot."""
    path = "positions/ibkr_positions.csv"
    positions.to_csv(path, index=False)
    
    print(f"✅ Positions saved: {path}")


def write_equity_curve(returns: pd.Series):
    """Append to equity curve."""
    date_str = datetime.now().strftime('%Y%m%d')
    path = f"equity_curve/equity_{date_str}.csv"
    
    returns.to_csv(path)
    print(f"✅ Equity curve saved: {path}")

