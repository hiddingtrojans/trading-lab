#!/usr/bin/env python3
"""
Trade Tracker - Comprehensive Trade History & Performance Analytics
====================================================================

Tracks all trades over time to validate bot accuracy and performance.
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import os
from pathlib import Path

class TradeTracker:
    """Track and analyze all trades for performance validation."""
    
    def __init__(self, db_path: str = "data/trades.db"):
        """Initialize trade tracker with SQLite database."""
        self.db_path = db_path
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table - records all entries and exits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                entry_price REAL NOT NULL,
                exit_price REAL,
                shares INTEGER NOT NULL,
                stop_price REAL,
                target_price REAL,
                entry_reason TEXT,
                exit_reason TEXT,
                pnl REAL,
                pnl_pct REAL,
                status TEXT DEFAULT 'open',
                session_date DATE NOT NULL,
                commission REAL DEFAULT 0,
                slippage REAL DEFAULT 0,
                hold_time_minutes INTEGER,
                trade_type TEXT DEFAULT 'day_trade',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daily performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                break_even_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                total_commission REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                largest_win REAL DEFAULT 0,
                largest_loss REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Options trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike REAL NOT NULL,
                expiry DATE NOT NULL,
                volume INTEGER,
                open_interest INTEGER,
                unusual_volume_ratio REAL,
                delta REAL,
                current_price REAL,
                underlying_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Validation metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validation_date DATE NOT NULL,
                total_days_tested INTEGER,
                total_trades INTEGER,
                win_rate REAL,
                accuracy REAL,
                total_pnl REAL,
                avg_pnl_per_trade REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                profit_factor REAL,
                meets_threshold BOOLEAN,
                threshold_value REAL DEFAULT 0.55,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_entry(self, symbol: str, entry_price: float, shares: int,
                     stop_price: float, target_price: float, entry_reason: str = None) -> int:
        """Record a new trade entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_date = datetime.now().date()
        entry_time = datetime.now()
        
        cursor.execute("""
            INSERT INTO trades (
                symbol, entry_time, entry_price, shares, stop_price, 
                target_price, entry_reason, session_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (symbol, entry_time, entry_price, shares, stop_price, 
              target_price, entry_reason, session_date))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def record_exit(self, trade_id: int, exit_price: float, exit_reason: str = None) -> Dict:
        """Record trade exit and calculate P&L."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        exit_time = datetime.now()
        
        # Get entry details
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        trade = cursor.fetchone()
        
        if not trade:
            conn.close()
            return {'error': 'Trade not found'}
        
        # Calculate P&L - Fix column indices (0-based after SELECT *)
        # Columns: id, symbol, entry_time, exit_time, entry_price, exit_price, shares...
        entry_price = trade[4]  # entry_price column
        shares = trade[6]  # shares column
        entry_time_str = trade[2]  # entry_time column
        
        pnl = (exit_price - entry_price) * shares
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        # Calculate hold time
        entry_time = datetime.fromisoformat(entry_time_str)
        hold_time_minutes = int((exit_time - entry_time).total_seconds() / 60)
        
        # Update trade
        cursor.execute("""
            UPDATE trades 
            SET exit_time = ?, exit_price = ?, exit_reason = ?,
                pnl = ?, pnl_pct = ?, hold_time_minutes = ?, status = 'closed'
            WHERE id = ?
        """, (exit_time, exit_price, exit_reason, pnl, pnl_pct, hold_time_minutes, trade_id))
        
        conn.commit()
        
        # Update daily performance
        self._update_daily_performance(trade[14])  # session_date column
        
        conn.close()
        
        return {
            'trade_id': trade_id,
            'symbol': trade[2],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_time_minutes': hold_time_minutes
        }
    
    def record_options_scan(self, symbol: str, option_type: str, strike: float,
                           expiry: str, volume: int, open_interest: int,
                           unusual_volume_ratio: float, delta: float,
                           current_price: float, underlying_price: float):
        """Record unusual options activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO options_scans (
                scan_time, symbol, option_type, strike, expiry, volume,
                open_interest, unusual_volume_ratio, delta, current_price,
                underlying_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now(), symbol, option_type, strike, expiry, volume,
              open_interest, unusual_volume_ratio, delta, current_price,
              underlying_price))
        
        conn.commit()
        conn.close()
    
    def _update_daily_performance(self, date: str):
        """Update daily performance metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all closed trades for this date
        cursor.execute("""
            SELECT pnl, pnl_pct, commission 
            FROM trades 
            WHERE session_date = ? AND status = 'closed'
        """, (date,))
        
        trades = cursor.fetchall()
        
        if not trades:
            conn.close()
            return
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t[0] > 0)
        losing_trades = sum(1 for t in trades if t[0] < 0)
        break_even_trades = sum(1 for t in trades if t[0] == 0)
        
        total_pnl = sum(t[0] for t in trades)
        total_commission = sum(t[2] for t in trades)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        wins = [t[0] for t in trades if t[0] > 0]
        losses = [t[0] for t in trades if t[0] < 0]
        
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        
        # Update or insert daily performance
        cursor.execute("""
            INSERT OR REPLACE INTO daily_performance (
                date, total_trades, winning_trades, losing_trades, break_even_trades,
                total_pnl, total_commission, win_rate, largest_win, largest_loss,
                avg_win, avg_loss, profit_factor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, total_trades, winning_trades, losing_trades, break_even_trades,
              total_pnl, total_commission, win_rate, largest_win, largest_loss,
              avg_win, avg_loss, profit_factor))
        
        conn.commit()
        conn.close()
    
    def get_performance_summary(self, days: int = None) -> Dict:
        """Get comprehensive performance summary."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all closed trades
        if days:
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status = 'closed' 
                AND entry_time >= datetime('now', '-' || ? || ' days')
                ORDER BY entry_time DESC
            """, (days,))
        else:
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status = 'closed'
                ORDER BY entry_time DESC
            """)
        
        trades = cursor.fetchall()
        
        if not trades:
            conn.close()
            return {
                'total_trades': 0,
                'message': 'No closed trades found'
            }
        
        # Calculate comprehensive metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t[11] > 0)  # pnl > 0
        losing_trades = sum(1 for t in trades if t[11] < 0)
        
        total_pnl = sum(t[11] for t in trades if t[11] is not None)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        accuracy = win_rate  # Win rate = accuracy for this bot
        
        wins = [t[11] for t in trades if t[11] and t[11] > 0]
        losses = [t[11] for t in trades if t[11] and t[11] < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        
        # Calculate max drawdown
        cumulative_pnl = []
        running_total = 0
        for trade in trades:
            if trade[11]:
                running_total += trade[11]
                cumulative_pnl.append(running_total)
        
        max_drawdown = 0
        if cumulative_pnl:
            peak = cumulative_pnl[0]
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # Get unique trading days
        cursor.execute("""
            SELECT COUNT(DISTINCT session_date) 
            FROM trades 
            WHERE status = 'closed'
        """)
        trading_days = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'trading_days': trading_days,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'accuracy': accuracy,
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': total_pnl / total_trades if total_trades > 0 else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'largest_win': max(wins) if wins else 0,
            'largest_loss': min(losses) if losses else 0,
            'meets_threshold': accuracy >= 55.0,
            'threshold': 55.0,
            'ready_for_production': accuracy >= 55.0 and trading_days >= 100
        }
    
    def get_all_trades(self, limit: int = None) -> List[Dict]:
        """Get all trades as list of dictionaries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades ORDER BY entry_time DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        trades = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = ['id', 'symbol', 'entry_time', 'exit_time', 'entry_price', 'exit_price',
                  'shares', 'stop_price', 'target_price', 'entry_reason', 'exit_reason',
                  'pnl', 'pnl_pct', 'status', 'session_date', 'commission', 'slippage',
                  'hold_time_minutes', 'trade_type', 'created_at']
        
        return [dict(zip(columns, trade)) for trade in trades]
    
    def get_validation_report(self, days: int = 100) -> Dict:
        """Generate validation report for production readiness."""
        summary = self.get_performance_summary(days)
        
        # Determine status
        if summary['total_trades'] == 0:
            status = "NO_DATA"
            recommendation = "Continue testing - no trades recorded yet"
        elif summary['trading_days'] < days:
            status = "INSUFFICIENT_DATA"
            recommendation = f"Continue testing - only {summary['trading_days']}/{days} days completed"
        elif summary['accuracy'] >= 55.0:
            status = "APPROVED"
            recommendation = "✅ Bot meets accuracy threshold - READY FOR PRODUCTION"
        else:
            status = "FAILED"
            recommendation = f"❌ Bot accuracy {summary['accuracy']:.1f}% < 55% threshold - NOT ready for production"
        
        return {
            'validation_period_days': days,
            'actual_trading_days': summary.get('trading_days', 0),
            'total_trades': summary['total_trades'],
            'accuracy': summary['accuracy'],
            'threshold': 55.0,
            'meets_threshold': summary['accuracy'] >= 55.0,
            'status': status,
            'recommendation': recommendation,
            'performance_summary': summary
        }
    
    def export_to_csv(self, filename: str = "data/trades_export.csv"):
        """Export all trades to CSV for analysis."""
        import csv
        
        trades = self.get_all_trades()
        
        if not trades:
            return {'error': 'No trades to export'}
        
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)
        
        return {
            'success': True,
            'filename': filename,
            'trades_exported': len(trades)
        }
    
    def get_daily_performance(self, days: int = 30) -> List[Dict]:
        """Get daily performance for charting."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM daily_performance
            ORDER BY date DESC
            LIMIT ?
        """, (days,))
        
        performance = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'date', 'total_trades', 'winning_trades', 'losing_trades',
                  'break_even_trades', 'total_pnl', 'total_commission', 'win_rate',
                  'largest_win', 'largest_loss', 'avg_win', 'avg_loss',
                  'profit_factor', 'sharpe_ratio', 'max_drawdown', 'created_at']
        
        return [dict(zip(columns, p)) for p in performance]
    
    def clear_all_data(self):
        """Clear all trade data (use with caution!)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM trades")
        cursor.execute("DELETE FROM daily_performance")
        cursor.execute("DELETE FROM options_scans")
        cursor.execute("DELETE FROM validation_metrics")
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'All data cleared'}


def test_trade_tracker():
    """Test the trade tracker with sample data."""
    tracker = TradeTracker()
    
    print("🧪 Testing Trade Tracker...")
    print("="*60)
    
    # Record some sample trades
    print("\n📊 Recording sample trades...")
    
    # Trade 1: Winner
    trade1_id = tracker.record_entry(
        symbol='AAPL',
        entry_price=175.00,
        shares=100,
        stop_price=171.50,
        target_price=180.00,
        entry_reason='Gap up + VWAP test'
    )
    tracker.record_exit(trade1_id, 178.50, 'Take profit hit')
    print(f"✅ Trade 1: AAPL +$350 profit")
    
    # Trade 2: Loser
    trade2_id = tracker.record_entry(
        symbol='TSLA',
        entry_price=250.00,
        shares=50,
        stop_price=245.00,
        target_price=257.50,
        entry_reason='Breakout confirmation'
    )
    tracker.record_exit(trade2_id, 245.00, 'Stop loss hit')
    print(f"❌ Trade 2: TSLA -$250 loss")
    
    # Trade 3: Winner
    trade3_id = tracker.record_entry(
        symbol='NVDA',
        entry_price=450.00,
        shares=25,
        stop_price=441.00,
        target_price=463.50,
        entry_reason='Volume spike + gap up'
    )
    tracker.record_exit(trade3_id, 463.50, 'Take profit hit')
    print(f"✅ Trade 3: NVDA +$337.50 profit")
    
    # Get performance summary
    print("\n📊 Performance Summary:")
    print("="*60)
    summary = tracker.get_performance_summary()
    
    print(f"Total Trades: {summary['total_trades']}")
    print(f"Win Rate: {summary['win_rate']:.1f}%")
    print(f"Accuracy: {summary['accuracy']:.1f}%")
    print(f"Total P&L: ${summary['total_pnl']:.2f}")
    print(f"Avg P&L/Trade: ${summary['avg_pnl_per_trade']:.2f}")
    print(f"Profit Factor: {summary['profit_factor']:.2f}")
    print(f"Meets 55% Threshold: {'✅ YES' if summary['meets_threshold'] else '❌ NO'}")
    
    # Validation report
    print("\n🎯 Validation Report (100-day test):")
    print("="*60)
    validation = tracker.get_validation_report(100)
    print(f"Status: {validation['status']}")
    print(f"Recommendation: {validation['recommendation']}")
    
    print("\n✅ Trade tracker test complete!")

if __name__ == "__main__":
    test_trade_tracker()
