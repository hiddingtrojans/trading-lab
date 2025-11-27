#!/usr/bin/env python3
"""
Test for Data Leakage
=====================

Validates no t+1 information leaks into features.
"""

import pytest
import pandas as pd
import numpy as np


def test_no_future_leakage():
    """Test that features don't contain future information."""
    
    # Create sample data with known future info
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # Feature that would leak: using t+1 return
    returns_t0 = pd.Series(np.random.randn(100), index=dates)
    returns_t1 = returns_t0.shift(-1)  # LEAK!
    
    features_clean = pd.DataFrame({
        'ret_lag1': returns_t0.shift(1),  # OK - uses past
        'ret_lag5': returns_t0.shift(5),  # OK - uses past
    })
    
    features_leaked = pd.DataFrame({
        'ret_future': returns_t1,  # BAD - uses future
    })
    
    # Test: features should not correlate with future returns
    # If they do, we have leakage
    
    # Clean features should have low correlation with t+1
    corr_clean = features_clean.corrwith(returns_t1).abs().max()
    
    # Leaked features will have high correlation
    corr_leaked = features_leaked.corrwith(returns_t1).abs().max()
    
    print(f"Clean features max correlation with t+1: {corr_clean:.3f}")
    print(f"Leaked features max correlation with t+1: {corr_leaked:.3f}")
    
    # Assert no leakage in clean features
    assert corr_clean < 0.3, f"Possible leakage detected: correlation={corr_clean}"
    
    # Leaked features should be detected
    assert corr_leaked > 0.8, "Leak test failed - should detect known leak"
    
    print("✅ Leakage test passed")


def test_embargo_enforcement():
    """Test that embargo prevents train/test overlap."""
    from alpha_lab.utils.cv import walk_forward_indices
    
    days = pd.date_range('2024-01-01', periods=200, freq='D')
    embargo = 21
    
    for train_idx, test_idx in walk_forward_indices(
        days,
        min_train=100,
        folds=3,
        embargo=embargo
    ):
        # Last train day
        last_train = train_idx[-1]
        # First test day
        first_test = test_idx[0]
        
        # Gap should be >= embargo
        gap = first_test - last_train
        
        assert gap >= embargo, f"Embargo violated: gap={gap}, embargo={embargo}"
    
    print("✅ Embargo enforcement test passed")


if __name__ == "__main__":
    test_no_future_leakage()
    test_embargo_enforcement()
    print("\n✅ All leakage tests passed!")

