#!/usr/bin/env python3
"""
Ensemble Classifier (M12)
=========================

LightGBM classifier for directional prediction.
"""

import numpy as np
import lightgbm as lgb
from typing import Optional


class Classifier:
    """LightGBM classifier for BUY/SELL/HOLD."""
    
    def __init__(self, params: Optional[dict] = None):
        """
        Initialize classifier.
        
        Args:
            params: Optional LightGBM params
        """
        default_params = dict(
            objective='multiclass',
            num_class=3,  # SELL=0, HOLD=1, BUY=2
            learning_rate=0.05,
            num_leaves=31,
            min_data_in_leaf=100,
            verbose=-1
        )
        
        self.params = default_params | (params or {})
        self.model = None
        
    def fit(self, X, y):
        """
        Fit classifier.
        
        Args:
            X: Feature matrix
            y: Labels (0=SELL, 1=HOLD, 2=BUY)
        """
        lgb_train = lgb.Dataset(X, label=y)
        
        self.model = lgb.train(
            self.params,
            lgb_train,
            num_boost_round=500,
            verbose_eval=False
        )
        
    def predict(self, X) -> np.ndarray:
        """
        Predict class probabilities.
        
        Args:
            X: Feature matrix
            
        Returns:
            Array of probabilities (n_samples x 3) for [SELL, HOLD, BUY]
        """
        if self.model is None:
            # Return uniform probabilities
            return np.full((len(X), 3), 1/3)
        
        return self.model.predict(X)
    
    def predict_signal(self, X) -> np.ndarray:
        """
        Predict directional signal (-1=SELL, 0=HOLD, +1=BUY).
        
        Args:
            X: Feature matrix
            
        Returns:
            Signal array
        """
        proba = self.predict(X)
        classes = np.argmax(proba, axis=1)  # 0, 1, or 2
        
        # Convert to -1, 0, +1
        return classes - 1

