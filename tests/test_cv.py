#!/usr/bin/env python3
"""
Test Cross-Validation
=====================

Validates CV split logic.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from alpha_lab.utils.cv import walk_forward_indices


def test_walk_forward_splits():
    """Test walk-forward splitting."""
    days = pd.date_range('2024-01-01', periods=600, freq='D')
    
    splits = list(walk_forward_indices(
        days,
        min_train=504,  # ~2 years
        folds=3,
        embargo=21
    ))
    
    assert len(splits) > 0, "No splits generated"
    
    for i, (train_idx, test_idx) in enumerate(splits):
        print(f"\nFold {i+1}:")
        print(f"  Train: {len(train_idx)} days")
        print(f"  Test: {len(test_idx)} days")
        print(f"  Gap: {test_idx[0] - train_idx[-1]} days")
        
        # Validate no overlap
        assert len(set(train_idx) & set(test_idx)) == 0, "Train/test overlap detected"
        
        # Validate embargo
        assert test_idx[0] - train_idx[-1] >= 21, "Embargo violation"
        
        # Validate ordering
        assert train_idx[-1] < test_idx[0], "Test before train"
    
    print(f"\n✅ Generated {len(splits)} valid splits")


def test_expanding_window():
    """Test that training window expands (not rolling)."""
    days = pd.date_range('2024-01-01', periods=700, freq='D')
    
    splits = list(walk_forward_indices(
        days,
        min_train=504,
        folds=3,
        embargo=21
    ))
    
    # Check train size increases each fold
    prev_train_size = 0
    for train_idx, test_idx in splits:
        train_size = len(train_idx)
        assert train_size > prev_train_size, "Training window not expanding"
        prev_train_size = train_size
    
    print("✅ Expanding window validated")


if __name__ == "__main__":
    test_walk_forward_splits()
    test_expanding_window()
    print("\n✅ All CV tests passed!")

