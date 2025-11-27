#!/usr/bin/env python3
"""
Build Features Pipeline
=======================

Constructs feature matrix from all sources.
"""

from datetime import datetime, timezone
import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from alpha_lab.features.price import build_price_features
from alpha_lab.features.sentiment import build_sentiment_features
from alpha_lab.features.macro import build_macro_features
from alpha_lab.features.flows import build_flow_features
from alpha_lab.io.writer import write_features_parquet


def run(cfg: dict):
    """
    Build complete feature matrix.
    
    Args:
        cfg: Config dict
    """
    print("="*70)
    print("🏗️  BUILDING FEATURES")
    print("="*70)
    
    _ = datetime.now(timezone.utc)  # Timestamp if needed
    
    # Build each feature set
    print("\n1. Building price features...")
    price = build_price_features(cfg)
    print(f"   ✅ Price features: {price.shape}")
    
    print("\n2. Building sentiment features...")
    sent = build_sentiment_features(cfg, cutoff_utc=cfg['signal_cutoff_utc'])
    print(f"   ✅ Sentiment features: {sent.shape}")
    
    print("\n3. Building macro features...")
    macro = build_macro_features(cfg)
    print(f"   ✅ Macro features: {macro.shape}")
    
    print("\n4. Building flow features...")
    flows = build_flow_features(cfg)
    print(f"   ✅ Flow features: {flows.shape}")
    
    # Join all features
    print("\n5. Joining features...")
    
    # Start with price features
    feats = price.copy()
    
    # Join sentiment if not empty
    if not sent.empty:
        feats = feats.join(sent, how="left")
    
    # Join macro if not empty
    if not macro.empty:
        feats = feats.join(macro, how="left")
    
    # Join flows if not empty
    if not flows.empty:
        feats = feats.join(flows, how="left")
    
    # Forward fill within each asset group
    feats = feats.groupby(level=1).apply(lambda df: df.fillna(method='ffill'))
    
    print(f"   ✅ Combined features: {feats.shape}")
    print(f"   Columns: {list(feats.columns)}")
    
    # Write to Parquet
    print("\n6. Writing to Parquet...")
    write_features_parquet(feats, cfg)
    
    print("\n" + "="*70)
    print("✅ Feature construction complete")
    print("="*70)
    
    return feats


if __name__ == "__main__":
    from alpha_lab.io.reader import load_config
    
    cfg = load_config('configs/default.yaml')
    feats = run(cfg)
    
    print(f"\nFeature matrix shape: {feats.shape}")
    print(f"Date range: {feats.index.get_level_values(0).min()} to {feats.index.get_level_values(0).max()}")

