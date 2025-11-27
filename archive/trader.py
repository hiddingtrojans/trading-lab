#!/usr/bin/env python3
"""
Unified Trading System Launcher
================================

One command to access all three trading systems:
1. Day Trading Bot (Humble Trader gaps)
2. LEAPS Options Analysis
3. Intraday Scanner (quantitative)

Plus systematic trading and utilities.
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime
import pytz

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print main banner."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}                    UNIFIED TRADING SYSTEM{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

def print_market_status():
    """Show current market status."""
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    
    # Check market hours
    is_weekend = now.weekday() >= 5
    is_premarket = 4 <= now.hour < 9 or (now.hour == 9 and now.minute < 30)
    is_market_hours = (now.hour == 9 and now.minute >= 30) or (10 <= now.hour < 16)
    is_afterhours = 16 <= now.hour < 20
    
    status = "CLOSED"
    status_color = Colors.RED
    
    if is_weekend:
        status = "WEEKEND"
        status_color = Colors.YELLOW
    elif is_premarket:
        status = "PRE-MARKET"
        status_color = Colors.YELLOW
    elif is_market_hours:
        status = "OPEN"
        status_color = Colors.GREEN
    elif is_afterhours:
        status = "AFTER-HOURS"
        status_color = Colors.YELLOW
    
    print(f"{Colors.BOLD}Time:{Colors.END} {now.strftime('%I:%M %p ET')} | "
          f"{Colors.BOLD}Market:{Colors.END} {status_color}{status}{Colors.END}\n")

def run_command(cmd, description):
    """Run a command with proper environment."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.GREEN}▶ {description}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    # Build full command with environment activation
    full_cmd = f"""
cd {os.getcwd()}
source leaps_env/bin/activate
export PYTHONPATH={os.getcwd()}/src
{cmd}
"""
    
    try:
        subprocess.run(full_cmd, shell=True, executable='/bin/bash')
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⏹ Stopped by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")

def show_main_menu():
    """Display main interactive menu."""
    print_banner()
    print_market_status()
    
    print(f"{Colors.BOLD}┌────────────────────────────────────────────────────────────────────┐{Colors.END}")
    print(f"{Colors.BOLD}│  MAIN STRATEGIES                                                   │{Colors.END}")
    print(f"{Colors.BOLD}├────────────────────────────────────────────────────────────────────┤{Colors.END}")
    print(f"{Colors.BOLD}│  {Colors.GREEN}[1]{Colors.END} Intelligent Analysis   {Colors.BOLD}(All 3 systems combined){Colors.END}           │")
    print(f"{Colors.BOLD}│  {Colors.GREEN}[2]{Colors.END} Day Trading Bot        {Colors.BOLD}(Gaps, VWAP, Humble Trader style){Colors.END}    │")
    print(f"{Colors.BOLD}│  {Colors.GREEN}[3]{Colors.END} LEAPS Options          {Colors.BOLD}(Long-term options analysis){Colors.END}        │")
    print(f"{Colors.BOLD}│  {Colors.GREEN}[4]{Colors.END} Intraday Scanner       {Colors.BOLD}(Quantitative signals){Colors.END}              │")
    print(f"{Colors.BOLD}│                                                                    │{Colors.END}")
    print(f"{Colors.BOLD}│  COMPLETE WORKFLOWS                                                │{Colors.END}")
    print(f"{Colors.BOLD}├────────────────────────────────────────────────────────────────────┤{Colors.END}")
    print(f"{Colors.BOLD}│  {Colors.BLUE}[5]{Colors.END} Morning Routine        {Colors.BOLD}(All pre-market analysis){Colors.END}           │")
    print(f"{Colors.BOLD}│  {Colors.BLUE}[6]{Colors.END} Full Day Trading       {Colors.BOLD}(Complete day trading workflow){Colors.END}     │")
    print(f"{Colors.BOLD}│  {Colors.BLUE}[7]{Colors.END} Evening Analysis       {Colors.BOLD}(After-hours + next day prep){Colors.END}       │")
    print(f"{Colors.BOLD}│                                                                    │{Colors.END}")
    print(f"{Colors.BOLD}│  VALIDATION & TESTING                                              │{Colors.END}")
    print(f"{Colors.BOLD}├────────────────────────────────────────────────────────────────────┤{Colors.END}")
    print(f"{Colors.BOLD}│  {Colors.GREEN}[8]{Colors.END} Live Validator         {Colors.BOLD}(Real signals, you execute) ⭐{Colors.END}      │")
    print(f"{Colors.BOLD}│  {Colors.YELLOW}[9]{Colors.END} Historical Backtest    {Colors.BOLD}(Test on past data){Colors.END}                │")
    print(f"{Colors.BOLD}│  {Colors.YELLOW}[10]{Colors.END} Backtest Scanner      {Colors.BOLD}(Scanner validation){Colors.END}               │")
    print(f"{Colors.BOLD}│  {Colors.YELLOW}[11]{Colors.END} Paper Trading         {Colors.BOLD}(Auto bot, paper account){Colors.END}          │")
    print(f"{Colors.BOLD}│                                                                    │{Colors.END}")
    print(f"{Colors.BOLD}│  SYSTEMATIC TRADING                                                │{Colors.END}")
    print(f"{Colors.BOLD}├────────────────────────────────────────────────────────────────────┤{Colors.END}")
    print(f"{Colors.BOLD}│  [12] ETF Signals          (Daily signals - low alpha currently)  │{Colors.END}")
    print(f"{Colors.BOLD}│  [13] Submit Orders        (Send to IBKR)                          │{Colors.END}")
    print(f"{Colors.BOLD}│  [14] Reconcile            (Track positions)                       │{Colors.END}")
    print(f"{Colors.BOLD}│                                                                    │{Colors.END}")
    print(f"{Colors.BOLD}│  UTILITIES                                                         │{Colors.END}")
    print(f"{Colors.BOLD}├────────────────────────────────────────────────────────────────────┤{Colors.END}")
    print(f"{Colors.BOLD}│  [15] Portfolio Tracker    (All positions unified view)           │{Colors.END}")
    print(f"{Colors.BOLD}│  [16] Build Universes      (Russell 1000/2000 one-time setup)     │{Colors.END}")
    print(f"{Colors.BOLD}│  [17] System Status        (Check what's installed/working)       │{Colors.END}")
    print(f"{Colors.BOLD}│  [18] Help & Docs          (Open documentation)                    │{Colors.END}")
    print(f"{Colors.BOLD}│                                                                    │{Colors.END}")
    print(f"{Colors.BOLD}│  [0] Exit                                                          │{Colors.END}")
    print(f"{Colors.BOLD}└────────────────────────────────────────────────────────────────────┘{Colors.END}\n")

def morning_routine():
    """Complete morning pre-market routine."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🌅 MORNING ROUTINE - PRE-MARKET ANALYSIS{Colors.END}\n")
    print("This will run:")
    print("  1. After-hours movers scanner")
    print("  2. Gap-up scanner (day trading bot)")
    print("  3. LEAPS opportunities check")
    print("  4. Intraday signals prep\n")
    
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.END}")
    
    # After-hours movers
    run_command(
        "python scanner.py --mode after_hours --universe liquid --save",
        "Step 1/4: Scanning After-Hours Movers"
    )
    
    print(f"\n{Colors.GREEN}✓ After-hours scan complete{Colors.END}")
    print("Review: data/output/after_hours_signals_*.csv\n")
    input(f"{Colors.YELLOW}Press Enter to continue to gap scanner...{Colors.END}")
    
    # Note about day trading bot
    print(f"\n{Colors.BOLD}Step 2/4: Gap Scanner{Colors.END}")
    print("The day trading bot will automatically scan for gaps when you start it.")
    print("We'll prepare the watchlist now...\n")
    
    # Quick LEAPS check on top movers
    print(f"\n{Colors.BOLD}Step 3/4: LEAPS Quick Check{Colors.END}")
    print("Enter tickers to check for LEAPS (comma-separated), or press Enter to skip:")
    tickers = input("> ").strip()
    
    if tickers:
        run_command(
            f"python scripts/run_leaps_analysis.py --batch {tickers.replace(',', ' ')}",
            "Analyzing LEAPS Opportunities"
        )
    
    # Intraday prep
    print(f"\n{Colors.BOLD}Step 4/4: Intraday Scanner Prep{Colors.END}")
    print("Building watchlist for intraday signals...\n")
    
    run_command(
        "python scanner.py --mode intraday --universe liquid --top 20 --save",
        "Pre-Market Intraday Scan"
    )
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓✓✓ MORNING ROUTINE COMPLETE{Colors.END}")
    print("\nReview outputs in data/output/ and prepare your watchlist.")
    print(f"\nRecommended next: Start day trading bot (option 5) at 9:30 AM\n")

def full_day_trading():
    """Complete day trading workflow."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}📈 FULL DAY TRADING WORKFLOW{Colors.END}\n")
    print("This starts the day trading bot with:")
    print("  • Pre-market gap scanning")
    print("  • VWAP entry signals")
    print("  • Risk management (dollar stops)")
    print("  • Position monitoring")
    print("  • Web dashboard (localhost:5000)")
    print("\nBest used: 9:30 AM - 4:00 PM ET\n")
    
    choice = input(f"Start in {Colors.GREEN}[P]aper{Colors.END} or {Colors.RED}[L]ive{Colors.END} mode? (P/L): ").strip().upper()
    
    if choice == 'L':
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  WARNING: LIVE TRADING MODE{Colors.END}")
        print("This will trade with REAL MONEY.")
        confirm = input("Type 'YES' to confirm: ").strip()
        if confirm != 'YES':
            print("Cancelled.")
            return
        run_command(
            "python scripts/run_live_trading.py",
            "Starting LIVE Day Trading Bot"
        )
    else:
        run_command(
            "python scripts/run_paper_trading.py",
            "Starting Paper Trading Bot"
        )

def evening_analysis():
    """Evening after-hours analysis."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🌆 EVENING ANALYSIS - AFTER-HOURS{Colors.END}\n")
    print("This will:")
    print("  1. Scan after-hours movers")
    print("  2. Reconcile positions (if trading)")
    print("  3. Prepare watchlist for tomorrow")
    print("  4. Run LEAPS analysis on movers\n")
    
    input(f"{Colors.YELLOW}Press Enter to continue...{Colors.END}")
    
    # After-hours scan
    run_command(
        "python scanner.py --mode after_hours --universe liquid --top 20 --save",
        "Step 1/4: After-Hours Movers"
    )
    
    # Reconcile
    print(f"\n{Colors.BOLD}Step 2/4: Reconcile Positions{Colors.END}")
    reconcile = input("Did you trade today? (y/n): ").strip().lower()
    if reconcile == 'y':
        run_command(
            "python scripts/reconcile_ibkr.py",
            "Reconciling IBKR Positions"
        )
    
    # Tomorrow prep
    print(f"\n{Colors.BOLD}Step 3/4: Tomorrow's Watchlist{Colors.END}")
    print("Review today's movers and add to watchlist...")
    print("Check: data/output/after_hours_signals_*.csv\n")
    
    # LEAPS on movers
    print(f"\n{Colors.BOLD}Step 4/4: LEAPS Analysis{Colors.END}")
    print("Enter tickers for LEAPS analysis (comma-separated), or press Enter to skip:")
    tickers = input("> ").strip()
    
    if tickers:
        run_command(
            f"python scripts/run_leaps_analysis.py --batch {tickers.replace(',', ' ')}",
            "Evening LEAPS Analysis"
        )
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓✓✓ EVENING ANALYSIS COMPLETE{Colors.END}")
    print("\nReady for tomorrow's trading session.\n")

def system_status():
    """Check system status."""
    print(f"\n{Colors.BOLD}SYSTEM STATUS CHECK{Colors.END}\n")
    
    print("Checking components...\n")
    
    # Check IBKR connection
    print(f"{Colors.BOLD}IBKR Gateway:{Colors.END} ", end="")
    try:
        from ib_insync import IB
        ib = IB()
        ib.connect('127.0.0.1', 4001, clientId=999, timeout=2)
        print(f"{Colors.GREEN}✓ Connected{Colors.END}")
        ib.disconnect()
    except:
        print(f"{Colors.YELLOW}⚠ Not connected (expected if Gateway not running){Colors.END}")
    
    # Check files
    print(f"\n{Colors.BOLD}Core Files:{Colors.END}")
    files_to_check = [
        ('scanner.py', 'Unified Scanner'),
        ('src/trading/day_trading_bot.py', 'Day Trading Bot'),
        ('src/leaps/complete_leaps_system.py', 'LEAPS System'),
        ('scripts/run_1000trade_validation.py', 'Validation Script'),
        ('data/russell1000_tickers.csv', 'Russell 1000 Universe'),
        ('data/russell2000_tickers.csv', 'Russell 2000 Universe'),
    ]
    
    for file, name in files_to_check:
        if os.path.exists(file):
            print(f"  {Colors.GREEN}✓{Colors.END} {name}")
        else:
            print(f"  {Colors.RED}✗{Colors.END} {name} (missing)")
    
    # Check dependencies
    print(f"\n{Colors.BOLD}Key Dependencies:{Colors.END}")
    deps = ['ib_insync', 'pandas', 'numpy', 'yfinance']
    for dep in deps:
        try:
            __import__(dep)
            print(f"  {Colors.GREEN}✓{Colors.END} {dep}")
        except ImportError:
            print(f"  {Colors.RED}✗{Colors.END} {dep} (not installed)")
    
    print()

def show_docs():
    """Open documentation."""
    print(f"\n{Colors.BOLD}DOCUMENTATION{Colors.END}\n")
    print("Available documentation:")
    print("  1. START_HERE.md - Quick start guide")
    print("  2. COMPLETE_SYSTEM_AUDIT.md - Full system overview")
    print("  3. docs/SCANNER_GUIDE.md - Scanner documentation")
    print("  4. CONSOLIDATION_SUMMARY.md - What changed")
    print("  5. SCRIPT_AUDIT.md - Script inventory")
    
    choice = input(f"\nView which doc? (1-5, or Enter to skip): ").strip()
    
    docs = {
        '1': 'START_HERE.md',
        '2': 'COMPLETE_SYSTEM_AUDIT.md',
        '3': 'docs/SCANNER_GUIDE.md',
        '4': 'CONSOLIDATION_SUMMARY.md',
        '5': 'SCRIPT_AUDIT.md'
    }
    
    if choice in docs:
        subprocess.run(f"cat {docs[choice]} | less", shell=True)

def main():
    """Main interactive loop."""
    while True:
        show_main_menu()
        
        try:
            choice = input(f"{Colors.BOLD}Select option [0-18]: {Colors.END}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{Colors.BOLD}Goodbye!{Colors.END}\n")
            sys.exit(0)
        
        print()
        
        # Intelligent Analysis
        if choice == '1':
            tickers = input("Enter ticker(s) to analyze (comma-separated): ").strip()
            if tickers:
                tickers_clean = tickers.replace(',', ' ')
                run_command(f"python analyze.py {tickers_clean}",
                          f"Intelligent Analysis: {tickers}")
        
        # Main Strategies
        elif choice == '2':
            print(f"{Colors.BOLD}DAY TRADING BOT{Colors.END}")
            print("\nOptions:")
            print("  [V] Validate (1000 trades)")
            print("  [P] Paper trading")
            print("  [L] Live trading")
            sub = input("\nChoice: ").strip().upper()
            
            if sub == 'V':
                run_command("python scripts/run_1000trade_validation.py", 
                          "Day Trading Bot Validation (1000 trades)")
            elif sub == 'P':
                run_command("python scripts/run_paper_trading.py",
                          "Paper Trading Bot")
            elif sub == 'L':
                print(f"{Colors.RED}⚠️  LIVE TRADING - REAL MONEY{Colors.END}")
                confirm = input("Type 'YES' to confirm: ")
                if confirm == 'YES':
                    run_command("python scripts/run_live_trading.py",
                              "LIVE Trading Bot")
        
        elif choice == '3':
            ticker = input("Enter ticker(s) for LEAPS analysis (comma-separated): ").strip()
            if ticker:
                tickers = ticker.replace(',', ' ')
                run_command(f"python scripts/run_leaps_analysis.py --batch {tickers}",
                          f"LEAPS Analysis: {ticker}")
        
        elif choice == '4':
            print(f"{Colors.BOLD}INTRADAY SCANNER{Colors.END}")
            print("\nScan modes:")
            print("  [I] Intraday signals")
            print("  [A] After-hours movers")
            print("  [H] 1-hour momentum")
            print("  [X] All modes")
            sub = input("\nChoice: ").strip().upper()
            
            mode_map = {'I': 'intraday', 'A': 'after_hours', 'H': '1hour', 'X': 'all'}
            mode = mode_map.get(sub, 'intraday')
            
            run_command(f"python scanner.py --mode {mode} --universe liquid --top 10 --save",
                      f"Intraday Scanner ({mode})")
        
        # Complete Workflows
        elif choice == '5':
            morning_routine()
        
        elif choice == '6':
            full_day_trading()
        
        elif choice == '7':
            evening_analysis()
        
        # Validation & Testing
        elif choice == '8':
            print(f"{Colors.BOLD}LIVE VALIDATOR - Real Signals, You Execute{Colors.END}")
            print("\nOptions:")
            print("  [S] Single scan now")
            print("  [M] Monitor continuously (every 30 min)")
            print("  [P] Show performance")
            sub = input("\nChoice: ").strip().upper()
            
            if sub == 'S':
                run_command("python live_validator.py --scan",
                          "Live Validator - Single Scan")
            elif sub == 'M':
                run_command("python live_validator.py --monitor",
                          "Live Validator - Continuous Monitoring")
            elif sub == 'P':
                run_command("python live_validator.py --performance",
                          "Live Validator - Performance Report")
        
        elif choice == '9':
            run_command("python backtest_day_bot.py",
                      "Historical Backtest - Day Bot")
        
        elif choice == '10':
            run_command("python tools/backtest_intraday_signals.py",
                      "Backtest Scanner Signals")
        
        elif choice == '11':
            run_command("python scripts/run_paper_trading.py",
                      "Paper Trading (Auto Bot)")
        
        # Systematic Trading
        elif choice == '12':
            run_command("python scripts/live_daily.py --config configs/default.yaml",
                      "Generating ETF Signals (Low Alpha)")
        
        elif choice == '13':
            if not os.path.exists('signals/latest.csv'):
                print(f"{Colors.RED}No signals found. Run option [10] first.{Colors.END}")
            else:
                run_command("python scripts/send_orders_ibkr.py",
                          "Submitting Orders to IBKR")
        
        elif choice == '14':
            run_command("python scripts/reconcile_ibkr.py",
                      "Reconciling IBKR Positions")
        
        # Utilities
        elif choice == '15':
            run_command("python tools/portfolio_tracker.py --summary",
                      "Unified Portfolio Summary")
        
        # Utilities
        elif choice == '16':
            print("Building universes:")
            print("  [1] Russell 1000")
            print("  [2] Russell 2000")
            print("  [3] Both")
            sub = input("\nChoice: ").strip()
            
            if sub in ['1', '3']:
                run_command("python tools/get_russell1000.py", "Building Russell 1000")
            if sub in ['2', '3']:
                run_command("python tools/get_russell2000.py", "Building Russell 2000")
        
        elif choice == '17':
            system_status()
        
        elif choice == '18':
            show_docs()
        
        elif choice == '0':
            print(f"{Colors.BOLD}Goodbye!{Colors.END}\n")
            sys.exit(0)
        
        else:
            print(f"{Colors.RED}Invalid option. Please select 0-18.{Colors.END}\n")
        
        input(f"\n{Colors.YELLOW}⏎ Press Enter to return to menu...{Colors.END}")


if __name__ == "__main__":
    # Check if running from correct directory
    if not os.path.exists('leaps_env'):
        print(f"{Colors.RED}❌ Error: Must run from project root{Colors.END}")
        print(f"   Current: {os.getcwd()}")
        print(f"   Expected: /Users/raulacedo/Desktop/scanner")
        sys.exit(1)
    
    main()

