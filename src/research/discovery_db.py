"""
Discovery Database

Track stock scores over time to find IMPROVEMENTS.
The edge: Seeing stocks get better before the crowd notices.

Schema:
- weekly_scans: Full universe scan results by week
- score_history: Track each stock's score over time
- improvements: Stocks that improved significantly week-over-week
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class StockImprovement:
    """A stock that improved week-over-week."""
    ticker: str
    name: str
    sector: str
    prev_score: int
    curr_score: int
    score_change: int
    prev_revenue_growth: float
    curr_revenue_growth: float
    prev_fcf_positive: bool
    curr_fcf_positive: bool
    improvement_reason: str
    
    @property
    def is_significant(self) -> bool:
        """Improvement is significant if score jumped 10+ points."""
        return self.score_change >= 10
    
    @property
    def fcf_turned_positive(self) -> bool:
        """FCF flipped from negative to positive - huge signal."""
        return not self.prev_fcf_positive and self.curr_fcf_positive


class DiscoveryDatabase:
    """
    SQLite database for tracking stock discovery over time.
    
    Key insight: The edge isn't finding stocks once.
    It's seeing them IMPROVE before others notice.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), 
                '../../data/discovery.db'
            )
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Weekly scan results
        c.execute('''
            CREATE TABLE IF NOT EXISTS weekly_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_date TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                total_scanned INTEGER,
                total_discovered INTEGER,
                scan_criteria TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(year, week_number)
            )
        ''')
        
        # Individual stock scores per scan
        c.execute('''
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap_b REAL,
                price REAL,
                revenue_b REAL,
                revenue_growth REAL,
                gross_margin REAL,
                operating_margin REAL,
                fcf_margin REAL,
                net_cash_b REAL,
                debt_to_equity REAL,
                analyst_count INTEGER,
                insider_ownership REAL,
                pe_ratio REAL,
                ps_ratio REAL,
                score INTEGER NOT NULL,
                discovery_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scan_id) REFERENCES weekly_scans(id),
                UNIQUE(scan_id, ticker)
            )
        ''')
        
        # Score history for tracking trends
        c.execute('''
            CREATE TABLE IF NOT EXISTS score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                score INTEGER NOT NULL,
                revenue_growth REAL,
                fcf_positive INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, year, week_number)
            )
        ''')
        
        # Detected improvements
        c.execute('''
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                detected_date TEXT NOT NULL,
                prev_week INTEGER,
                curr_week INTEGER,
                prev_score INTEGER,
                curr_score INTEGER,
                score_change INTEGER,
                improvement_reason TEXT,
                fcf_turned_positive INTEGER DEFAULT 0,
                alerted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indexes for fast queries
        c.execute('CREATE INDEX IF NOT EXISTS idx_scan_results_ticker ON scan_results(ticker)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_scan_results_score ON scan_results(score DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_score_history_ticker ON score_history(ticker)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_improvements_date ON improvements(detected_date)')
        
        conn.commit()
        conn.close()
    
    def save_weekly_scan(
        self, 
        results: List[Dict],
        criteria: Dict,
        total_scanned: int
    ) -> int:
        """
        Save weekly scan results.
        
        Returns scan_id for reference.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        now = datetime.now()
        week_number = now.isocalendar()[1]
        year = now.year
        
        # Check if we already have a scan for this week
        c.execute(
            'SELECT id FROM weekly_scans WHERE year = ? AND week_number = ?',
            (year, week_number)
        )
        existing = c.fetchone()
        
        if existing:
            # Update existing scan
            scan_id = existing[0]
            c.execute('DELETE FROM scan_results WHERE scan_id = ?', (scan_id,))
            c.execute('''
                UPDATE weekly_scans 
                SET scan_date = ?, total_scanned = ?, total_discovered = ?, scan_criteria = ?
                WHERE id = ?
            ''', (now.isoformat(), total_scanned, len(results), json.dumps(criteria), scan_id))
        else:
            # Create new scan
            c.execute('''
                INSERT INTO weekly_scans (scan_date, week_number, year, total_scanned, total_discovered, scan_criteria)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now.isoformat(), week_number, year, total_scanned, len(results), json.dumps(criteria)))
            scan_id = c.lastrowid
        
        # Save individual results
        for stock in results:
            c.execute('''
                INSERT OR REPLACE INTO scan_results (
                    scan_id, ticker, name, sector, industry, market_cap_b, price,
                    revenue_b, revenue_growth, gross_margin, operating_margin, fcf_margin,
                    net_cash_b, debt_to_equity, analyst_count, insider_ownership,
                    pe_ratio, ps_ratio, score, discovery_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_id,
                stock.get('ticker'),
                stock.get('name'),
                stock.get('sector'),
                stock.get('industry'),
                stock.get('market_cap_b'),
                stock.get('price'),
                stock.get('revenue_b'),
                stock.get('revenue_growth'),
                stock.get('gross_margin'),
                stock.get('operating_margin'),
                stock.get('fcf_margin'),
                stock.get('net_cash_b'),
                stock.get('debt_to_equity'),
                stock.get('analyst_count'),
                stock.get('insider_ownership'),
                stock.get('pe_ratio'),
                stock.get('ps_ratio'),
                stock.get('score'),
                stock.get('discovery_reason'),
            ))
            
            # Also save to score history
            fcf_positive = 1 if stock.get('fcf_margin', 0) > 0 else 0
            c.execute('''
                INSERT OR REPLACE INTO score_history (ticker, week_number, year, score, revenue_growth, fcf_positive)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (stock.get('ticker'), week_number, year, stock.get('score'), stock.get('revenue_growth'), fcf_positive))
        
        conn.commit()
        conn.close()
        
        return scan_id
    
    def find_improvements(self, min_score_change: int = 10) -> List[StockImprovement]:
        """
        Find stocks that improved significantly vs last week.
        
        This is THE key insight - stocks getting better before crowd notices.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        now = datetime.now()
        curr_week = now.isocalendar()[1]
        curr_year = now.year
        
        # Handle year boundary
        if curr_week == 1:
            prev_week = 52
            prev_year = curr_year - 1
        else:
            prev_week = curr_week - 1
            prev_year = curr_year
        
        # Get current week's results
        c.execute('''
            SELECT 
                curr.ticker, curr.name, curr.sector,
                prev.score as prev_score, curr.score as curr_score,
                prev.revenue_growth as prev_rev, curr.revenue_growth as curr_rev,
                prev.fcf_positive as prev_fcf, curr.fcf_positive as curr_fcf
            FROM score_history curr
            LEFT JOIN score_history prev 
                ON curr.ticker = prev.ticker 
                AND prev.week_number = ? 
                AND prev.year = ?
            WHERE curr.week_number = ? AND curr.year = ?
            AND prev.score IS NOT NULL
            AND (curr.score - prev.score) >= ?
            ORDER BY (curr.score - prev.score) DESC
        ''', (prev_week, prev_year, curr_week, curr_year, min_score_change))
        
        improvements = []
        for row in c.fetchall():
            ticker, name, sector, prev_score, curr_score, prev_rev, curr_rev, prev_fcf, curr_fcf = row
            
            # Determine reason for improvement
            reasons = []
            if curr_score - prev_score >= 15:
                reasons.append("Major score jump")
            if curr_fcf == 1 and prev_fcf == 0:
                reasons.append("FCF turned positive")
            if curr_rev > prev_rev + 5:
                reasons.append("Revenue accelerating")
            
            improvement = StockImprovement(
                ticker=ticker,
                name=name or ticker,
                sector=sector or 'Unknown',
                prev_score=prev_score,
                curr_score=curr_score,
                score_change=curr_score - prev_score,
                prev_revenue_growth=prev_rev or 0,
                curr_revenue_growth=curr_rev or 0,
                prev_fcf_positive=bool(prev_fcf),
                curr_fcf_positive=bool(curr_fcf),
                improvement_reason=' + '.join(reasons) if reasons else 'Score improved'
            )
            improvements.append(improvement)
            
            # Record improvement
            c.execute('''
                INSERT INTO improvements (
                    ticker, detected_date, prev_week, curr_week, 
                    prev_score, curr_score, score_change, 
                    improvement_reason, fcf_turned_positive
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker, now.isoformat(), prev_week, curr_week,
                prev_score, curr_score, curr_score - prev_score,
                improvement.improvement_reason,
                1 if improvement.fcf_turned_positive else 0
            ))
        
        conn.commit()
        conn.close()
        
        return improvements
    
    def get_score_trend(self, ticker: str, weeks: int = 8) -> List[Tuple[str, int]]:
        """Get score history for a ticker over past N weeks."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                year || '-W' || printf('%02d', week_number) as week,
                score
            FROM score_history
            WHERE ticker = ?
            ORDER BY year DESC, week_number DESC
            LIMIT ?
        ''', (ticker, weeks))
        
        results = [(row[0], row[1]) for row in c.fetchall()]
        conn.close()
        
        return list(reversed(results))  # Oldest first
    
    def get_top_improvers_all_time(self, limit: int = 20) -> List[Dict]:
        """Get stocks with biggest improvements historically."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                ticker,
                COUNT(*) as improvement_count,
                SUM(score_change) as total_improvement,
                MAX(score_change) as max_single_improvement,
                SUM(fcf_turned_positive) as fcf_flips
            FROM improvements
            GROUP BY ticker
            ORDER BY total_improvement DESC
            LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return results
    
    def get_latest_scan_results(self, min_score: int = 50, limit: int = 50) -> List[Dict]:
        """Get results from the latest weekly scan."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get latest scan
        c.execute('SELECT id FROM weekly_scans ORDER BY year DESC, week_number DESC LIMIT 1')
        row = c.fetchone()
        
        if not row:
            conn.close()
            return []
        
        scan_id = row['id']
        
        c.execute('''
            SELECT * FROM scan_results 
            WHERE scan_id = ? AND score >= ?
            ORDER BY score DESC
            LIMIT ?
        ''', (scan_id, min_score, limit))
        
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return results
    
    def get_new_discoveries(self) -> List[Dict]:
        """
        Find stocks that appeared this week but weren't in last week's scan.
        These are NEW discoveries - stocks that just started meeting criteria.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        now = datetime.now()
        curr_week = now.isocalendar()[1]
        curr_year = now.year
        
        if curr_week == 1:
            prev_week = 52
            prev_year = curr_year - 1
        else:
            prev_week = curr_week - 1
            prev_year = curr_year
        
        c.execute('''
            SELECT curr.*
            FROM score_history curr
            LEFT JOIN score_history prev 
                ON curr.ticker = prev.ticker 
                AND prev.week_number = ? 
                AND prev.year = ?
            WHERE curr.week_number = ? AND curr.year = ?
            AND prev.ticker IS NULL
            ORDER BY curr.score DESC
        ''', (prev_week, prev_year, curr_week, curr_year))
        
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return results

