"""
Monthly Signal Review - Check outcomes and calculate performance.

Runs daily (or weekly) to:
1. Check prices for signals that are 1, 5, 20 days old
2. Update outcomes (win/loss)
3. Generate performance report

Also sends monthly summary to Telegram.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alpha_lab.signal_db import (
    get_pending_signals,
    update_signal_outcome,
    get_performance_stats,
    get_all_signals,
)
from src.alpha_lab.telegram_alerts import send_message


def check_signal_outcomes():
    """Check prices for pending signals and update outcomes."""
    print("📊 Checking signal outcomes...")
    
    # Get signals at least 1 day old
    pending = get_pending_signals(days_old=1)
    print(f"  Found {len(pending)} pending signals to check")
    
    updated = 0
    for signal in pending:
        ticker = signal['ticker']
        entry_price = signal['entry_price']
        target = signal.get('target_price')
        stop = signal.get('stop_loss')
        created_at = datetime.fromisoformat(signal['created_at'])
        
        age_days = (datetime.now() - created_at).days
        
        try:
            # Get current and historical prices
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1mo')
            
            if len(hist) < 2:
                continue
            
            current_price = hist['Close'].iloc[-1]
            
            # Get prices at specific intervals
            price_1d = None
            price_5d = None
            price_20d = None
            
            # Find price closest to 1 day after signal
            if age_days >= 1 and len(hist) >= 2:
                price_1d = hist['Close'].iloc[-min(age_days, len(hist)-1)]
            
            if age_days >= 5 and len(hist) >= 5:
                price_5d = hist['Close'].iloc[-min(age_days-4, len(hist)-1)]
            
            if age_days >= 20 and len(hist) >= 20:
                price_20d = hist['Close'].iloc[-min(age_days-19, len(hist)-1)]
            
            # Check if target/stop were hit
            hit_target = False
            hit_stop = False
            
            # Check high/low since signal
            highs = hist['High'].iloc[-min(age_days, len(hist)):]
            lows = hist['Low'].iloc[-min(age_days, len(hist)):]
            
            if target and highs.max() >= target:
                hit_target = True
            if stop and lows.min() <= stop:
                hit_stop = True
            
            # Update in DB
            update_signal_outcome(
                signal_id=signal['id'],
                price_1d=price_1d,
                price_5d=price_5d,
                price_20d=price_20d,
                hit_target=hit_target,
                hit_stop=hit_stop,
            )
            updated += 1
            
            # Log result
            return_5d = ((price_5d / entry_price) - 1) * 100 if price_5d else None
            outcome = "✅ WIN" if hit_target else ("❌ LOSS" if hit_stop else "⏳ PENDING")
            print(f"  {ticker}: {outcome} | Entry: ${entry_price:.2f} → ${current_price:.2f}")
            
        except Exception as e:
            print(f"  {ticker}: Error checking - {e}")
    
    print(f"  Updated {updated} signals")
    return updated


def generate_performance_report(days: int = 30) -> str:
    """Generate performance report for Telegram."""
    stats = get_performance_stats(days)
    
    lines = [
        f"📊 SIGNAL PERFORMANCE ({days}d)",
        "",
    ]
    
    # Overall stats
    if stats['completed'] > 0:
        lines.append(f"━━━ OVERALL ━━━")
        lines.append(f"Signals: {stats['total_signals']} ({stats['pending']} pending)")
        lines.append(f"Win Rate: {stats['win_rate']:.0f}% ({stats['wins']}W / {stats['losses']}L)")
        lines.append(f"Avg Return 5d: {stats['avg_return_5d']:+.1f}%")
        lines.append(f"Best: {stats['best_trade']:+.1f}% | Worst: {stats['worst_trade']:+.1f}%")
        lines.append("")
    else:
        lines.append("No completed signals yet")
        lines.append("")
    
    # By signal type
    if stats['by_signal_type']:
        lines.append("━━━ BY TYPE ━━━")
        for item in stats['by_signal_type']:
            win_rate = (item['wins'] / item['total'] * 100) if item['total'] > 0 else 0
            lines.append(f"• {item['signal_type']}: {win_rate:.0f}% WR ({item['total']} signals)")
        lines.append("")
    
    # By trade type
    if stats['by_trade_type']:
        lines.append("━━━ BY TRADE ━━━")
        for item in stats['by_trade_type']:
            win_rate = (item['wins'] / item['total'] * 100) if item['total'] > 0 else 0
            avg_ret = item['avg_return'] or 0
            lines.append(f"• {item['trade_type']}: {win_rate:.0f}% WR, {avg_ret:+.1f}% avg")
        lines.append("")
    
    # Recent signals
    if stats['recent']:
        lines.append("━━━ RECENT ━━━")
        for sig in stats['recent'][:5]:
            ticker = sig['ticker']
            ret = sig['return_5d']
            outcome = sig['outcome']
            emoji = "✅" if outcome == 'win' else ("❌" if outcome == 'loss' else "⏳")
            ret_str = f"{ret:+.1f}%" if ret else "N/A"
            lines.append(f"{emoji} {ticker}: {ret_str}")
    
    return "\n".join(lines)


def run_daily_review(send_telegram: bool = False):
    """Run daily signal review."""
    print("\n" + "="*50)
    print("🔄 DAILY SIGNAL REVIEW")
    print("="*50)
    
    # Check outcomes
    check_signal_outcomes()
    
    # Generate report
    report = generate_performance_report(30)
    print("\n" + report)
    
    if send_telegram:
        print("\nSending to Telegram...")
        success = send_message(report)
        print("✅ Sent!" if success else "❌ Failed")
    
    return report


def run_monthly_summary(send_telegram: bool = True):
    """Generate and send monthly performance summary."""
    print("\n" + "="*50)
    print("📅 MONTHLY PERFORMANCE SUMMARY")
    print("="*50)
    
    # Check all pending outcomes first
    check_signal_outcomes()
    
    # Get 30-day stats
    report = generate_performance_report(30)
    
    # Add header
    full_report = f"📅 MONTHLY SUMMARY - {datetime.now().strftime('%B %Y')}\n\n{report}"
    
    print("\n" + full_report)
    
    if send_telegram:
        print("\nSending to Telegram...")
        success = send_message(full_report)
        print("✅ Sent!" if success else "❌ Failed")
    
    return full_report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Review")
    parser.add_argument("--monthly", action="store_true", help="Send monthly summary")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    
    args = parser.parse_args()
    
    if args.monthly:
        run_monthly_summary(send_telegram=args.telegram)
    else:
        run_daily_review(send_telegram=args.telegram)

