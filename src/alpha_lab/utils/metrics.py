#!/usr/bin/env python3
"""
Performance Metrics
===================

Standard quantitative performance metrics.
"""

import numpy as np
import pandas as pd


def sharpe(daily_returns: pd.Series) -> float:
    """
    Calculate annualized Sharpe ratio.
    
    Args:
        daily_returns: Daily return series
        
    Returns:
        Annualized Sharpe ratio
    """
    mu = daily_returns.mean() * 252
    sd = daily_returns.std() * (252 ** 0.5)
    return 0.0 if sd == 0 else mu / sd


def max_drawdown(series: pd.Series) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        series: Return series or equity curve
        
    Returns:
        Maximum drawdown (negative value)
    """
    cum = (1 + series).cumprod()
    peak = cum.cummax()
    dd = cum / peak - 1
    return dd.min()


def sortino_ratio(daily_returns: pd.Series, target_return: float = 0.0) -> float:
    """
    Calculate Sortino ratio (downside deviation only).
    
    Args:
        daily_returns: Daily return series
        target_return: Target return threshold
        
    Returns:
        Annualized Sortino ratio
    """
    excess = daily_returns - target_return
    downside = excess[excess < 0].std()
    
    if downside == 0:
        return 0.0
    
    return (daily_returns.mean() * 252) / (downside * np.sqrt(252))


def calmar_ratio(daily_returns: pd.Series) -> float:
    """
    Calculate Calmar ratio (return / max drawdown).
    
    Args:
        daily_returns: Daily return series
        
    Returns:
        Calmar ratio
    """
    annual_return = daily_returns.mean() * 252
    mdd = abs(max_drawdown(daily_returns))
    
    return annual_return / mdd if mdd > 0 else 0.0

