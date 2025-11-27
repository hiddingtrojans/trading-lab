#!/usr/bin/env python3
"""
Institutional Memory Module
===========================

Persists "High Volume Nodes" (HVN) detected by the Whale Detector.
This builds a long-term map of where institutions have accumulated or distributed stock.

Database Schema:
- levels (id, ticker, date, price, volume_score, level_type, context)

Usage:
    memory = InstitutionalMemory()
    memory.save_level('NVDA', 180.50, 'ACCUMULATION')
    nearby = memory.check_levels('NVDA', 179.00)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import os
from typing import List, Dict, Optional

class InstitutionalMemory:
    """Manages historical institutional support/resistance levels."""
    
    DB_PATH = 'data/institutional.db'
    
    def __init__(self):
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database."""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(self.DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS whale_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                price REAL NOT NULL,
                level_type TEXT,
                volume_score REAL,
                notes TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
    def save_level(self, ticker: str, price: float, level_type: str, volume_score: float = 0, notes: str = ""):
        """
        Save a detected whale level.
        """
        # Deduplication: Don't save if we have a level within 1% detected in the last 5 days
        recent_levels = self.get_levels(ticker, days=5)
        for level in recent_levels:
            if abs(level['price'] - price) / price < 0.01:
                # Update existing? Or just skip. Let's skip to keep DB clean.
                return
        
        conn = sqlite3.connect(self.DB_PATH)
        c = conn.cursor()
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        c.execute('''
            INSERT INTO whale_levels (ticker, date, price, level_type, volume_score, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticker.upper(), date_str, price, level_type, volume_score, notes))
        
        conn.commit()
        conn.close()
        # print(f"  💾 Saved Institutional Level for {ticker}: ${price:.2f} ({level_type})")

    def get_levels(self, ticker: str, days: int = 90) -> List[Dict]:
        """Get historical levels for a ticker."""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        cutoff_date = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        
        c.execute('''
            SELECT * FROM whale_levels 
            WHERE ticker = ? AND date >= ?
            ORDER BY date DESC
        ''', (ticker.upper(), cutoff_date))
        
        rows = c.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def check_proximity(self, ticker: str, current_price: float, threshold_pct: float = 2.0) -> List[Dict]:
        """
        Check if current price is near any historical whale levels.
        """
        levels = self.get_levels(ticker, days=180) # Look back 6 months
        nearby = []
        
        for level in levels:
            hist_price = level['price']
            dist_pct = (current_price - hist_price) / hist_price * 100
            
            if abs(dist_pct) <= threshold_pct:
                # It's a match
                nearby.append({
                    'price': hist_price,
                    'date': level['date'],
                    'type': level['level_type'],
                    'distance_pct': round(dist_pct, 2),
                    'age_days': (datetime.now() - datetime.strptime(level['date'], '%Y-%m-%d')).days
                })
        
        # Sort by nearness
        nearby.sort(key=lambda x: abs(x['distance_pct']))
        return nearby

if __name__ == "__main__":
    # Test
    mem = InstitutionalMemory()
    mem.save_level('TEST_TICKER', 150.00, 'ACCUMULATION', 10.0, 'High volume node')
    
    alerts = mem.check_proximity('TEST_TICKER', 151.50) # 1% away
    if alerts:
        print(f"Alerts found: {alerts}")
    else:
        print("No alerts")
    
    # Cleanup
    import os
    # os.remove('data/institutional.db')

