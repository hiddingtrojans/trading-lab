#!/usr/bin/env python3
"""
Reconcile IBKR State
====================

Pulls fills, positions, and open trades from IBKR.
"""

import yaml
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ib_insync import IB
from alpha_lab.execute.ibkr_reconcile import pulls, to_df_fills, to_df_positions


def main():
    """Reconcile IBKR state."""
    # Load config
    cfg = yaml.safe_load(open('configs/ibkr.yaml'))
    
    # Connect to IBKR
    ib = IB()
    ib.connect(cfg['host'], cfg['port'], clientId=cfg['client_id'])
    
    print(f"✅ Connected to IBKR Gateway: {cfg['host']}:{cfg['port']}")
    print(f"📊 Account: {cfg['account']}")
    
    # Pull data
    fills, positions, trades = pulls(ib)
    
    # Convert to DataFrames
    fills_df = to_df_fills(fills)
    positions_df = to_df_positions(positions)
    
    # Save
    fills_df.to_csv('fills/ibkr_fills.csv', index=False)
    positions_df.to_csv('positions/ibkr_positions.csv', index=False)
    
    print(f"\n📊 Summary:")
    print(f"   Fills: {len(fills_df)}")
    print(f"   Positions: {len(positions_df)}")
    print(f"   Open Trades: {len(trades)}")
    
    if len(fills_df) > 0:
        print(f"\n✅ Recent Fills:")
        print(fills_df.tail(10))
    
    if len(positions_df) > 0:
        print(f"\n✅ Current Positions:")
        print(positions_df)
    
    ib.disconnect()


if __name__ == "__main__":
    main()

