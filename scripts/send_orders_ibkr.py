#!/usr/bin/env python3
"""
Send Orders to IBKR
===================

Reads latest signals and submits MOO orders.
"""

import yaml
import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from alpha_lab.execute.ibkr_router import submit_orders


def main():
    """Submit orders based on latest signals."""
    # Load config
    cfg = yaml.safe_load(open('configs/ibkr.yaml'))
    
    # Read signals (must have 'weight' column)
    signals = pd.read_csv('signals/latest.csv', index_col='asset')
    
    # Read reference prices
    prices = pd.read_csv('data/ref/close_ref.csv', index_col='asset')['close']
    
    # Read NAV
    nav = float(open('data/ref/nav.txt').read().strip())
    
    print(f"📊 Submitting orders for {len(signals)} assets")
    print(f"💰 NAV: ${nav:,.2f}")
    
    # Submit orders
    out = submit_orders(cfg, signals, prices, nav)
    
    # Save submitted orders
    out.to_csv('orders/ibkr_submitted.csv', index=False)
    
    print(f"✅ Submitted {len(out)} orders")
    print(out)


if __name__ == "__main__":
    main()

