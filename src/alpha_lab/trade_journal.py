#!/usr/bin/env python3
"""
Trade Journal Database
======================

SQLite-based trade logging system for tracking:
- Trade ideas (entries, stops, targets)
- Execution details
- Outcomes and P&L
- Notes and learnings

Schema:
    trades: id, ticker, strategy, direction, entry, stop, target, 
            status, entry_time, exit_time, exit_price, pnl, notes
    
    daily_stats: date, trades, wins, losses, pnl, best_trade, worst_trade
"""

import os
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TradeStatus(Enum):
    PLANNED = "planned"      # Idea logged, not executed
    OPEN = "open"            # Position entered
    CLOSED = "closed"        # Position exited
    CANCELLED = "cancelled"  # Idea abandoned


class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Trade:
    ticker: str
    strategy: str
    direction: str
    entry_price: float
    stop_price: float
    target_price: float
    shares: int = 0
    status: str = "planned"
    entry_time: datetime = None
    exit_time: datetime = None
    exit_price: float = None
    pnl: float = None
    notes: str = ""
    id: int = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def risk_reward(self) -> float:
        """Calculate risk/reward ratio."""
        risk = abs(self.entry_price - self.stop_price)
        reward = abs(self.target_price - self.entry_price)
        return reward / risk if risk > 0 else 0
    
    @property
    def risk_amount(self) -> float:
        """Calculate dollar risk."""
        return abs(self.entry_price - self.stop_price) * self.shares


class TradeJournal:
    """
    SQLite-backed trade journal for persistent logging.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), '../../data/trade_journal.db'
            )
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    strategy TEXT,
                    direction TEXT,
                    entry_price REAL,
                    stop_price REAL,
                    target_price REAL,
                    shares INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'planned',
                    entry_time TEXT,
                    exit_time TEXT,
                    exit_price REAL,
                    pnl REAL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_trades INTEGER,
                    wins INTEGER,
                    losses INTEGER,
                    total_pnl REAL,
                    best_trade_pnl REAL,
                    worst_trade_pnl REAL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(created_at)
            """)
            
            conn.commit()
    
    def log_trade(self, trade: Trade) -> int:
        """Log a new trade idea or execution."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trades (
                    ticker, strategy, direction, entry_price, stop_price, 
                    target_price, shares, status, entry_time, exit_time,
                    exit_price, pnl, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.ticker, trade.strategy, trade.direction,
                trade.entry_price, trade.stop_price, trade.target_price,
                trade.shares, trade.status,
                trade.entry_time.isoformat() if trade.entry_time else None,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.exit_price, trade.pnl, trade.notes,
                trade.created_at.isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def update_trade(self, trade_id: int, **kwargs):
        """Update trade fields."""
        allowed_fields = {
            'status', 'entry_time', 'exit_time', 'exit_price', 
            'pnl', 'notes', 'shares'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return
        
        # Convert datetime objects
        for key in ['entry_time', 'exit_time']:
            if key in updates and isinstance(updates[key], datetime):
                updates[key] = updates[key].isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [trade_id]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE trades SET {set_clause} WHERE id = ?", values)
            conn.commit()
    
    def close_trade(self, trade_id: int, exit_price: float, notes: str = ""):
        """Close a trade and calculate P&L."""
        trade = self.get_trade(trade_id)
        if not trade:
            return None
        
        # Calculate P&L
        if trade['direction'] == 'long':
            pnl = (exit_price - trade['entry_price']) * trade['shares']
        else:
            pnl = (trade['entry_price'] - exit_price) * trade['shares']
        
        self.update_trade(
            trade_id,
            status='closed',
            exit_time=datetime.now(),
            exit_price=exit_price,
            pnl=pnl,
            notes=notes
        )
        
        return pnl
    
    def get_trade(self, trade_id: int) -> Optional[Dict]:
        """Get a single trade by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_trades_by_ticker(self, ticker: str, limit: int = 50) -> List[Dict]:
        """Get trades for a specific ticker."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM trades WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
                (ticker.upper(), limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades_by_date(self, target_date: date) -> List[Dict]:
        """Get all trades for a specific date."""
        date_str = target_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM trades WHERE DATE(created_at) = ? ORDER BY created_at",
                (date_str,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_trades(self, days: int = 30, status: str = None) -> List[Dict]:
        """Get recent trades."""
        query = """
            SELECT * FROM trades 
            WHERE created_at >= date('now', ?)
        """
        params = [f'-{days} days']
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self, days: int = 30) -> Dict:
        """Calculate trading statistics."""
        trades = self.get_recent_trades(days, status='closed')
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'best_trade': None,
                'worst_trade': None
            }
        
        wins = [t for t in trades if t['pnl'] and t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] and t['pnl'] < 0]
        
        total_wins = sum(t['pnl'] for t in wins) if wins else 0
        total_losses = abs(sum(t['pnl'] for t in losses)) if losses else 0
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_pnl': sum(t['pnl'] or 0 for t in trades),
            'avg_win': total_wins / len(wins) if wins else 0,
            'avg_loss': total_losses / len(losses) if losses else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else 0,
            'best_trade': max(trades, key=lambda t: t['pnl'] or 0) if trades else None,
            'worst_trade': min(trades, key=lambda t: t['pnl'] or 0) if trades else None
        }
    
    def get_strategy_performance(self, days: int = 90) -> Dict:
        """Get performance breakdown by strategy."""
        trades = self.get_recent_trades(days, status='closed')
        
        strategies = {}
        for trade in trades:
            strat = trade['strategy'] or 'Unknown'
            if strat not in strategies:
                strategies[strat] = {'trades': 0, 'wins': 0, 'pnl': 0}
            
            strategies[strat]['trades'] += 1
            strategies[strat]['pnl'] += trade['pnl'] or 0
            if trade['pnl'] and trade['pnl'] > 0:
                strategies[strat]['wins'] += 1
        
        # Calculate win rate
        for strat in strategies:
            total = strategies[strat]['trades']
            strategies[strat]['win_rate'] = (
                strategies[strat]['wins'] / total * 100 if total > 0 else 0
            )
        
        return strategies
    
    def print_summary(self, days: int = 30):
        """Print trading summary to console."""
        stats = self.get_statistics(days)
        strat_perf = self.get_strategy_performance(days)
        
        print(f"\n{'='*60}")
        print(f"TRADE JOURNAL - Last {days} Days")
        print('='*60)
        
        print(f"\nOverall Performance:")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total P&L: ${stats['total_pnl']:.2f}")
        print(f"  Avg Win: ${stats['avg_win']:.2f}")
        print(f"  Avg Loss: ${stats['avg_loss']:.2f}")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        
        if strat_perf:
            print(f"\nBy Strategy:")
            for strat, perf in sorted(strat_perf.items(), key=lambda x: x[1]['pnl'], reverse=True):
                print(f"  {strat}: {perf['trades']} trades, "
                      f"{perf['win_rate']:.0f}% win, ${perf['pnl']:.2f}")
        
        if stats['best_trade']:
            best = stats['best_trade']
            print(f"\nBest Trade: {best['ticker']} +${best['pnl']:.2f}")
        
        if stats['worst_trade']:
            worst = stats['worst_trade']
            print(f"Worst Trade: {worst['ticker']} ${worst['pnl']:.2f}")
        
        print('='*60)


if __name__ == "__main__":
    # Test the journal
    journal = TradeJournal()
    
    # Log a test trade
    trade = Trade(
        ticker="NVDA",
        strategy="Gap & Go",
        direction="long",
        entry_price=180.50,
        stop_price=178.00,
        target_price=185.00,
        shares=100,
        status="planned"
    )
    
    trade_id = journal.log_trade(trade)
    print(f"Logged trade ID: {trade_id}")
    
    # Update to open
    journal.update_trade(trade_id, status="open", entry_time=datetime.now())
    
    # Close with profit
    pnl = journal.close_trade(trade_id, exit_price=184.00, notes="Hit first target")
    print(f"Closed with P&L: ${pnl:.2f}")
    
    # Print summary
    journal.print_summary()

