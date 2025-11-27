#!/usr/bin/env python3
"""
Walk-Forward Cross-Validation with Embargo
===========================================

Prevents look-ahead bias in backtesting.
"""

import numpy as np
import pandas as pd
from typing import Iterator, Tuple


def walk_forward_indices(days: pd.Index, 
                         min_train: int = 504,
                         folds: int = 5,
                         embargo: int = 21) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """
    Generate walk-forward train/test indices with embargo.
    
    Args:
        days: Sorted index of dates
        min_train: Minimum training days
        folds: Number of test folds
        embargo: Days to skip between train and test (prevents leakage)
        
    Yields:
        (train_indices, test_indices) tuples
    """
    days = pd.Index(days).sort_values()
    n = len(days)
    fold_size = max(1, (n - min_train) // folds)
    
    for k in range(folds):
        train_end = min_train + k * fold_size
        test_start = train_end + embargo
        test_end = min(test_start + fold_size, n)
        
        if test_start >= n:
            break
        
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)
        
        yield train_idx, test_idx

