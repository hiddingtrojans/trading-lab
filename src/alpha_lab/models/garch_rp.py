#!/usr/bin/env python3
"""
GARCH Risk Premium Model (M5)
==============================

GARCH-based volatility risk premium forecasting.
"""

import numpy as np
from arch import arch_model
import warnings
warnings.filterwarnings('ignore')


class GARCH_RP:
    """GARCH model for risk premium estimation."""
    
    def __init__(self, p: int = 1, q: int = 1):
        self.p = p
        self.q = q
        self.model = None
        self.fitted_model = None
        
    def fit(self, X, y):
        """
        Fit GARCH model.
        
        Args:
            X: Features (not used, for API compatibility)
            y: Return series (percentage)
        """
        # Convert to percentage if not already
        returns = y * 100 if np.abs(y).mean() < 1 else y
        
        # Fit GARCH(1,1)
        self.model = arch_model(
            returns,
            vol='Garch',
            p=self.p,
            q=self.q,
            dist='normal'
        )
        
        self.fitted_model = self.model.fit(disp='off', show_warning=False)
        
    def predict(self, X) -> np.ndarray:
        """
        Predict risk premium (forecast vol - realized vol).
        
        Args:
            X: Features
            
        Returns:
            Risk premium forecast
        """
        if self.fitted_model is None:
            return np.zeros(len(X))
        
        # Forecast next-day variance
        forecast = self.fitted_model.forecast(horizon=1)
        forecast_vol = np.sqrt(forecast.variance.iloc[-1, 0])
        
        # Realized vol (from conditional volatility)
        realized_vol = self.fitted_model.conditional_volatility.iloc[-1]
        
        # Risk premium = forecast - realized
        rp = forecast_vol - realized_vol
        
        # Return array same length as X
        return np.full(len(X), rp)

