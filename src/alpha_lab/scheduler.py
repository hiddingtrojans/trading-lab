#!/usr/bin/env python3
"""
Scheduled Runner
================

Runs trading research tasks on a schedule.
Can be triggered by system cron or run as a daemon.

Setup (macOS/Linux):
    # Add to crontab (crontab -e):
    30 8 * * 1-5 cd /path/to/scanner && ./leaps_env/bin/python src/alpha_lab/scheduler.py --task briefing
    
    # Or run as daemon:
    python src/alpha_lab/scheduler.py --daemon

Tasks:
    - briefing: Daily market briefing (8:30 AM)
    - regime: Market regime check (every 30 min during market hours)
    - whale: Whale scan on watchlist (every hour)
    - eod: End of day summary (4:30 PM)
"""

import os
import sys
import time
import argparse
import schedule
from datetime import datetime, timedelta
from typing import Callable, Dict, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from alpha_lab.alerts import get_alert_manager, AlertPriority


class TradingScheduler:
    """
    Manages scheduled trading research tasks.
    """
    
    def __init__(self):
        self.alert_manager = get_alert_manager()
        self._last_regime = None
        self._tasks_run_today: Dict[str, datetime] = {}
        
    def run_daily_briefing(self):
        """Generate and send daily briefing."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running Daily Briefing...")
        
        try:
            from alpha_lab.daily_briefing import DailyBriefing
            
            briefing = DailyBriefing()
            results = briefing.generate()
            
            # Extract key info for alert
            regime = results.get('regime', {}).get('status', 'UNKNOWN')
            top_picks = results.get('top_opportunities', [])
            
            # Send summary alert
            self.alert_manager.daily_summary(
                regime=regime,
                top_picks=top_picks,
                alerts_count=len(self.alert_manager.history)
            )
            
            print(f"  Daily briefing complete. Regime: {regime}")
            self._tasks_run_today['briefing'] = datetime.now()
            
        except Exception as e:
            print(f"  Error in daily briefing: {e}")
            import traceback
            traceback.print_exc()
    
    def check_regime(self):
        """Check for market regime changes."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking Market Regime...")
        
        try:
            from alpha_lab.market_regime import MarketRegimeAnalyzer
            from utils.data_fetcher import DataFetcher
            
            fetcher = DataFetcher(None)
            analyzer = MarketRegimeAnalyzer(fetcher)
            result = analyzer.analyze_regime()
            
            current_regime = result['status']
            score = result['score']
            
            # Check for change
            if self._last_regime and self._last_regime != current_regime:
                print(f"  REGIME CHANGE: {self._last_regime} → {current_regime}")
                self.alert_manager.regime_change(self._last_regime, current_regime, score)
            else:
                print(f"  Regime: {current_regime} (Score: {score})")
            
            self._last_regime = current_regime
            
        except Exception as e:
            print(f"  Error checking regime: {e}")
    
    def scan_watchlist_whales(self):
        """Scan watchlist for whale activity."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning Watchlist for Whales...")
        
        try:
            from alpha_lab.whale_detector import WhaleDetector
            from alpha_lab.watchlist import load_watchlist
            from utils.data_fetcher import DataFetcher
            
            watchlist = load_watchlist()
            if not watchlist:
                print("  No watchlist configured")
                return
            
            fetcher = DataFetcher(None)
            detector = WhaleDetector(fetcher)
            
            alerts_sent = 0
            for ticker in watchlist[:20]:  # Limit to 20 to avoid rate limits
                try:
                    result = detector.detect_whales(ticker)
                    
                    if result['status'] in ['ACCUMULATION', 'DISTRIBUTION', 'BULLISH FLOW', 'BEARISH FLOW']:
                        self.alert_manager.whale_detected(
                            ticker=ticker,
                            status=result['status'],
                            confidence=result['confidence'],
                            details=result['details']
                        )
                        alerts_sent += 1
                        
                except Exception as e:
                    continue
            
            print(f"  Scanned {len(watchlist[:20])} tickers, {alerts_sent} whale alerts")
            
        except ImportError:
            print("  Watchlist module not found")
        except Exception as e:
            print(f"  Error scanning whales: {e}")
    
    def run_eod_summary(self):
        """End of day summary."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generating EOD Summary...")
        
        try:
            from alpha_lab.trade_journal import TradeJournal
            
            journal = TradeJournal()
            today_trades = journal.get_trades_by_date(datetime.now().date())
            
            # Summary stats
            if today_trades:
                wins = sum(1 for t in today_trades if t.get('pnl', 0) > 0)
                total_pnl = sum(t.get('pnl', 0) for t in today_trades)
                
                print(f"  Today: {len(today_trades)} trades, {wins} wins, ${total_pnl:.2f} P&L")
            else:
                print("  No trades logged today")
                
        except Exception as e:
            print(f"  Error in EOD summary: {e}")
    
    def is_market_hours(self) -> bool:
        """Check if within US market hours (9:30 AM - 4:00 PM ET)."""
        now = datetime.now()
        
        # Simple check (doesn't account for timezone, holidays)
        # Market hours: 9:30 - 16:00
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Weekday check (Monday=0, Sunday=6)
        if now.weekday() >= 5:
            return False
        
        return market_open <= now <= market_close
    
    def setup_schedule(self):
        """Configure the schedule."""
        # Daily briefing at 8:30 AM (before market open)
        schedule.every().monday.at("08:30").do(self.run_daily_briefing)
        schedule.every().tuesday.at("08:30").do(self.run_daily_briefing)
        schedule.every().wednesday.at("08:30").do(self.run_daily_briefing)
        schedule.every().thursday.at("08:30").do(self.run_daily_briefing)
        schedule.every().friday.at("08:30").do(self.run_daily_briefing)
        
        # Regime check every 30 minutes during market hours
        schedule.every(30).minutes.do(
            lambda: self.check_regime() if self.is_market_hours() else None
        )
        
        # Whale scan every hour during market hours
        schedule.every(1).hours.do(
            lambda: self.scan_watchlist_whales() if self.is_market_hours() else None
        )
        
        # EOD summary at 4:30 PM
        schedule.every().monday.at("16:30").do(self.run_eod_summary)
        schedule.every().tuesday.at("16:30").do(self.run_eod_summary)
        schedule.every().wednesday.at("16:30").do(self.run_eod_summary)
        schedule.every().thursday.at("16:30").do(self.run_eod_summary)
        schedule.every().friday.at("16:30").do(self.run_eod_summary)
        
        print("Schedule configured:")
        print("  • Daily Briefing: 8:30 AM (Mon-Fri)")
        print("  • Regime Check: Every 30 min (market hours)")
        print("  • Whale Scan: Every hour (market hours)")
        print("  • EOD Summary: 4:30 PM (Mon-Fri)")
    
    def run_daemon(self):
        """Run as a background daemon."""
        self.setup_schedule()
        
        print(f"\nScheduler started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped.")
    
    def run_task(self, task_name: str):
        """Run a specific task immediately."""
        tasks = {
            'briefing': self.run_daily_briefing,
            'regime': self.check_regime,
            'whale': self.scan_watchlist_whales,
            'eod': self.run_eod_summary
        }
        
        if task_name in tasks:
            tasks[task_name]()
        else:
            print(f"Unknown task: {task_name}")
            print(f"Available: {', '.join(tasks.keys())}")


def main():
    parser = argparse.ArgumentParser(description='Trading Research Scheduler')
    parser.add_argument('--task', choices=['briefing', 'regime', 'whale', 'eod'],
                       help='Run a specific task immediately')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as a background daemon')
    args = parser.parse_args()
    
    scheduler = TradingScheduler()
    
    if args.daemon:
        scheduler.run_daemon()
    elif args.task:
        scheduler.run_task(args.task)
    else:
        # Default: show status
        print("Trading Scheduler")
        print("="*50)
        print(f"Market Hours: {scheduler.is_market_hours()}")
        print(f"Telegram Alerts: {scheduler.alert_manager.telegram_enabled}")
        print(f"Email Alerts: {scheduler.alert_manager.email_enabled}")
        print(f"SMS Alerts: {scheduler.alert_manager.sms_enabled}")
        print("\nTasks available:")
        print("  --task briefing  : Run daily market briefing")
        print("  --task regime    : Check market regime")
        print("  --task whale     : Scan watchlist for whales")
        print("  --task eod       : End of day summary")
        print("  --daemon         : Run continuously with schedule")


if __name__ == "__main__":
    main()

