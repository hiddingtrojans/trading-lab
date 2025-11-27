#!/usr/bin/env python3
"""
Trend Kalman Filter (M3)
========================

State-space model for trend extraction.
"""

import numpy as np
from pykalman import KalmanFilter
from typing import Tuple


class TrendKalman:
    """Kalman filter for trend extraction."""
    
    def __init__(self, transition_cov: float = 0.01, observation_cov: float = 1.0):
        self.transition_cov = transition_cov
        self.observation_cov = observation_cov
        self.kf = None
        self.state_means = None
        
    def fit(self, X, y):
        """
        Fit Kalman filter.
        
        Args:
            X: Features (not used, for API compatibility)
            y: Price series or returns
        """
        # State: [level, trend]
        self.kf = KalmanFilter(
            transition_matrices=[[1, 1], [0, 1]],
            observation_matrices=[[1, 0]],
            transition_covariance=self.transition_cov * np.eye(2),
            observation_covariance=self.observation_cov,
            initial_state_mean=[y[0], 0],
            initial_state_covariance=np.eye(2)
        )
        
        self.state_means, _ = self.kf.filter(y)
        
    def predict(self, X) -> np.ndarray:
        """
        Predict next value (trend component).
        
        Args:
            X: Features (not used)
            
        Returns:
            Predicted trends (same length as X)
        """
        if self.state_means is None:
            return np.zeros(len(X))
        
        # Return trend component (state[1])
        # For prediction, use last N trends
        trends = self.state_means[:, 1]
        
        # Return trends aligned with input length
        if len(trends) >= len(X):
            return trends[-len(X):]
        else:
            # Pad if needed
            return np.concatenate([np.zeros(len(X) - len(trends)), trends])

