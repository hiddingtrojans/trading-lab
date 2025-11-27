#!/usr/bin/env python3
"""
Quantile Gradient Boosting (QGB)
=================================

LightGBM quantile regression for return distribution forecasting.
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, Tuple


class QGB:
    """Quantile Gradient Boosting model."""
    
    def __init__(self, quantiles=(0.1, 0.5, 0.9), params=None):
        """
        Initialize QGB model.
        
        Args:
            quantiles: Quantiles to predict (default: 10%, 50%, 90%)
            params: Optional LightGBM params override
        """
        self.qs = quantiles
        self.models = {}
        
        # Base params
        base = dict(
            objective="quantile",
            learning_rate=0.05,
            num_leaves=15,
            min_data_in_leaf=200,
            verbose=-1
        )
        
        # Create params for each quantile
        self.params = {q: {**base, "alpha": q} | (params or {}) for q in self.qs}
    
    def fit(self, X, y):
        """
        Fit quantile models.
        
        Args:
            X: Feature matrix
            y: Target (forward returns)
        """
        for q in self.qs:
            lgb_train = lgb.Dataset(X, label=y)
            self.models[q] = lgb.train(
                self.params[q],
                lgb_train,
                num_boost_round=500
            )
    
    def predict(self, X) -> Dict[float, np.ndarray]:
        """
        Predict quantiles.
        
        Args:
            X: Feature matrix
            
        Returns:
            dict mapping quantile -> predictions
        """
        return {q: self.models[q].predict(X) for q in self.qs}


def signal_from_quantiles(preds: Dict[float, np.ndarray],
                          vol: np.ndarray,
                          index: int = -1) -> float:
    """
    Convert quantile predictions to position weight.
    
    Args:
        preds: Quantile predictions from QGB
        vol: Realized volatility
        index: Which prediction to use (default: -1 = last)
        
    Returns:
        Position weight (-0.3 to +0.3)
    """
    q10 = preds[0.1][index] if isinstance(preds[0.1], np.ndarray) else preds[0.1]
    q50 = preds[0.5][index] if isinstance(preds[0.5], np.ndarray) else preds[0.5]
    q90 = preds[0.9][index] if isinstance(preds[0.9], np.ndarray) else preds[0.9]
    
    vol_val = vol[index] if isinstance(vol, np.ndarray) else vol
    
    mu = q50
    spread = (q90 - q10)
    
    # Weight = (expected return / vol) * (spread / vol)
    # Clip to avoid extreme positions
    w = np.clip(mu / (vol_val + 1e-8), -0.3, 0.3) * np.clip(spread / (vol_val + 1e-8), 0.0, 1.0)
    
    return float(w)


# Test
if __name__ == "__main__":
    np.random.seed(42)
    
    # Generate synthetic data
    n = 1000
    X = np.random.randn(n, 10)
    y = X[:, :3].sum(axis=1) + np.random.randn(n) * 0.5
    
    print("="*70)
    print("QGB (QUANTILE GRADIENT BOOSTING) TEST")
    print("="*70)
    
    # Fit model
    qgb = QGB()
    qgb.fit(X, y)
    
    # Predict
    preds = qgb.predict(X[-10:])
    
    print("\nQuantile Predictions (last 10 samples):")
    print("-" * 70)
    for i in range(10):
        print(f"Sample {i+1}:")
        print(f"  10th percentile: {preds[0.1][i]:.3f}")
        print(f"  50th percentile (median): {preds[0.5][i]:.3f}")
        print(f"  90th percentile: {preds[0.9][i]:.3f}")
        print(f"  Actual: {y[-10+i]:.3f}")
    
    # Test signal generation
    vol = np.ones(10) * 0.02
    weight = signal_from_quantiles(preds, vol, index=-1)
    
    print(f"\nSignal Generation:")
    print(f"  Position Weight: {weight:.3f}")
    
    print("\n" + "="*70)
    print("✅ QGB test complete")
    print("="*70)

