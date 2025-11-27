#!/usr/bin/env python3
"""
1000-Trade Bot Validation - Test Before Production
===================================================

Run the trading bot for 1000 trades to validate accuracy >= 55%
before deploying to production.
"""

import asyncio
import sys
import os
import threading

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading.simple_paper_bot import SimplePaperTradingBot, CONFIG
from dashboard.validation_dashboard import start_validation_dashboard
from utils.trade_tracker import TradeTracker
import logging

def print_validation_info():
    """Print validation mode information."""
    print("\n" + "="*70)
    print("🎯 1000-TRADE BOT VALIDATION - PRODUCTION READINESS TEST")
    print("="*70)
    print()
    print("📋 VALIDATION CRITERIA:")
    print("   ✅ Target: 1000 trades for statistical significance")
    print("   ✅ Accuracy Target: ≥ 55% win rate")
    print("   ✅ Minimum for approval: 500+ trades completed")
    print()
    print("📊 WHAT THIS TRACKS:")
    print("   • Every trade entry and exit")
    print("   • Win rate and accuracy over time")
    print("   • P&L per trade and cumulative")
    print("   • Max drawdown and risk metrics")
    print("   • Profit factor and Sharpe ratio")
    print()
    print("🌐 DASHBOARDS:")
    print("   • Validation Dashboard: http://127.0.0.1:5001 (Performance tracking)")
    print("   • Trading Dashboard:    http://127.0.0.1:5000 (Live positions)")
    print()
    print("🎯 PRODUCTION APPROVAL:")
    print("   IF accuracy ≥ 55% after 1000 trades → ✅ APPROVED FOR PRODUCTION")
    print("   IF accuracy < 55% after 1000 trades → ❌ NEEDS OPTIMIZATION")
    print()
    print("="*70)
    print()

async def main():
    """Main execution with dual dashboards."""
    print_validation_info()
    
    # Initialize trade tracker
    tracker = TradeTracker()
    
    # Show current progress
    summary = tracker.get_performance_summary()  # All trades, no time limit
    
    total_trades = summary.get('total_trades', 0)
    target_trades = 1000
    progress_pct = min(100, (total_trades / target_trades) * 100)
    
    print("📊 CURRENT VALIDATION STATUS:")
    print("="*70)
    print(f"Total Trades: {total_trades}/1000 ({progress_pct:.1f}% complete)")
    print(f"Current Accuracy: {summary.get('accuracy', 0):.1f}%")
    print(f"Win Rate: {summary.get('win_rate', 0):.1f}%")
    print(f"Total P&L: ${summary.get('total_pnl', 0):.2f}")
    print(f"Meets Threshold: {'✅ YES' if summary.get('meets_threshold', False) else '❌ NO'}")
    
    if total_trades >= 1000:
        if summary.get('accuracy', 0) >= 55:
            print(f"\n🎉 ✅ BOT APPROVED FOR PRODUCTION!")
            print(f"   Accuracy: {summary['accuracy']:.1f}% ≥ 55%")
        else:
            print(f"\n⚠️ ❌ BOT NEEDS OPTIMIZATION")
            print(f"   Accuracy: {summary['accuracy']:.1f}% < 55%")
    elif total_trades >= 500:
        print(f"\n⏳ Continue testing - {1000 - total_trades} more trades needed")
    else:
        print(f"\n⏳ Early stage - {1000 - total_trades} more trades needed for validation")
    print("="*70)
    print()
    
    # Start validation dashboard in background
    dashboard_thread = threading.Thread(
        target=lambda: start_validation_dashboard(host='127.0.0.1', port=5001),
        daemon=True
    )
    dashboard_thread.start()
    
    print("🌐 Validation dashboard started at http://127.0.0.1:5001")
    print("📊 Monitor 100-day performance and validation status")
    print()
    
    # Wait for dashboard to start
    await asyncio.sleep(2)
    
    # Start the paper trading bot with tracking
    print("🚀 Starting paper trading bot with comprehensive tracking...")
    print("📊 All trades will be recorded for validation analysis")
    print("⏰ Press Ctrl+C to stop\n")
    
    bot = SimplePaperTradingBot(CONFIG)
    
    try:
        await bot.run_trading_session_with_dashboard()
    except KeyboardInterrupt:
        print("\n⏹️ Validation session stopped by user")
        
        # Show updated status
        summary = tracker.get_performance_summary()
        
        total_trades = summary.get('total_trades', 0)
        target_trades = 1000
        
        print("\n" + "="*70)
        print("📊 SESSION SUMMARY")
        print("="*70)
        print(f"Total Trades: {total_trades}/1000 ({(total_trades/target_trades*100):.1f}%)")
        print(f"Accuracy: {summary.get('accuracy', 0):.1f}%")
        print(f"Win Rate: {summary.get('win_rate', 0):.1f}%")
        print(f"Total P&L: ${summary.get('total_pnl', 0):.2f}")
        print(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
        print("="*70)
        
        if total_trades >= 1000:
            if summary.get('accuracy', 0) >= 55:
                print("\n🎉 ✅ BOT APPROVED FOR PRODUCTION!")
                print(f"   1000 trades completed")
                print(f"   Accuracy: {summary['accuracy']:.1f}% ≥ 55% threshold")
                print("   Ready to deploy with real money!")
            else:
                print("\n⚠️ ❌ BOT NEEDS OPTIMIZATION")
                print(f"   1000 trades completed")
                print(f"   Accuracy: {summary['accuracy']:.1f}% < 55% threshold")
                print("   Do not deploy - needs improvement")
        elif total_trades >= 500:
            print(f"\n⏳ Halfway there! {1000 - total_trades} more trades needed")
            print(f"   Current trend: {'✅ On track' if summary.get('accuracy', 0) >= 55 else '⚠️ Below threshold'}")
        else:
            print(f"\n⏳ Early stage - {1000 - total_trades} more trades needed")
    
    except Exception as e:
        logging.error(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/validation.log')
        ]
    )
    
    asyncio.run(main())
