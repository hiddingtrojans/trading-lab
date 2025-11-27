#!/usr/bin/env python3
"""
IBKR Reconciliation
===================

Pull fills, positions, and trades from IBKR Gateway.
"""

from ib_insync import IB
import pandas as pd
from typing import Tuple, List


def pulls(ib: IB) -> Tuple[List, List, List]:
    """
    Pull fills, positions, and open trades from IBKR.
    
    Args:
        ib: Connected IB instance
        
    Returns:
        (fills, positions, trades) tuple
    """
    fills = ib.fills()
    positions = ib.positions()
    trades = ib.openTrades()
    
    return fills, positions, trades


def to_df_fills(fills: List) -> pd.DataFrame:
    """
    Convert fills to DataFrame.
    
    Args:
        fills: List of (Fill, Contract, Execution) tuples
        
    Returns:
        DataFrame with fill details
    """
    rows = []
    
    for fill in fills:
        if len(fill) == 3:
            f, c, e = fill
        else:
            continue
        rows.append(dict(
            ts=e.time,
            symbol=c.symbol,
            side=e.side,
            qty=e.shares,
            price=e.price,
            commission=(f.commissionReport.commission or 0.0) if f.commissionReport else 0.0,
            execId=e.execId,
            orderId=e.orderId
        ))
    
    return pd.DataFrame(rows).sort_values('ts') if rows else pd.DataFrame()


def to_df_positions(positions: List) -> pd.DataFrame:
    """
    Convert positions to DataFrame.
    
    Args:
        positions: List of Position objects
        
    Returns:
        DataFrame with position details
    """
    rows = []
    
    for p in positions:
        rows.append(dict(
            symbol=p.contract.symbol,
            qty=p.position,
            avgCost=p.avgCost
        ))
    
    return pd.DataFrame(rows) if rows else pd.DataFrame()

