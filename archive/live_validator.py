#!/usr/bin/env python3
"""
Live Trade Validator (No Auto-Execution)
=========================================

Monitors live market, identifies trade signals, logs recommendations.
You manually execute trades you agree with.
Tracks your decisions and outcomes for validation.

This is BETTER than historical backtest because:
- Tests on live market conditions
- You experience real emotions/decisions
- Validates with actual slippage
- No risk (you control execution)
- Builds discipline
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import yaml
import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, List
from ib_insync import IB, Stock, util
import sqlite3
import warnings
warnings.filterwarnings('ignore')

from alpha_lab.intraday_signals import IntradaySignalGenerator


class LiveValidator:
    """
    Monitors live market, logs trade signals, tracks your execution decisions.
    
    NO AUTO-EXECUTION - You decide what to trade.
    """
    
    def __init__(self, db_path: str = 'data/live_validation.db'):
        """Initialize validator."""
        self.db_path = db_path
        self.ib = None
        self.scanner = None
        self._init_database()
    
    def _init_database(self):
        """Create database for tracking signals and executions."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Signals table - what system recommended
        c.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                target_price REAL NOT NULL,
                reasoning TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Executions table - what YOU actually did
        c.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                executed INTEGER DEFAULT 0,
                execution_time TEXT,
                actual_entry REAL,
                actual_exit REAL,
                actual_pnl REAL,
                notes TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect_ibkr(self, use_paper: bool = True):
        """
        Connect to IBKR.
        
        Args:
            use_paper: True for paper account, False for live
                      (doesn't matter since we're not executing)
        """
        try:
            cfg = yaml.safe_load(open('configs/ibkr.yaml'))
            
            self.ib = IB()
            
            # Use paper port by default (4002), or live port (4001)
            port = 4002 if use_paper else cfg.get('port', 4001)
            
            self.ib.connect(cfg['host'], port, clientId=cfg['client_id']+99, timeout=15)
            
            print(f"✓ Connected to IBKR ({'Paper' if use_paper else 'Live'} account)")
            print(f"  Account: {self.ib.managedAccounts()[0]}")
            print(f"\n⚠️  NO AUTO-EXECUTION - You control all trades\n")
            
            self.scanner = IntradaySignalGenerator(self.ib)
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def log_signal(self, signal: Dict) -> int:
        """
        Log a trade signal to database.
        
        Returns:
            Signal ID for tracking
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO signals 
            (timestamp, ticker, signal_type, confidence, entry_price, 
             stop_loss, target_price, reasoning, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            datetime.now().isoformat(),
            signal['symbol'],
            signal['signal'],
            signal['confidence'],
            signal['price'],
            signal.get('stop_loss', signal['price'] - 0.25),
            signal.get('target', signal['price'] + 0.50),
            signal.get('reasoning', '')
        ))
        
        conn.commit()
        signal_id = c.lastrowid
        conn.close()
        
        return signal_id
    
    def display_signal(self, signal: Dict, signal_id: int):
        """Display signal to user for manual decision."""
        print("\n" + "="*80)
        print(f"🚨 TRADE SIGNAL #{signal_id}")
        print("="*80)
        print(f"\nTicker: {signal['symbol']}")
        print(f"Signal: {signal['signal']}")
        print(f"Confidence: {signal['confidence']:.1f}/100")
        print(f"\nEntry: ${signal['price']:.2f}")
        print(f"Stop: ${signal.get('stop_loss', signal['price'] - 0.25):.2f}")
        print(f"Target: ${signal.get('target', signal['price'] + 0.50):.2f}")
        print(f"Risk: ${abs(signal['price'] - signal.get('stop_loss', signal['price'] - 0.25)):.2f}")
        print(f"Reward: ${abs(signal.get('target', signal['price'] + 0.50) - signal['price']):.2f}")
        print(f"R/R: {abs(signal.get('target', signal['price'] + 0.50) - signal['price']) / abs(signal['price'] - signal.get('stop_loss', signal['price'] - 0.25)):.1f}:1")
        
        print(f"\n" + "="*80)
        print(f"MANUAL DECISION REQUIRED")
        print(f"="*80)
        print(f"\nOptions:")
        print(f"  [T] Take this trade (log as executed)")
        print(f"  [S] Skip this trade (log as skipped)")
        print(f"  [W] Watch / Decide later")
        print(f"  [Q] Quit validator")
        
        return signal_id
    
    def record_decision(self, signal_id: int, decision: str, 
                       entry_price: float = None, notes: str = None):
        """
        Record your manual decision on a signal.
        
        Args:
            signal_id: Signal ID
            decision: 'executed', 'skipped', 'watching'
            entry_price: Actual entry if executed
            notes: Your reasoning
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if decision == 'executed':
            c.execute('''
                INSERT INTO executions 
                (signal_id, executed, execution_time, actual_entry, notes)
                VALUES (?, 1, ?, ?, ?)
            ''', (signal_id, datetime.now().isoformat(), entry_price, notes))
            
            c.execute('UPDATE signals SET status = ? WHERE id = ?', 
                     ('executed', signal_id))
            
            print(f"\n✓ Logged as EXECUTED at ${entry_price:.2f}")
            print(f"  Track this trade and log exit when closed")
        
        elif decision == 'skipped':
            c.execute('''
                INSERT INTO executions 
                (signal_id, executed, notes)
                VALUES (?, 0, ?)
            ''', (signal_id, notes))
            
            c.execute('UPDATE signals SET status = ? WHERE id = ?', 
                     ('skipped', signal_id))
            
            print(f"\n○ Logged as SKIPPED")
        
        elif decision == 'watching':
            c.execute('UPDATE signals SET status = ? WHERE id = ?', 
                     ('watching', signal_id))
            print(f"\n⏳ Logged as WATCHING")
        
        conn.commit()
        conn.close()
    
    def log_exit(self, signal_id: int, exit_price: float, notes: str = None):
        """
        Log trade exit after you close position.
        
        Args:
            signal_id: Original signal ID
            exit_price: Your exit price
            notes: Exit reasoning
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get original entry
        c.execute('''
            SELECT actual_entry FROM executions WHERE signal_id = ?
        ''', (signal_id,))
        
        row = c.fetchone()
        if not row or not row[0]:
            print(f"✗ No execution found for signal {signal_id}")
            conn.close()
            return
        
        entry_price = row[0]
        pnl = exit_price - entry_price
        
        c.execute('''
            UPDATE executions 
            SET actual_exit = ?, actual_pnl = ?, notes = notes || ?
            WHERE signal_id = ?
        ''', (exit_price, pnl, f"\nExit: {notes}" if notes else '', signal_id))
        
        c.execute('UPDATE signals SET status = ? WHERE id = ?', 
                 ('closed', signal_id))
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Trade closed: ${pnl:+.2f} P&L")
    
    def scan_and_alert(self, universe: List[str], min_confidence: float = 60):
        """
        Scan universe once and alert on high-confidence signals.
        
        Args:
            universe: List of tickers to scan
            min_confidence: Minimum confidence to alert
        """
        print(f"\nScanning {len(universe)} tickers...")
        print(f"Minimum confidence: {min_confidence}/100\n")
        
        signals = self.scanner.scan_universe(universe)
        
        if signals.empty:
            print("No signals found")
            return
        
        # Filter by confidence
        high_conf = signals[signals['confidence'] >= min_confidence]
        
        if high_conf.empty:
            print(f"No signals above {min_confidence} confidence")
            return
        
        print(f"Found {len(high_conf)} high-confidence signals\n")
        
        # Show each signal and get decision
        for _, signal in high_conf.iterrows():
            signal_id = self.log_signal(signal.to_dict())
            self.display_signal(signal.to_dict(), signal_id)
            
            decision = input("\nYour decision [T/S/W/Q]: ").strip().upper()
            
            if decision == 'Q':
                print("\nValidator stopped")
                break
            elif decision == 'T':
                entry = float(input(f"Entry price (press Enter for ${signal['price']:.2f}): ").strip() or signal['price'])
                notes = input("Notes (optional): ").strip()
                self.record_decision(signal_id, 'executed', entry, notes)
            elif decision == 'S':
                notes = input("Why skipped? (optional): ").strip()
                self.record_decision(signal_id, 'skipped', notes=notes)
            elif decision == 'W':
                self.record_decision(signal_id, 'watching')
            
            print()
    
    def show_performance(self, days: int = 30):
        """Show validation performance."""
        conn = sqlite3.connect(self.db_path)
        
        # Get all closed trades
        query = '''
            SELECT s.ticker, s.signal_type, s.confidence, 
                   e.actual_entry, e.actual_exit, e.actual_pnl
            FROM signals s
            JOIN executions e ON s.id = e.signal_id
            WHERE e.executed = 1 AND e.actual_exit IS NOT NULL
            ORDER BY s.timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("\nNo closed trades yet")
            return
        
        print("\n" + "="*80)
        print("LIVE VALIDATION PERFORMANCE")
        print("="*80)
        
        total_trades = len(df)
        winners = df[df['actual_pnl'] > 0]
        losers = df[df['actual_pnl'] <= 0]
        
        win_rate = len(winners) / total_trades * 100
        avg_win = winners['actual_pnl'].mean() if len(winners) > 0 else 0
        avg_loss = losers['actual_pnl'].mean() if len(losers) > 0 else 0
        total_pnl = df['actual_pnl'].sum()
        
        print(f"\nTotal Trades: {total_trades}")
        print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"Losers: {len(losers)}")
        print(f"\nTotal P&L: ${total_pnl:+.2f}")
        print(f"Avg Win: ${avg_win:+.2f}")
        print(f"Avg Loss: ${avg_loss:+.2f}")
        
        print(f"\n{'='*80}")
        if total_trades < 20:
            print(f"⏳ Need more trades ({20 - total_trades} more for significance)")
        elif win_rate >= 55:
            print(f"✅ STRATEGY VALIDATED - Win rate {win_rate:.1f}% >= 55%")
        else:
            print(f"❌ Strategy not validated - Win rate {win_rate:.1f}% < 55%")
        print("="*80)


def main():
    """Run live validator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trade Validator')
    parser.add_argument('--scan', action='store_true', help='Run one scan')
    parser.add_argument('--monitor', action='store_true', help='Continuous monitoring')
    parser.add_argument('--performance', action='store_true', help='Show performance')
    parser.add_argument('--log-exit', nargs=2, metavar=('ID', 'PRICE'),
                       help='Log trade exit: signal_id exit_price')
    parser.add_argument('--min-confidence', type=float, default=60,
                       help='Minimum confidence threshold')
    parser.add_argument('--paper', action='store_true', 
                       help='Use paper account (default: live data monitoring)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("LIVE TRADE VALIDATOR - No Auto-Execution")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'Paper Account' if args.paper else 'Live Data Monitoring'}")
    print()
    
    validator = LiveValidator()
    
    # Show performance
    if args.performance:
        validator.show_performance()
        return
    
    # Log exit
    if args.log_exit:
        signal_id, exit_price = args.log_exit
        validator.log_exit(int(signal_id), float(exit_price))
        validator.show_performance()
        return
    
    # Connect to IBKR
    if not validator.connect_ibkr(use_paper=args.paper):
        print("Failed to connect. Make sure IBKR Gateway is running.")
        return
    
    # Define universe (liquid stocks for $20K account)
    universe = [
        'AAPL', 'NVDA', 'TSLA', 'AMD', 'META',
        'COIN', 'PLTR', 'HOOD', 'SOFI',
        'SPY', 'QQQ', 'IWM',
        'GME', 'AMC',
        'UPST', 'AFRM'
    ]
    
    try:
        if args.monitor:
            # Continuous monitoring
            print("Starting continuous monitoring...")
            print("Will scan every 30 minutes during market hours")
            print("Press Ctrl+C to stop\n")
            
            import time
            
            while True:
                now = datetime.now().time()
                market_open = dt_time(9, 30) <= now <= dt_time(16, 0)
                
                if market_open:
                    print(f"\n[{datetime.now().strftime('%H:%M')}] Scanning...")
                    validator.scan_and_alert(universe, args.min_confidence)
                    print(f"\nNext scan in 30 minutes...")
                    time.sleep(1800)  # 30 minutes
                else:
                    print(f"[{datetime.now().strftime('%H:%M')}] Market closed, waiting...")
                    time.sleep(300)  # 5 minutes
        
        else:
            # Single scan
            validator.scan_and_alert(universe, args.min_confidence)
            
            # Show current performance
            print("\n" + "="*80)
            validator.show_performance()
    
    except KeyboardInterrupt:
        print("\n\nValidator stopped")
        validator.show_performance()
    
    finally:
        if validator.ib and validator.ib.isConnected():
            validator.ib.disconnect()


if __name__ == "__main__":
    main()

