#!/usr/bin/env python3
"""
Daily Backtest Script
=====================

Run walk-forward backtest on ETF universe.
"""

import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from alpha_lab.io.reader import load_config
from alpha_lab.pipeline.build_features import run as build_features
from alpha_lab.pipeline.backtest import backtest
from alpha_lab.models.qgb import QGB
from alpha_lab.utils.metrics import sharpe, max_drawdown
import pandas as pd


def main():
    """Run backtest."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/default.yaml')
    args = parser.parse_args()
    
    # Load config
    cfg = load_config(args.config)
    
    print("="*70)
    print("📊 DAILY STRATEGY BACKTEST")
    print("="*70)
    print(f"\nUniverse: {cfg['universe']}")
    print(f"Models: {[m['id'] for m in cfg['models']]}")
    
    # Build features
    print("\n🏗️  Building features...")
    features = build_features(cfg)
    
    # Create labels (forward 1-day returns)
    print("\n📈 Creating labels...")
    prices = features['ret_1d'].unstack()  # Unstack to date x asset
    labels = prices.shift(-1).stack()  # Forward return
    
    # Align features and labels
    aligned = features.join(labels.to_frame('fwd_ret'), how='inner')
    X = aligned.drop('fwd_ret', axis=1)
    y = aligned['fwd_ret']
    
    # Drop NaN
    valid_idx = ~y.isna()
    X = X[valid_idx]
    y = y[valid_idx]
    
    print(f"   Total samples: {len(y)}")
    
    # Run backtest with QGB model
    print("\n🧪 Running walk-forward backtest...")
    model = QGB()
    
    rets = backtest(cfg, X, y, model)
    
    # Calculate metrics
    print("\n📊 BACKTEST RESULTS:")
    print("="*70)
    print(f"Total Days: {len(rets)}")
    print(f"Total Return: {rets['ret'].sum():.2%}")
    print(f"Sharpe Ratio: {sharpe(rets['ret']):.2f}")
    print(f"Max Drawdown: {max_drawdown(rets['ret']):.2%}")
    print(f"Win Rate: {(rets['ret'] > 0).mean():.1%}")
    
    # Save equity curve
    from alpha_lab.io.writer import write_equity_curve
    write_equity_curve(rets['ret'])
    
    print("="*70)
    print("✅ Backtest complete")


if __name__ == "__main__":
    main()

