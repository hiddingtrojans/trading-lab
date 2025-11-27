#!/usr/bin/env python3
"""
Live Daily Signal Generation
=============================

Generate signals for next trading session.
"""

import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from alpha_lab.io.reader import load_config
from alpha_lab.pipeline.build_features import run as build_features
from alpha_lab.pipeline.generate_signals import generate_signals
from alpha_lab.io.writer import write_signals


def main():
    """Generate live signals."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/default.yaml')
    args = parser.parse_args()
    
    # Load config
    cfg = load_config(args.config)
    
    print("="*70)
    print("🎯 LIVE DAILY SIGNAL GENERATION")
    print("="*70)
    print(f"\nUniverse: {cfg['universe']}")
    print(f"Signal Cutoff: {cfg['signal_cutoff_utc']} UTC")
    
    # Build features
    print("\n🏗️  Building features...")
    features = build_features(cfg)
    
    # Generate signals
    print("\n🎯 Generating signals...")
    signals = generate_signals(cfg, features)
    
    print("\n📊 SIGNALS FOR NEXT SESSION:")
    print("="*70)
    print(signals)
    
    # Write signals to disk
    print("\n💾 Saving signals...")
    write_signals(signals)
    
    print("\n✅ Signals ready for execution")
    print("   Next: python scripts/send_orders_ibkr.py")


if __name__ == "__main__":
    main()

