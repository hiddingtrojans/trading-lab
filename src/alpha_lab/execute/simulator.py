#!/usr/bin/env python3
"""
Execution Simulator
===================

Simulates MOO execution with transaction costs.
"""

import pandas as pd
import numpy as np


def simulate_moo(weights: pd.DataFrame,
                 next_day_returns: pd.Series,
                 costs_bps: float = 2) -> pd.DataFrame:
    """
    Simulate Market-On-Open execution.
    
    Args:
        weights: DataFrame with index=date x asset, values=weights
        next_day_returns: Series with index=date x asset, values=returns
        costs_bps: Transaction costs in basis points
        
    Returns:
        DataFrame with daily returns
    """
    # Stack to align weights and returns
    aligned = (weights.stack().to_frame('w')
               .join(next_day_returns.stack().to_frame('r'), how='inner'))
    
    # Gross P&L (before costs)
    gross = (aligned['w'] * aligned['r']).groupby(level=0).sum()
    
    # Calculate turnover (change in weights)
    turn = (aligned['w']
            .groupby(level=1)
            .apply(lambda s: s.diff().abs().fillna(abs(s))))
    
    # Transaction costs
    costs = (turn.groupby(level=0).sum() * (costs_bps / 1e4))
    
    # Net daily returns
    daily = gross - costs.reindex(gross.index).fillna(0.0)
    
    return daily.to_frame('ret')

