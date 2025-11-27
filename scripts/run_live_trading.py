#!/usr/bin/env python3
"""
Live Trading Bot Runner
========================

Entry point for the live trading bot.
"""

import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from trading.day_trading_bot import main

if __name__ == "__main__":
    asyncio.run(main())
