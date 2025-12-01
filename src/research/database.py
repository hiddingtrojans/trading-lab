"""
Research Database

Track your research:
- Thesis on each stock
- Price targets (buy zone, sell zone)
- Notes and observations
- When you first researched it
- Alerts when price hits targets

Your research is your edge. Track it.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import json


DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/research.db')


def get_connection():
    """Get database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS research (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            name TEXT,
            
            -- Your thesis
            thesis TEXT,
            bull_case TEXT,
            bear_case TEXT,
            
            -- Targets
            buy_below REAL,
            sell_above REAL,
            stop_loss REAL,
            
            -- Status
            status TEXT DEFAULT 'watching',  -- watching, buying, holding, sold
            conviction TEXT DEFAULT 'medium',  -- low, medium, high
            
            -- Position (if any)
            shares_owned INTEGER DEFAULT 0,
            avg_cost REAL,
            
            -- Tracking
            first_researched TEXT,
            last_updated TEXT,
            
            -- Alerts
            alert_on_price INTEGER DEFAULT 1,
            alert_on_earnings INTEGER DEFAULT 1,
            alert_on_news INTEGER DEFAULT 0
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS research_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            note TEXT NOT NULL,
            note_type TEXT DEFAULT 'general',  -- general, earnings, news, technical
            created_at TEXT NOT NULL,
            
            FOREIGN KEY (ticker) REFERENCES research(ticker)
        )
    ''')
    
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_research_ticker ON research(ticker)
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_notes_ticker ON research_notes(ticker)
    ''')
    
    conn.commit()
    return conn


def save_research(
    ticker: str,
    name: str = None,
    thesis: str = None,
    bull_case: str = None,
    bear_case: str = None,
    buy_below: float = None,
    sell_above: float = None,
    stop_loss: float = None,
    status: str = 'watching',
    conviction: str = 'medium',
) -> int:
    """Save or update research on a stock."""
    conn = get_connection()
    
    now = datetime.now().isoformat()
    
    # Check if exists
    existing = conn.execute(
        'SELECT id, first_researched FROM research WHERE ticker = ?',
        (ticker.upper(),)
    ).fetchone()
    
    if existing:
        # Update
        conn.execute('''
            UPDATE research SET
                name = COALESCE(?, name),
                thesis = COALESCE(?, thesis),
                bull_case = COALESCE(?, bull_case),
                bear_case = COALESCE(?, bear_case),
                buy_below = COALESCE(?, buy_below),
                sell_above = COALESCE(?, sell_above),
                stop_loss = COALESCE(?, stop_loss),
                status = ?,
                conviction = ?,
                last_updated = ?
            WHERE ticker = ?
        ''', (
            name, thesis, bull_case, bear_case,
            buy_below, sell_above, stop_loss,
            status, conviction, now, ticker.upper()
        ))
        research_id = existing['id']
    else:
        # Insert new
        cursor = conn.execute('''
            INSERT INTO research (
                ticker, name, thesis, bull_case, bear_case,
                buy_below, sell_above, stop_loss,
                status, conviction, first_researched, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker.upper(), name, thesis, bull_case, bear_case,
            buy_below, sell_above, stop_loss,
            status, conviction, now, now
        ))
        research_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return research_id


def add_note(ticker: str, note: str, note_type: str = 'general') -> int:
    """Add a research note."""
    conn = get_connection()
    
    cursor = conn.execute('''
        INSERT INTO research_notes (ticker, note, note_type, created_at)
        VALUES (?, ?, ?, ?)
    ''', (ticker.upper(), note, note_type, datetime.now().isoformat()))
    
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_research(ticker: str) -> Optional[Dict]:
    """Get research for a stock."""
    conn = get_connection()
    
    row = conn.execute(
        'SELECT * FROM research WHERE ticker = ?',
        (ticker.upper(),)
    ).fetchone()
    
    if row:
        result = dict(row)
        
        # Get notes
        notes = conn.execute(
            'SELECT * FROM research_notes WHERE ticker = ? ORDER BY created_at DESC',
            (ticker.upper(),)
        ).fetchall()
        result['notes'] = [dict(n) for n in notes]
        
        conn.close()
        return result
    
    conn.close()
    return None


def get_watchlist() -> List[Dict]:
    """Get all stocks being researched."""
    conn = get_connection()
    
    rows = conn.execute('''
        SELECT * FROM research
        ORDER BY 
            CASE status
                WHEN 'buying' THEN 1
                WHEN 'holding' THEN 2
                WHEN 'watching' THEN 3
                ELSE 4
            END,
            conviction DESC,
            last_updated DESC
    ''').fetchall()
    
    conn.close()
    return [dict(row) for row in rows]


def get_price_alerts() -> List[Dict]:
    """Get stocks with price alerts enabled and targets set."""
    conn = get_connection()
    
    rows = conn.execute('''
        SELECT ticker, name, buy_below, sell_above, stop_loss, status
        FROM research
        WHERE alert_on_price = 1
        AND (buy_below IS NOT NULL OR sell_above IS NOT NULL)
    ''').fetchall()
    
    conn.close()
    return [dict(row) for row in rows]


def update_position(ticker: str, shares: int, avg_cost: float):
    """Update position information."""
    conn = get_connection()
    
    conn.execute('''
        UPDATE research SET
            shares_owned = ?,
            avg_cost = ?,
            status = CASE WHEN ? > 0 THEN 'holding' ELSE status END,
            last_updated = ?
        WHERE ticker = ?
    ''', (shares, avg_cost, shares, datetime.now().isoformat(), ticker.upper()))
    
    conn.commit()
    conn.close()


def format_watchlist() -> str:
    """Format watchlist as readable output."""
    watchlist = get_watchlist()
    
    if not watchlist:
        return "📋 Watchlist is empty. Add stocks with: research.py --add TICKER"
    
    lines = [
        "═" * 60,
        "📋 YOUR RESEARCH WATCHLIST",
        "═" * 60,
        "",
    ]
    
    # Group by status
    by_status = {}
    for stock in watchlist:
        status = stock['status']
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(stock)
    
    status_order = ['buying', 'holding', 'watching', 'sold']
    status_emoji = {
        'buying': '🟢',
        'holding': '📦',
        'watching': '👀',
        'sold': '✅',
    }
    
    for status in status_order:
        if status not in by_status:
            continue
        
        stocks = by_status[status]
        lines.append(f"{status_emoji.get(status, '•')} {status.upper()} ({len(stocks)})")
        lines.append("─" * 40)
        
        for s in stocks:
            conviction_stars = {'high': '⭐⭐⭐', 'medium': '⭐⭐', 'low': '⭐'}.get(s['conviction'], '')
            
            lines.append(f"  {s['ticker']} - {s['name'][:25] if s['name'] else 'Unknown'}")
            lines.append(f"    Conviction: {conviction_stars}")
            
            if s['buy_below']:
                lines.append(f"    Buy below: ${s['buy_below']:.2f}")
            if s['sell_above']:
                lines.append(f"    Sell above: ${s['sell_above']:.2f}")
            
            if s['thesis']:
                lines.append(f"    Thesis: {s['thesis'][:50]}...")
            
            lines.append("")
        
        lines.append("")
    
    lines.append("═" * 60)
    lines.append("Commands:")
    lines.append("  research.py TICKER        - Deep analysis")
    lines.append("  research.py --add TICKER  - Add to watchlist")
    lines.append("  research.py --alerts      - Check price alerts")
    lines.append("═" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    print(format_watchlist())

