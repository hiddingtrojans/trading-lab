#!/usr/bin/env python3
"""
IBKR Order Router
=================

Submit MOO/MOC orders via IBKR Gateway.
"""

from ib_insync import MarketOrder
import math
import pandas as pd
from typing import Dict
from .ibkr_client import IBKR
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from alpha_lab.risk.controls import pretrade_guard


def _round_shares(qty_float: float) -> int:
    """Round to whole shares."""
    return int(math.floor(abs(qty_float)))


def _moo(qty: int) -> MarketOrder:
    """Create Market-On-Open order."""
    o = MarketOrder('BUY' if qty > 0 else 'SELL', abs(int(qty)))
    o.tif = 'OPG'   # Market-On-Open
    return o


def _moc(qty: int) -> MarketOrder:
    """Create Market-On-Close order."""
    o = MarketOrder('BUY' if qty > 0 else 'SELL', abs(int(qty)))
    o.tif = 'MOC'   # Market-On-Close (venue support varies)
    return o


def submit_orders(cfg: Dict,
                  signals_df: pd.DataFrame,
                  prices_ref: pd.Series,
                  nav: float) -> pd.DataFrame:
    """
    Submit orders to IBKR based on signals.
    
    Args:
        cfg: IBKR config dict
        signals_df: DataFrame with index='asset', col='weight' for next session
        prices_ref: Reference price per asset (prior close)
        nav: Account equity (NAV)
        
    Returns:
        DataFrame with submitted orders
    """
    ib = IBKR(cfg)
    ib.ensure()
    
    logs = []
    
    for asset, row in signals_df.iterrows():
        w = float(row['weight'])
        
        if abs(w) < 1e-6:
            continue
        
        # Pre-trade risk check
        try:
            pretrade_guard(asset, w, cfg)
        except ValueError as e:
            print(f"⚠️  Risk guard failed for {asset}: {e}")
            continue
        
        # Get reference price
        px = float(prices_ref.get(asset, 0.0))
        if px <= 0:
            print(f"⚠️  No price for {asset}, skipping")
            continue
        
        # Calculate notional
        notional = nav * max(min(w, cfg['risk']['per_asset_cap']),
                            -cfg['risk']['per_asset_cap'])
        
        # Calculate shares
        qty = _round_shares(notional / px)
        
        if qty == 0:
            continue
        
        # Create contract
        contract = ib.contract_etf(asset)
        
        # Create MOO order
        order = _moo(qty if w > 0 else -qty)
        
        # Submit order
        trade = ib.ib.placeOrder(contract, order)
        
        logs.append(dict(
            asset=asset,
            qty=qty if w > 0 else -qty,
            tif=order.tif,
            oid=trade.order.orderId
        ))
        
        print(f"✅ Submitted {order.tif}: {qty if w > 0 else -qty:+d} {asset}")
    
    return pd.DataFrame(logs)

