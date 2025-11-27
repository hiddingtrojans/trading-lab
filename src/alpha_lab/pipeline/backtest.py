#!/usr/bin/env python3
"""
Walk-Forward Backtest
=====================

Backtest with proper embargo to prevent leakage.
"""

import pandas as pd
import numpy as np
from typing import Dict
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from alpha_lab.utils.cv import walk_forward_indices
from alpha_lab.portfolio.sizer import vol_target_weights
from alpha_lab.execute.simulator import simulate_moo


def backtest(cfg: Dict,
             features: pd.DataFrame,
             labels: pd.Series,
             model) -> pd.DataFrame:
    """
    Run walk-forward backtest.
    
    Args:
        cfg: Config dict
        features: Feature DataFrame (index: date x asset)
        labels: Forward returns (index: date x asset)
        model: Model with fit() and predict() methods
        
    Returns:
        DataFrame with daily returns
    """
    rets = []
    days = features.index.get_level_values(0).unique()
    
    print(f"📊 Starting walk-forward backtest")
    print(f"   Total days: {len(days)}")
    print(f"   Min train: {cfg['cv']['train_min_days']} days")
    print(f"   Folds: {cfg['cv']['folds']}")
    print(f"   Embargo: {cfg['cv']['embargo_days']} days")
    
    fold_num = 0
    
    for train_idx, test_idx in walk_forward_indices(
        days,
        min_train=cfg['cv']['train_min_days'],
        folds=cfg['cv']['folds'],
        embargo=cfg['cv']['embargo_days']
    ):
        fold_num += 1
        
        # Split data
        X_tr = features.iloc[train_idx]
        y_tr = labels.iloc[train_idx]
        X_te = features.iloc[test_idx]
        y_te = labels.iloc[test_idx]
        
        print(f"\n📈 Fold {fold_num}/{cfg['cv']['folds']}")
        print(f"   Train: {len(train_idx)} samples")
        print(f"   Test: {len(test_idx)} samples")
        
        # Fit model
        model.fit(X_tr.values, y_tr.values)
        
        # Predict
        pred = model.predict(X_te.values)
        
        # Convert predictions to weights
        w = vol_target_weights(pred, X_te, cfg)
        
        # Simulate MOO execution
        costs_bps = cfg['costs']['etf_bps']
        pnl = simulate_moo(w.unstack(), y_te, costs_bps=costs_bps)
        
        rets.append(pnl)
        
        # Fold stats
        fold_ret = pnl['ret'].sum()
        print(f"   Fold Return: {fold_ret:.2%}")
    
    # Combine all folds
    all_rets = pd.concat(rets).sort_index()
    
    return all_rets

