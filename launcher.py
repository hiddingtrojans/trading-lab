#!/usr/bin/env python3
"""
 Trading System Launcher
 =======================
 
 Simple menu interface to run the trading system tools.
 No coding knowledge required.
"""

import os
import sys
import time
import subprocess
import webbrowser
from datetime import datetime

# Suppress noisy warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Load Telegram config if available
telegram_env = os.path.join(os.path.dirname(__file__), 'configs', 'telegram.env')
if os.path.exists(telegram_env):
    with open(telegram_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Remove 'export ' prefix if present
                if line.startswith('export '):
                    line = line[7:]
                key, value = line.split('=', 1)
                # Remove quotes from value
                value = value.strip('"').strip("'")
                os.environ[key] = value

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("="*60)
    print("   🚀  TRADING SYSTEM & RESEARCH LAB  🚀")
    print("="*60)
    print(f"   System Ready | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 60)

def run_command(command):
    try:
        # Use the current python interpreter
        if command.startswith("python "):
            command = command.replace("python ", f"{sys.executable} ", 1)
            
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Process encountered an error (Exit Code: {e.returncode})")
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    
    input("\nPress Enter to continue...")

def show_dashboard():
    print("\n🌐 Starting Dashboard...")
    print("   Opening http://127.0.0.1:5000 in your browser...")
    
    # Open browser after a slight delay to let server start
    def open_browser():
        time.sleep(2)
        webbrowser.open('http://127.0.0.1:5000')
    
    import threading
    threading.Thread(target=open_browser).start()
    
    run_command("python src/dashboard/simple_dashboard.py")

def analyze_stock():
    ticker = input("\n🔎 Enter Ticker Symbol (e.g. NVDA): ").strip().upper()
    if not ticker: return
    
    print(f"\nRunning comprehensive analysis for {ticker}...")
    print("This may take 1-2 minutes (Data, LEAPS, Signals)...")
    run_command(f"python unified_analyzer.py --ticker {ticker} --types all --save")

def screen_market():
    print("\n🔍 Select Screener Type:")
    print("   1. High Growth Stocks")
    print("   2. Undervalued Stocks")
    print("   3. Momentum/Breakout")
    print("   4. LEAPS Opportunities")
    
    choice = input("\n   Enter choice (1-4): ")
    
    mode = "growth"
    if choice == "2": mode = "value"
    elif choice == "3": mode = "momentum"
    elif choice == "4": mode = "leaps"
    
    print(f"\nScreening for {mode.upper()} opportunities...")
    run_command(f"python unified_analyzer.py --screen {mode} --top 10 --save")

def run_backtest():
    print("\n📉 Select Backtest Universe:")
    print("   1. Liquid Tech (Top 16)")
    print("   2. Broad Market (Russell 1000 - Top 30)")
    print("   3. Custom List (Enter manually)")
    
    uni_choice = input("\n   Enter choice (1-3): ")
    universe = "liquid"
    custom_tickers = ""
    
    if uni_choice == "2": 
        universe = "russell1000"
    elif uni_choice == "3": 
        universe = "custom"
        custom_tickers = input("   Enter tickers (e.g. NVDA,AMD): ").strip()
        if not custom_tickers: return

    print("\n📉 Select Strategy:")
    print("   1. Gap + VWAP (Mean Reversion/Trend)")
    print("   2. Volatility Breakout (ORB 30m)")
    print("   3. Strategy Ensemble (Adaptive Multi-Strategy)")
    
    strat_choice = input("\n   Enter choice (1-3): ")
    strategy = "gap_vwap"
    if strat_choice == "2": strategy = "vol_breakout"
    elif strat_choice == "3": strategy = "ensemble"
    
    print("\n📉 Select Duration:")
    print("   1. Quick Test (30 Days)")
    print("   2. Full Test (1 Year - Slower)")
    
    time_choice = input("\n   Enter choice (1-2): ")
    days = "30" if time_choice == "1" else "252"
    
    # Construct command
    cmd = f"python comprehensive_backtest.py --universe {universe} --days {days} --strategy {strategy}"
    if universe == "custom":
        cmd += f" --tickers {custom_tickers}"
    
    print(f"\nRunning backtest on {universe.upper()} ({strategy})...")
    run_command(cmd)

def check_portfolio():
    print("\n🏥 Portfolio Health Check")
    print("Enter your tickers separated by commas (e.g. NVDA,AMD,TSM)")
    tickers = input("   Tickers: ").strip()
    if not tickers: return
    
    print(f"\nRunning risk analysis...")
    run_command(f"python src/alpha_lab/portfolio_risk.py --tickers {tickers}")

def daily_briefing():
    print("\n☕ Generating Daily Briefing...")
    run_command("python src/alpha_lab/daily_briefing.py")

def manage_watchlist():
    print("\n📋 Watchlist Manager")
    run_command("python src/alpha_lab/watchlist.py")

def trade_journal():
    print("\n📔 Trade Journal")
    print("   1. View Statistics (Last 30 Days)")
    print("   2. Log New Trade")
    print("   3. View Recent Trades")
    
    choice = input("\n   Enter choice (1-3): ")
    
    if choice == "1":
        run_command("python src/alpha_lab/trade_journal.py")
    elif choice == "2":
        ticker = input("   Ticker: ").strip().upper()
        strategy = input("   Strategy (Gap/LEAPS/Swing): ").strip()
        entry = input("   Entry Price: ").strip()
        stop = input("   Stop Price: ").strip()
        target = input("   Target Price: ").strip()
        
        if all([ticker, entry, stop, target]):
            cmd = f'python -c "from src.alpha_lab.trade_journal import TradeJournal, Trade; j=TradeJournal(); t=Trade(ticker=\'{ticker}\', strategy=\'{strategy}\', direction=\'long\', entry_price={entry}, stop_price={stop}, target_price={target}); print(f\'Logged trade ID: {{j.log_trade(t)}}\')"'
            run_command(cmd)
    elif choice == "3":
        run_command('python -c "from src.alpha_lab.trade_journal import TradeJournal; j=TradeJournal(); j.print_summary(30)"')

def options_greeks():
    ticker = input("\n📊 Enter Ticker for Greeks Analysis: ").strip().upper()
    if not ticker: return
    run_command(f"python src/alpha_lab/options_greeks.py {ticker}")

def multi_timeframe():
    ticker = input("\n📈 Enter Ticker for Multi-Timeframe Analysis: ").strip().upper()
    if not ticker: return
    run_command(f"python src/alpha_lab/multi_timeframe.py {ticker}")

def correlation_check():
    print("\n🔗 Portfolio Correlation Check")
    tickers = input("   Enter positions (e.g. NVDA,AMD,TSM): ").strip()
    if not tickers: return
    run_command(f'python -c "from src.alpha_lab.correlation_filter import CorrelationFilter; cf=CorrelationFilter(); cf.print_analysis([\'{t.strip()}\' for t in \'{tickers}\'.split(\',\')])"')

def advanced_tools():
    while True:
        clear_screen()
        print("="*60)
        print("   ADVANCED TOOLS")
        print("="*60)
        print("\n   1. 📋  Manage Watchlists")
        print("   2. 📔  Trade Journal")
        print("   3. 📊  Options Greeks Analysis")
        print("   4. 📈  Multi-Timeframe Check")
        print("   5. 🔗  Portfolio Correlation")
        print("   6. ⏰  Start Scheduler (Daemon)")
        print("   0. ⬅️   Back to Main Menu")
        
        choice = input("\nSelect: ")
        
        if choice == "1":
            manage_watchlist()
        elif choice == "2":
            trade_journal()
        elif choice == "3":
            options_greeks()
        elif choice == "4":
            multi_timeframe()
        elif choice == "5":
            correlation_check()
        elif choice == "6":
            print("\nStarting scheduler daemon...")
            print("Press Ctrl+C to stop")
            run_command("python src/alpha_lab/scheduler.py --daemon")
        elif choice == "0":
            break
        else:
            input("\nInvalid option. Press Enter...")

def universe_scan():
    """Scan 150+ small/mid caps for institutional accumulation."""
    print("\n🔭 UNIVERSE SCANNER")
    print("   Scanning 150+ small/mid cap stocks for edge signals...")
    print("   (Volume anomalies, momentum, relative strength, setups)")
    print("\n   This takes 2-3 minutes. Be patient.\n")
    run_command("python src/alpha_lab/universe_scanner.py")

def check_performance():
    """Validate if recent signals actually worked."""
    print("\n📈 SIGNAL PERFORMANCE CHECK")
    print("   Validating signals from the past 5-10 days...")
    print("   This shows if the scanner is actually profitable.\n")
    run_command("python src/alpha_lab/performance_checker.py")

def main():
    while True:
        clear_screen()
        print_header()
        print("\nMAIN MENU:")
        print("   1. 📊  Open Dashboard (View Results)")
        print("   2. 🔎  Analyze a Stock (Deep Dive)")
        print("   3. 📡  Screen the Market (Find Ideas)")
        print("   4. 🧪  Run Backtest (Validate Strategy)")
        print("   5. 🏥  Portfolio Health Check")
        print("   6. ☕  Daily Briefing (One-Click Research)")
        print("   7. 🔧  Advanced Tools")
        print("   8. 🔭  Universe Scan (Find Edge)")
        print("   9. 📈  Performance Check (Did Signals Work?)")
        print("   0. ❌  Exit")
        
        choice = input("\nSelect an option: ")
        
        if choice == "1":
            show_dashboard()
        elif choice == "2":
            analyze_stock()
        elif choice == "3":
            screen_market()
        elif choice == "4":
            run_backtest()
        elif choice == "5":
            check_portfolio()
        elif choice == "6":
            daily_briefing()
        elif choice == "7":
            advanced_tools()
        elif choice == "8":
            universe_scan()
        elif choice == "9":
            check_performance()
        elif choice == "0":
            print("\nGoodbye! Happy Trading.")
            sys.exit(0)
        else:
            input("\nInvalid option. Press Enter...")

if __name__ == "__main__":
    # Ensure we are in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()

