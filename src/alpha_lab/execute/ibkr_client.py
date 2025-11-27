#!/usr/bin/env python3
"""
IBKR Client
===========

Connection wrapper for Interactive Brokers Gateway.
"""

from ib_insync import IB, Stock
from typing import Dict


class IBKR:
    """IBKR Gateway client."""
    
    def __init__(self, cfg: Dict):
        """
        Initialize IBKR client.
        
        Args:
            cfg: Config dict with host, port, client_id
        """
        self.cfg = cfg
        self.ib = IB()
    
    def connect(self):
        """Connect to IB Gateway."""
        self.ib.connect(
            self.cfg['host'],
            self.cfg['port'],
            clientId=self.cfg['client_id']
        )
        self.ib.reqMarketDataType(self.cfg['market_data']['md_type'])
    
    def ensure(self):
        """Ensure connection is active."""
        if not self.ib.isConnected():
            self.connect()
    
    def contract_etf(self, symbol: str) -> Stock:
        """
        Create Stock contract for ETF.
        
        Args:
            symbol: ETF symbol
            
        Returns:
            Stock contract
        """
        return Stock(symbol, 'SMART', 'USD')
    
    def disconnect(self):
        """Disconnect from IB Gateway."""
        if self.ib.isConnected():
            self.ib.disconnect()

