#!/usr/bin/env python3
"""
Simple Signal Generator
=======================

Generates clean signals for latest date only.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from alpha_lab.io.reader import load_config
from alpha_lab.pipeline.build_features import run as build_features
from alpha_lab.io.writer import write_signals


def generate_signals(cfg: dict, features: pd.DataFrame) -> pd.DataFrame:
    """
    Generate signals for latest date per asset.
    
    Args:
        cfg: Configuration dict with universe
        features: Full feature DataFrame (multi-index: date x asset)
        
    Returns:
        DataFrame with one row per asset, column 'weight'
    """
    universe = cfg['universe']
    return generate_latest_signals(features, universe)


def generate_latest_signals(features: pd.DataFrame, universe: list) -> pd.DataFrame:
    """
    Generate signals for latest date per asset.
    
    Args:
        features: Full feature DataFrame (multi-index: date x asset)
        universe: List of assets
        
    Returns:
        DataFrame with one row per asset, column 'weight'
    """
    signals = []
    
    for asset in universe:
        try:
            # Get all data for this asset
            asset_data = features.xs(asset, level=0)
            
            if asset_data.empty:
                signals.append({'asset': asset, 'weight': 0.0})
                continue
            
            # Get most recent row
            latest = asset_data.iloc[-1]
            
            # Generate signal based on momentum
            momentum = latest.get('momentum_20d', 0)
            vol = latest.get('realized_vol_20d', 0.15)
            
            if pd.isna(momentum) or pd.isna(vol):
                weight = 0.0
            else:
                # Vol-scaled momentum
                weight = np.clip(momentum / (vol + 1e-8), -0.3, 0.3)
            
            signals.append({'asset': asset, 'weight': float(weight)})
            
        except Exception as e:
            print(f"   ⚠️  Error for {asset}: {e}")
            signals.append({'asset': asset, 'weight': 0.0})
    
    return pd.DataFrame(signals).set_index('asset')


if __name__ == "__main__":
    cfg = load_config('configs/default.yaml')
    
    print("="*70)
    print("🎯 SIMPLE SIGNAL GENERATION")
    print("="*70)
    print(f"\nUniverse: {cfg['universe']}")
    
    # Build features
    print("\n🏗️  Building features...")
    feats = build_features(cfg)
    
    # Generate signals
    print("\n🎯 Generating signals for latest date...")
    signals = generate_latest_signals(feats, cfg['universe'])
    
    print("\n📊 SIGNALS:")
    print("="*70)
    print(signals)
    
    # Write to file
    write_signals(signals)
    
    print("\n✅ Done. Signals saved to signals/latest.csv")

