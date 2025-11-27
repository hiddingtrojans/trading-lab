#!/usr/bin/env python3
"""
Risk Controls
=============

Pre-trade risk checks and position limits.
"""

import pandas as pd
from typing import Dict


def pretrade_guard(asset: str, weight: float, cfg: Dict):
    """
    Pre-trade risk checks.
    
    Args:
        asset: Asset symbol
        weight: Position weight
        cfg: Config dict with risk limits
        
    Raises:
        ValueError: If risk limits breached
    """
    # Check per-asset cap
    per_asset_cap = cfg['risk']['per_asset_cap']
    if abs(weight) > per_asset_cap + 1e-9:
        raise ValueError(f"Per-asset cap breach: {asset} weight={weight:.3f} > cap={per_asset_cap}")
    
    # Check shorts allowed
    if not cfg['risk'].get('allow_shorts', True) and weight < 0:
        raise ValueError(f"Shorts disabled: {asset} weight={weight:.3f}")
    
    # Passed all checks
    return True


def check_gross_exposure(weights: pd.DataFrame, cfg: Dict):
    """Check total gross exposure."""
    import pandas as pd
    
    gross = weights.abs().sum()
    max_gross = cfg['risk']['max_gross']
    
    if gross > max_gross + 1e-6:
        raise ValueError(f"Gross exposure breach: {gross:.3f} > {max_gross}")
    
    return True

