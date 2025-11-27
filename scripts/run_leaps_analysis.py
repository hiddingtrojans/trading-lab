#!/usr/bin/env python3
"""
LEAPS Analysis Runner
=====================

Entry point for the LEAPS analysis system.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from leaps.complete_leaps_system import main

if __name__ == "__main__":
    main()
