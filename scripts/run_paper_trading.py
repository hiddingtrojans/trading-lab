#!/usr/bin/env python3
"""
Paper Trading Bot Runner
========================

Entry point for the paper trading bot with dashboard.
"""

import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from trading.simple_paper_bot import main

if __name__ == "__main__":
    asyncio.run(main())
