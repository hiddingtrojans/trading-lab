#!/usr/bin/env python3
"""
Position Monitor
================

Monitors open positions against live prices:
- Alerts when stop/target hit
- Warns when approaching stop/target
- Generates EOD summary

Can run as daemon or one-shot check.

Usage:
    python src/alpha_lab/position_monitor.py          # One-time check
    python src/alpha_lab/position_monitor.py --daemon # Continuous monitoring
    python src/alpha_lab/position_monitor.py --eod    # EOD summary only
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

import yfinance as yf
from alpha_lab.position_manager import PositionManager
from alpha_lab.telegram_alerts import (
    TelegramAlerter, send_position, send_eod, send_regime
)
from alpha_lab.config import get_config


class PositionMonitor:
    """Monitor positions and send alerts."""
    
    def __init__(self):
        self.pm = PositionManager()
        self.alerter = TelegramAlerter()
        
        # Thresholds from config
        self.near_stop_pct = get_config('alerts.near_stop_pct', 2)
        self.near_target_pct = get_config('alerts.near_target_pct', 2)
        
        # Track what we've already alerted on (avoid spam)
        self.alerted_today = set()
        self._load_alert_state()
    
    def _load_alert_state(self):
        """Load today's alert state to avoid duplicates."""
        state_path = os.path.join(project_root, 'data', 'alert_state.json')
        if os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    state = json.load(f)
                    # Reset if different day
                    if state.get('date') == datetime.now().strftime('%Y-%m-%d'):
                        self.alerted_today = set(state.get('alerted', []))
            except:
                pass
    
    def _save_alert_state(self):
        """Save alert state."""
        state_path = os.path.join(project_root, 'data', 'alert_state.json')
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'alerted': list(self.alerted_today)
            }, f)
    
    def check_positions(self) -> List[Dict]:
        """
        Check all positions against current prices.
        
        Returns:
            List of alerts generated
        """
        alerts = []
        positions = self.pm.get_open_positions()
        
        if not positions:
            return alerts
        
        for pos in positions:
            ticker = pos['ticker']
            entry = pos['entry']
            stop = pos['stop']
            target = pos['target']
            current = pos['current_price']
            
            # Calculate distances
            stop_dist = (current - stop) / current * 100
            target_dist = (target - current) / current * 100
            pnl_pct = (current - entry) / entry * 100
            
            alert_key = f"{ticker}_{datetime.now().strftime('%Y%m%d')}"
            
            # Check stop hit
            if current <= stop:
                if f"{alert_key}_stop" not in self.alerted_today:
                    send_position(
                        ticker=ticker,
                        alert_type='STOP_HIT',
                        entry=entry,
                        current=current,
                        stop=stop,
                        pnl_pct=pnl_pct
                    )
                    self.alerted_today.add(f"{alert_key}_stop")
                    alerts.append({'ticker': ticker, 'type': 'STOP_HIT', 'price': current})
                    
                    # Auto-close position
                    self.pm.close_position(ticker, current, 'Stop hit')
            
            # Check target hit
            elif current >= target:
                if f"{alert_key}_target" not in self.alerted_today:
                    send_position(
                        ticker=ticker,
                        alert_type='TARGET_HIT',
                        entry=entry,
                        current=current,
                        target=target,
                        pnl_pct=pnl_pct
                    )
                    self.alerted_today.add(f"{alert_key}_target")
                    alerts.append({'ticker': ticker, 'type': 'TARGET_HIT', 'price': current})
            
            # Check near stop
            elif stop_dist <= self.near_stop_pct:
                if f"{alert_key}_near_stop" not in self.alerted_today:
                    send_position(
                        ticker=ticker,
                        alert_type='NEAR_STOP',
                        entry=entry,
                        current=current,
                        stop=stop,
                        pnl_pct=pnl_pct
                    )
                    self.alerted_today.add(f"{alert_key}_near_stop")
                    alerts.append({'ticker': ticker, 'type': 'NEAR_STOP', 'price': current})
            
            # Check near target
            elif target_dist <= self.near_target_pct:
                if f"{alert_key}_near_target" not in self.alerted_today:
                    send_position(
                        ticker=ticker,
                        alert_type='NEAR_TARGET',
                        entry=entry,
                        current=current,
                        target=target,
                        pnl_pct=pnl_pct
                    )
                    self.alerted_today.add(f"{alert_key}_near_target")
                    alerts.append({'ticker': ticker, 'type': 'NEAR_TARGET', 'price': current})
        
        self._save_alert_state()
        return alerts
    
    def get_regime(self) -> Dict:
        """Get current market regime."""
        try:
            spy = yf.Ticker('SPY')
            hist = spy.history(period='3mo')
            
            spy_price = hist['Close'].iloc[-1]
            spy_sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            
            vix = yf.Ticker('^VIX')
            vix_hist = vix.history(period='5d')
            vix_level = vix_hist['Close'].iloc[-1] if len(vix_hist) > 0 else 20
            
            # Determine regime
            if spy_price > spy_sma50 and vix_level < 20:
                status = 'GREEN'
                action = 'Full size longs OK'
            elif spy_price > spy_sma50 and vix_level < 30:
                status = 'YELLOW'
                action = 'Selective, smaller size'
            else:
                status = 'RED'
                action = 'No new longs'
            
            return {
                'status': status,
                'action': action,
                'spy_price': spy_price,
                'vix': vix_level,
                'spy_vs_sma': (spy_price - spy_sma50) / spy_sma50 * 100
            }
        except Exception as e:
            return {'status': 'UNKNOWN', 'action': 'Unable to determine', 'error': str(e)}
    
    def check_regime_change(self, previous_regime: str = None) -> Optional[str]:
        """
        Check if regime has changed.
        
        Args:
            previous_regime: Previous regime status
        
        Returns:
            New regime if changed, None otherwise
        """
        regime = self.get_regime()
        current = regime.get('status')
        
        if previous_regime and current != previous_regime:
            send_regime(
                old_regime=previous_regime,
                new_regime=current,
                details=regime
            )
            return current
        
        return None
    
    def send_eod_summary(self):
        """Send end-of-day summary."""
        positions = self.pm.get_open_positions()
        regime = self.get_regime()
        
        # Calculate daily P&L (simplified - would need position history for accurate)
        daily_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
        
        send_eod(
            positions=positions,
            regime=regime,
            daily_pnl=daily_pnl
        )
        
        print(f"EOD Summary sent. {len(positions)} positions, ${daily_pnl:+,.0f} unrealized")
    
    def run_daemon(self, check_interval: int = 60):
        """
        Run continuous monitoring.
        
        Args:
            check_interval: Seconds between checks
        """
        print(f"Starting position monitor (checking every {check_interval}s)")
        print("Press Ctrl+C to stop\n")
        
        previous_regime = self.get_regime().get('status')
        
        while True:
            try:
                # Check positions
                alerts = self.check_positions()
                
                if alerts:
                    for a in alerts:
                        print(f"  ALERT: {a['type']} - {a['ticker']} @ ${a['price']:.2f}")
                
                # Check regime change
                new_regime = self.check_regime_change(previous_regime)
                if new_regime:
                    print(f"  REGIME CHANGE: {previous_regime} -> {new_regime}")
                    previous_regime = new_regime
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(check_interval)
    
    def run_once(self):
        """Run single check and print status."""
        print("Checking positions...")
        
        positions = self.pm.get_open_positions()
        regime = self.get_regime()
        
        print(f"\nRegime: {regime.get('status')} (SPY ${regime.get('spy_price', 0):.2f}, VIX {regime.get('vix', 0):.1f})")
        print(f"Open positions: {len(positions)}")
        
        if positions:
            print("\n" + "-" * 50)
            for p in positions:
                pnl = p.get('unrealized_pct', 0)
                stop_dist = (p['current_price'] - p['stop']) / p['current_price'] * 100
                target_dist = (p['target'] - p['current_price']) / p['current_price'] * 100
                
                status = "OK"
                if stop_dist <= self.near_stop_pct:
                    status = "NEAR STOP"
                elif target_dist <= self.near_target_pct:
                    status = "NEAR TARGET"
                
                print(f"{p['ticker']}: ${p['current_price']:.2f} ({pnl:+.1f}%) - {status}")
                print(f"  Stop: ${p['stop']:.2f} ({stop_dist:.1f}% away)")
                print(f"  Target: ${p['target']:.2f} ({target_dist:.1f}% away)")
        
        # Check for alerts
        alerts = self.check_positions()
        if alerts:
            print(f"\nAlerts sent: {len(alerts)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Position Monitor')
    parser.add_argument('--daemon', action='store_true', help='Run continuously')
    parser.add_argument('--eod', action='store_true', help='Send EOD summary only')
    parser.add_argument('--interval', type=int, default=60, help='Check interval (seconds)')
    args = parser.parse_args()
    
    monitor = PositionMonitor()
    
    if args.eod:
        monitor.send_eod_summary()
    elif args.daemon:
        monitor.run_daemon(check_interval=args.interval)
    else:
        monitor.run_once()

