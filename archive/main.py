#!/usr/bin/env python3
"""
Trading System - Unified CLI Launcher
======================================

Single entry point to run all trading strategies and tools.
"""

import sys
import os
import subprocess


BANNER = """
╔════════════════════════════════════════════════════════════════════╗
║                   TRADING SYSTEM LAUNCHER                          ║
╚════════════════════════════════════════════════════════════════════╝
"""

MENU = """
┌────────────────────────────────────────────────────────────────────┐
│  INTRADAY SCANNER (Recommended - Start Here)                       │
├────────────────────────────────────────────────────────────────────┤
│  [1] Unified Scanner               (Gap/Momentum/VWAP signals)     │
│  [2] After-Hours Movers            (Pre/post-market gaps)          │
│  [3] Backtest Intraday Signals     (Validate signals)              │
│                                                                     │
│  DAY TRADING BOT                                                    │
├────────────────────────────────────────────────────────────────────┤
│  [4] Test Day Trading Bot          (Validate 1000 trades)          │
│  [5] Paper Trading Bot             (Practice trading)              │
│  [6] Live Day Trading Bot          (Full bot - use after testing)  │
│                                                                     │
│  SYSTEMATIC TRADING (ETF Daily Signals - Low Alpha Currently)      │
├────────────────────────────────────────────────────────────────────┤
│  [7] Generate Daily Signals        (Build features + signals)      │
│  [8] Run Backtest                  (Test strategy performance)     │
│  [9] Submit Orders to IBKR         (Send MOO orders)               │
│  [10] Reconcile IBKR State         (Pull fills & positions)        │
│                                                                     │
│  LEAPS ANALYSIS (Long-term options)                                 │
├────────────────────────────────────────────────────────────────────┤
│  [11] Run LEAPS Analysis           (Find long-term options)        │
│                                                                     │
│  UTILITIES                                                          │
├────────────────────────────────────────────────────────────────────┤
│  [12] Build Russell 1000 Universe  (One-time setup)                │
│  [13] Build Russell 2000 Universe  (One-time setup)                │
│                                                                     │
│  SYSTEM                                                             │
├────────────────────────────────────────────────────────────────────┤
│  [0] Exit                                                           │
└────────────────────────────────────────────────────────────────────┘
"""


def activate_env():
    """Activate virtual environment."""
    activate_path = os.path.join(os.getcwd(), 'leaps_env', 'bin', 'activate')
    if not os.path.exists(activate_path):
        print("⚠️  Virtual environment not found. Please run from project root.")
        sys.exit(1)
    return activate_path


def run_command(cmd, description):
    """Run a command with proper environment."""
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}\n")
    
    # Build full command with environment activation and PYTHONPATH
    full_cmd = f"""
cd {os.getcwd()}
source leaps_env/bin/activate
export PYTHONPATH={os.getcwd()}/src
{cmd}
"""
    
    try:
        subprocess.run(full_cmd, shell=True, executable='/bin/bash')
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Main CLI launcher."""
    print(BANNER)
    
    while True:
        print(MENU)
        
        try:
            choice = input("Select option [0-13]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        
        print()
        
        # Intraday Scanner
        if choice == '1':
            run_command(
                "python scanner.py --mode intraday --universe liquid --top 10",
                "Intraday Scanner: Gap/Momentum/VWAP Signals"
            )
        
        elif choice == '2':
            run_command(
                "python scanner.py --mode after_hours --universe liquid",
                "After-Hours Movers Scanner"
            )
        
        elif choice == '3':
            run_command(
                "python backtest_intraday_signals.py",
                "Backtest Intraday Signals (Validate Performance)"
            )
        
        # Day Trading Bot
        elif choice == '4':
            run_command(
                "python scripts/run_1000trade_validation.py",
                "Day Trading: Validate Bot (1000 Trades)"
            )
        
        elif choice == '5':
            run_command(
                "python scripts/run_paper_trading.py",
                "Day Trading: Paper Trading Bot"
            )
        
        elif choice == '6':
            run_command(
                "python scripts/run_live_trading.py",
                "Day Trading: Live Bot (USE WITH CAUTION)"
            )
        
        # Systematic Trading
        elif choice == '7':
            run_command(
                "python scripts/live_daily.py --config configs/default.yaml",
                "Systematic: Generate Daily ETF Signals"
            )
        
        elif choice == '8':
            run_command(
                "python scripts/backtest_daily.py --config configs/default.yaml",
                "Systematic: Backtest ETF Strategy"
            )
        
        elif choice == '9':
            # Check if signals exist
            if not os.path.exists('signals/latest.csv'):
                print("❌ No signals found. Run option [7] first to generate signals.\n")
                continue
            
            run_command(
                "python scripts/send_orders_ibkr.py",
                "Systematic: Submit MOO Orders to IBKR"
            )
        
        elif choice == '10':
            run_command(
                "python scripts/reconcile_ibkr.py",
                "Systematic: Reconcile IBKR State"
            )
        
        # LEAPS
        elif choice == '11':
            symbol = input("Enter ticker symbol (or press Enter for AAPL): ").strip() or "AAPL"
            run_command(
                f"python scripts/run_leaps_analysis.py {symbol}",
                f"LEAPS Analysis for {symbol}"
            )
        
        # Utilities
        elif choice == '12':
            run_command(
                "python get_russell1000.py",
                "Building Russell 1000 Universe"
            )
        
        elif choice == '13':
            run_command(
                "python get_russell2000.py",
                "Building Russell 2000 Universe"
            )
        
        # Exit
        elif choice == '0':
            print("👋 Goodbye!\n")
            sys.exit(0)
        
        else:
            print("❌ Invalid option. Please select 0-13.\n")
        
        input("\n⏎ Press Enter to return to menu...")


if __name__ == "__main__":
    # Check if running from correct directory
    if not os.path.exists('leaps_env'):
        print("❌ Error: Must run from project root (where leaps_env/ is located)")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Expected: /Users/raulacedo/Desktop/scanner")
        sys.exit(1)
    
    main()

