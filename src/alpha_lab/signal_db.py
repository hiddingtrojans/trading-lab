"""
Signal Database - Track all trading signals and their outcomes.

Stores:
- Signal details (ticker, thesis, levels, trade type)
- Entry conditions at signal time
- Outcomes (1d, 5d, 20d returns)
- Win/loss tracking

Monthly review calculates performance metrics.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/signals.db')


def get_connection():
    """Get database connection, creating tables if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            ticker TEXT NOT NULL,
            signal_type TEXT NOT NULL,  -- 'momentum', 'breakout', 'insider', 'volume_spike'
            trade_type TEXT NOT NULL,   -- 'day_trade', 'swing', 'leaps'
            
            -- Entry conditions
            entry_price REAL NOT NULL,
            market_cap_b REAL,
            volume_ratio REAL,
            change_pct REAL,
            
            -- Thesis
            thesis TEXT NOT NULL,
            catalyst TEXT,
            
            -- Levels
            support REAL,
            resistance REAL,
            target_price REAL,
            stop_loss REAL,
            risk_reward REAL,
            
            -- Market context
            spy_price REAL,
            vix REAL,
            regime TEXT,
            
            -- Outcomes (filled by review job)
            price_1d REAL,
            price_5d REAL,
            price_20d REAL,
            return_1d REAL,
            return_5d REAL,
            return_20d REAL,
            hit_target INTEGER,  -- 0/1
            hit_stop INTEGER,    -- 0/1
            outcome TEXT,        -- 'win', 'loss', 'pending'
            reviewed_at TEXT
        )
    ''')
    
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(created_at)
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)
    ''')
    
    conn.commit()
    return conn


def save_signal(
    ticker: str,
    signal_type: str,
    trade_type: str,
    entry_price: float,
    thesis: str,
    catalyst: str = None,
    market_cap_b: float = None,
    volume_ratio: float = None,
    change_pct: float = None,
    support: float = None,
    resistance: float = None,
    target_price: float = None,
    stop_loss: float = None,
    spy_price: float = None,
    vix: float = None,
    regime: str = None,
) -> int:
    """
    Save a new signal to the database.
    Returns signal ID.
    """
    conn = get_connection()
    
    # Calculate risk/reward if we have target and stop
    risk_reward = None
    if target_price and stop_loss and entry_price:
        upside = target_price - entry_price
        downside = entry_price - stop_loss
        if downside > 0:
            risk_reward = round(upside / downside, 2)
    
    cursor = conn.execute('''
        INSERT INTO signals (
            created_at, ticker, signal_type, trade_type,
            entry_price, market_cap_b, volume_ratio, change_pct,
            thesis, catalyst,
            support, resistance, target_price, stop_loss, risk_reward,
            spy_price, vix, regime,
            outcome
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (
        datetime.now().isoformat(),
        ticker,
        signal_type,
        trade_type,
        entry_price,
        market_cap_b,
        volume_ratio,
        change_pct,
        thesis,
        catalyst,
        support,
        resistance,
        target_price,
        stop_loss,
        risk_reward,
        spy_price,
        vix,
        regime,
    ))
    
    conn.commit()
    signal_id = cursor.lastrowid
    conn.close()
    
    return signal_id


def get_pending_signals(days_old: int = 1) -> List[Dict]:
    """Get signals that need outcome review (at least N days old)."""
    conn = get_connection()
    
    cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()
    
    rows = conn.execute('''
        SELECT * FROM signals
        WHERE outcome = 'pending'
        AND created_at < ?
        ORDER BY created_at
    ''', (cutoff,)).fetchall()
    
    conn.close()
    return [dict(row) for row in rows]


def update_signal_outcome(
    signal_id: int,
    price_1d: float = None,
    price_5d: float = None,
    price_20d: float = None,
    hit_target: bool = None,
    hit_stop: bool = None,
):
    """Update a signal with its outcome."""
    conn = get_connection()
    
    # Get original entry price
    row = conn.execute('SELECT entry_price FROM signals WHERE id = ?', (signal_id,)).fetchone()
    if not row:
        conn.close()
        return
    
    entry_price = row['entry_price']
    
    # Calculate returns
    return_1d = ((price_1d / entry_price) - 1) * 100 if price_1d and entry_price else None
    return_5d = ((price_5d / entry_price) - 1) * 100 if price_5d and entry_price else None
    return_20d = ((price_20d / entry_price) - 1) * 100 if price_20d and entry_price else None
    
    # Determine outcome
    if hit_target:
        outcome = 'win'
    elif hit_stop:
        outcome = 'loss'
    elif return_5d is not None:
        outcome = 'win' if return_5d > 0 else 'loss'
    else:
        outcome = 'pending'
    
    conn.execute('''
        UPDATE signals SET
            price_1d = ?,
            price_5d = ?,
            price_20d = ?,
            return_1d = ?,
            return_5d = ?,
            return_20d = ?,
            hit_target = ?,
            hit_stop = ?,
            outcome = ?,
            reviewed_at = ?
        WHERE id = ?
    ''', (
        price_1d,
        price_5d,
        price_20d,
        round(return_1d, 2) if return_1d else None,
        round(return_5d, 2) if return_5d else None,
        round(return_20d, 2) if return_20d else None,
        1 if hit_target else 0,
        1 if hit_stop else 0,
        outcome,
        datetime.now().isoformat(),
        signal_id,
    ))
    
    conn.commit()
    conn.close()


def get_performance_stats(days: int = 30) -> Dict:
    """Get performance statistics for recent signals."""
    conn = get_connection()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Overall stats
    stats = conn.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome = 'pending' THEN 1 ELSE 0 END) as pending,
            AVG(return_1d) as avg_return_1d,
            AVG(return_5d) as avg_return_5d,
            AVG(return_20d) as avg_return_20d,
            MAX(return_5d) as best_trade,
            MIN(return_5d) as worst_trade
        FROM signals
        WHERE created_at > ?
    ''', (cutoff,)).fetchone()
    
    # By signal type
    by_type = conn.execute('''
        SELECT
            signal_type,
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(return_5d) as avg_return
        FROM signals
        WHERE created_at > ? AND outcome != 'pending'
        GROUP BY signal_type
    ''', (cutoff,)).fetchall()
    
    # By trade type
    by_trade = conn.execute('''
        SELECT
            trade_type,
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(return_5d) as avg_return
        FROM signals
        WHERE created_at > ? AND outcome != 'pending'
        GROUP BY trade_type
    ''', (cutoff,)).fetchall()
    
    # Recent signals
    recent = conn.execute('''
        SELECT ticker, signal_type, entry_price, return_5d, outcome, created_at
        FROM signals
        WHERE created_at > ?
        ORDER BY created_at DESC
        LIMIT 10
    ''', (cutoff,)).fetchall()
    
    conn.close()
    
    total = stats['total'] or 0
    wins = stats['wins'] or 0
    losses = stats['losses'] or 0
    completed = wins + losses
    
    return {
        'period_days': days,
        'total_signals': total,
        'completed': completed,
        'pending': stats['pending'] or 0,
        'wins': wins,
        'losses': losses,
        'win_rate': round(wins / completed * 100, 1) if completed > 0 else 0,
        'avg_return_1d': round(stats['avg_return_1d'] or 0, 2),
        'avg_return_5d': round(stats['avg_return_5d'] or 0, 2),
        'avg_return_20d': round(stats['avg_return_20d'] or 0, 2),
        'best_trade': round(stats['best_trade'] or 0, 2),
        'worst_trade': round(stats['worst_trade'] or 0, 2),
        'by_signal_type': [dict(row) for row in by_type],
        'by_trade_type': [dict(row) for row in by_trade],
        'recent': [dict(row) for row in recent],
    }


def get_all_signals(limit: int = 100) -> List[Dict]:
    """Get all signals, most recent first."""
    conn = get_connection()
    rows = conn.execute('''
        SELECT * FROM signals
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    # Test
    print("Testing Signal DB...")
    
    # Save a test signal
    signal_id = save_signal(
        ticker="TEST",
        signal_type="momentum",
        trade_type="swing",
        entry_price=100.0,
        thesis="Test signal for development",
        catalyst="Testing",
        target_price=110.0,
        stop_loss=95.0,
    )
    print(f"Created test signal ID: {signal_id}")
    
    # Get stats
    stats = get_performance_stats(30)
    print(f"Stats: {stats}")

