#!/usr/bin/env python3
"""
Stock Discovery - Find growth stocks before the crowd.

Usage:
    python discover.py                    # Quick scan (300 stocks)
    python discover.py --scan 500         # Scan 500 stocks
    python discover.py --scan 1000        # Deeper scan
    python discover.py --min-moat 7       # Only show strong moats
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from research.smart_discovery import smart_discover


def main():
    parser = argparse.ArgumentParser(description='Discover growth stocks')
    parser.add_argument('--scan', type=int, default=300, help='Number of stocks to scan')
    parser.add_argument('--min-moat', type=int, default=5, help='Minimum moat score (1-10)')
    parser.add_argument('--no-telegram', action='store_true', help='Skip Telegram alert')
    
    args = parser.parse_args()
    
    print(f"\n🔍 Scanning {args.scan} stocks for opportunities...\n")
    
    results = smart_discover(
        max_scan=args.scan,
        min_moat_score=args.min_moat,
        send_telegram=not args.no_telegram,
    )
    
    if results:
        print(f"\n✅ Found {len(results)} vetted opportunities")
    else:
        print("\n😕 No stocks passed the filters. Try --scan with more stocks.")


if __name__ == "__main__":
    main()

