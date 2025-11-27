#!/usr/bin/env python3
"""
HMM Regime Model (M11)
======================

Hidden Markov Model for regime classification.
"""

import numpy as np
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class RegimeHMM:
    """HMM for market regime detection."""
    
    def __init__(self, n_states: int = 3, seed: int = 7):
        self.n_states = n_states
        self.hmm = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=200,
            random_state=seed
        )
        self.scaler = StandardScaler()
        self.fitted = False
        
    def fit(self, X, y=None):
        """
        Fit HMM.
        
        Args:
            X: Features [returns, realized_vol, drawdown_flag, ...]
            y: Not used (unsupervised)
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit HMM
        self.hmm.fit(X_scaled)
        self.fitted = True
        
    def predict(self, X) -> np.ndarray:
        """
        Predict regime probabilities.
        
        Args:
            X: Features
            
        Returns:
            Array of regime probabilities (n_samples x n_states)
        """
        if not self.fitted:
            return np.zeros((len(X), self.n_states))
        
        X_scaled = self.scaler.transform(X)
        
        # Get posterior probabilities
        _, posteriors = self.hmm.score_samples(X_scaled)
        
        return posteriors  # Shape: (n_samples, n_states)
    
    def regime_probs(self, X) -> np.ndarray:
        """
        Get regime probabilities (alias for predict).
        
        Args:
            X: Features with columns [returns, realized_vol, drawdown_flag]
            
        Returns:
            Posterior probabilities (T x n_states)
        """
        return self.predict(X)

