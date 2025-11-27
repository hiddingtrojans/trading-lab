#!/usr/bin/env python3
"""
Position Sizing Module
======================

Calculates the optimal trade size based on risk tolerance and technical levels.
Implements 'Fixed Fractional Risk' and 'Kelly Criterion' logic.

Usage:
    sizer = PositionSizer(account_equity=200000)
    size = sizer.calculate_size(entry=150.0, stop=145.0, risk_pct=0.01)
"""

import math
from typing import Dict

class PositionSizer:
    """Professional Risk Management & Sizing Engine."""
    
    def __init__(self, account_equity: float = 200000.0):
        self.equity = account_equity
        
    def calculate_size(self, entry: float, stop: float, risk_pct: float = 0.01, win_rate: float = 0.60, payoff: float = 2.0) -> Dict:
        """
        Calculate position size.
        
        Args:
            entry: Entry price
            stop: Stop loss price
            risk_pct: % of equity to risk (default 1%)
            win_rate: Historical win rate of strategy (for Kelly)
            payoff: Profit factor / Ratio (for Kelly)
            
        Returns:
            Dict with sizing details
        """
        if entry <= 0 or stop <= 0 or entry <= stop:
            return {'shares': 0, 'reason': 'Invalid Price/Stop'}
            
        # 1. Fixed Fractional Risk (The standard)
        risk_per_share = entry - stop
        total_risk_amount = self.equity * risk_pct
        
        shares_risk_based = int(total_risk_amount / risk_per_share)
        
        # 2. Kelly Criterion (The optimizer)
        # Kelly % = W - (1 - W) / R
        # Half-Kelly is safer for real markets
        kelly_pct = win_rate - (1 - win_rate) / payoff
        half_kelly = kelly_pct / 2
        
        # If Kelly suggests negative or huge leverage, cap it
        if half_kelly < 0:
            kelly_allocation = 0
        elif half_kelly > 0.25: # Cap max allocation at 25% per trade for safety
            kelly_allocation = 0.25
        else:
            kelly_allocation = half_kelly
            
        # Convert Kelly allocation % to shares
        # Kelly tells you how much EQUITY to bet, not risk
        # Shares = (Equity * Kelly%) / Entry
        shares_kelly = int((self.equity * kelly_allocation) / entry) if kelly_allocation > 0 else 0
        
        # 3. Select Conservative Option
        # Use Risk-Based sizing but capped by Kelly if Kelly is lower (rare) 
        # or cap by max portfolio weight (e.g., 20%)
        
        max_shares_by_capital = int((self.equity * 0.20) / entry) # Max 20% position
        
        final_shares = min(shares_risk_based, max_shares_by_capital)
        
        # Calculate outcome metrics
        cost_basis = final_shares * entry
        dollar_risk = final_shares * risk_per_share
        
        return {
            'shares': final_shares,
            'cost_basis': cost_basis,
            'risk_amount': dollar_risk,
            'risk_pct_actual': (dollar_risk / self.equity) * 100,
            'kelly_suggestion': shares_kelly,
            'stop_width_pct': (risk_per_share / entry) * 100
        }

def vol_target_weights(predictions, features, cfg):
    """
    Convert model predictions to portfolio weights using volatility targeting.
    
    Used by walk-forward backtest for position sizing.
    
    Args:
        predictions: Model output (alpha scores)
        features: DataFrame with realized_vol column
        cfg: Config dict with 'vol_target' (e.g., 0.10 for 10% annualized)
        
    Returns:
        Series of portfolio weights (same index as predictions)
    """
    import pandas as pd
    import numpy as np
    
    vol_target = cfg.get('vol_target', 0.10)  # 10% annualized target
    
    # Get volatility from features
    if 'realized_vol_20d' in features.columns:
        vol = features['realized_vol_20d'].values
    else:
        vol = np.full(len(predictions), 0.15)  # Fallback to 15%
    
    # Prevent division by zero
    vol = np.maximum(vol, 0.01)
    
    # Scale by vol target
    weights = predictions * (vol_target / vol)
    
    # Clip to reasonable bounds
    weights = np.clip(weights, -0.5, 0.5)
    
    return pd.Series(weights, index=features.index)


if __name__ == "__main__":
    sizer = PositionSizer(100000) # $100k account
    res = sizer.calculate_size(150.0, 147.0, risk_pct=0.01) # $3 stop (2%)
    
    print(f"Entry: $150 | Stop: $147")
    print(f"Risking 1% of $100k ($1,000)")
    print(f"Recommended Size: {res['shares']} shares")
    print(f"Cost Basis: ${res['cost_basis']:,.2f}")
    print(f"Actual Risk: ${res['risk_amount']:.2f}")
