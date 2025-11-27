#!/usr/bin/env python3
"""
Unified Portfolio Tracker
==========================

Tracks positions across all three strategies:
1. Day trading bot
2. LEAPS positions
3. Scanner trades

Provides unified view of total exposure, P&L, and risk.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import os


class UnifiedPortfolioTracker:
    """Track all positions across strategies."""
    
    def __init__(self, db_path: str = 'data/unified_portfolio.db'):
        """Initialize tracker."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Positions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                strategy TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                stop_loss REAL,
                target_price REAL,
                exit_date TEXT,
                exit_price REAL,
                pnl REAL,
                status TEXT DEFAULT 'open',
                notes TEXT
            )
        ''')
        
        # Daily snapshots for tracking
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                strategy TEXT NOT NULL,
                num_positions INTEGER,
                total_value REAL,
                daily_pnl REAL,
                cumulative_pnl REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_position(self, ticker: str, strategy: str, entry_price: float,
                    quantity: int, stop_loss: float = None, 
                    target_price: float = None, notes: str = None):
        """Add new position."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO positions 
            (ticker, strategy, entry_date, entry_price, quantity, 
             stop_loss, target_price, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
        ''', (ticker, strategy, datetime.now().isoformat(), entry_price,
              quantity, stop_loss, target_price, notes))
        
        conn.commit()
        position_id = c.lastrowid
        conn.close()
        
        print(f"✓ Added {strategy} position: {ticker} @ ${entry_price:.2f} x {quantity}")
        return position_id
    
    def close_position(self, position_id: int, exit_price: float):
        """Close a position."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get position details
        c.execute('SELECT entry_price, quantity FROM positions WHERE id = ?', (position_id,))
        row = c.fetchone()
        
        if not row:
            print(f"✗ Position {position_id} not found")
            conn.close()
            return
        
        entry_price, quantity = row
        pnl = (exit_price - entry_price) * quantity
        
        c.execute('''
            UPDATE positions 
            SET exit_date = ?, exit_price = ?, pnl = ?, status = 'closed'
            WHERE id = ?
        ''', (datetime.now().isoformat(), exit_price, pnl, position_id))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Closed position {position_id}: P&L ${pnl:+.2f}")
        return pnl
    
    def get_open_positions(self, strategy: str = None) -> pd.DataFrame:
        """Get all open positions."""
        conn = sqlite3.connect(self.db_path)
        
        if strategy:
            query = "SELECT * FROM positions WHERE status = 'open' AND strategy = ?"
            df = pd.read_sql_query(query, conn, params=(strategy,))
        else:
            query = "SELECT * FROM positions WHERE status = 'open'"
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        return df
    
    def get_closed_positions(self, days: int = 30) -> pd.DataFrame:
        """Get closed positions from last N days."""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = (datetime.now() - pd.Timedelta(days=days)).isoformat()
        query = """
            SELECT * FROM positions 
            WHERE status = 'closed' AND exit_date >= ?
            ORDER BY exit_date DESC
        """
        df = pd.read_sql_query(query, conn, params=(cutoff,))
        
        conn.close()
        return df
    
    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary."""
        open_positions = self.get_open_positions()
        closed_30d = self.get_closed_positions(30)
        
        # Group by strategy
        summary = {}
        
        for strategy in ['day_bot', 'leaps', 'scanner']:
            strategy_open = open_positions[open_positions['strategy'] == strategy]
            strategy_closed = closed_30d[closed_30d['strategy'] == strategy]
            
            summary[strategy] = {
                'open_positions': len(strategy_open),
                'closed_30d': len(strategy_closed),
                'total_pnl_30d': strategy_closed['pnl'].sum() if len(strategy_closed) > 0 else 0,
                'win_rate_30d': (strategy_closed['pnl'] > 0).sum() / len(strategy_closed) * 100 
                                if len(strategy_closed) > 0 else 0
            }
        
        # Overall
        total_open = len(open_positions)
        total_pnl_30d = closed_30d['pnl'].sum() if len(closed_30d) > 0 else 0
        
        return {
            'strategies': summary,
            'total_open_positions': total_open,
            'total_pnl_30d': total_pnl_30d,
            'total_trades_30d': len(closed_30d)
        }
    
    def display_summary(self):
        """Display formatted portfolio summary."""
        summary = self.get_portfolio_summary()
        
        print("\n" + "="*80)
        print("UNIFIED PORTFOLIO SUMMARY")
        print("="*80)
        
        # By strategy
        print("\nBY STRATEGY:")
        print("-"*80)
        print(f"{'Strategy':<15} {'Open':<8} {'Closed(30d)':<14} {'P&L(30d)':<12} {'Win Rate':<10}")
        print("-"*80)
        
        for strategy, metrics in summary['strategies'].items():
            print(f"{strategy:<15} {metrics['open_positions']:<8} "
                  f"{metrics['closed_30d']:<14} "
                  f"${metrics['total_pnl_30d']:>+10.2f} "
                  f"{metrics['win_rate_30d']:>8.1f}%")
        
        # Overall
        print("-"*80)
        print(f"{'TOTAL':<15} {summary['total_open_positions']:<8} "
              f"{summary['total_trades_30d']:<14} "
              f"${summary['total_pnl_30d']:>+10.2f}")
        print("="*80)
        
        # Show open positions
        open_pos = self.get_open_positions()
        if not open_pos.empty:
            print("\nOPEN POSITIONS:")
            print("-"*80)
            for _, pos in open_pos.iterrows():
                print(f"{pos['ticker']:<6} ({pos['strategy']:<10}): "
                      f"{pos['quantity']:>4} shares @ ${pos['entry_price']:.2f} "
                      f"on {pos['entry_date'][:10]}")
            print()


def main():
    """Demo/CLI for portfolio tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Portfolio Tracker')
    parser.add_argument('--add', nargs=5, metavar=('TICKER', 'STRATEGY', 'PRICE', 'QTY', 'STOP'),
                       help='Add position: ticker strategy price quantity stop')
    parser.add_argument('--close', nargs=2, metavar=('ID', 'PRICE'),
                       help='Close position: id exit_price')
    parser.add_argument('--summary', action='store_true', help='Show portfolio summary')
    parser.add_argument('--open', action='store_true', help='Show open positions')
    
    args = parser.parse_args()
    
    tracker = UnifiedPortfolioTracker()
    
    if args.add:
        ticker, strategy, price, qty, stop = args.add
        tracker.add_position(ticker, strategy, float(price), int(qty), float(stop))
    
    elif args.close:
        pos_id, exit_price = args.close
        tracker.close_position(int(pos_id), float(exit_price))
    
    elif args.summary:
        tracker.display_summary()
    
    elif args.open:
        df = tracker.get_open_positions()
        if df.empty:
            print("No open positions")
        else:
            print(df[['id', 'ticker', 'strategy', 'entry_price', 'quantity', 'entry_date']])
    
    else:
        # Default: show summary
        tracker.display_summary()


if __name__ == "__main__":
    main()

