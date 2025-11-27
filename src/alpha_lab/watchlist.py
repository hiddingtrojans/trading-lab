#!/usr/bin/env python3
"""
Watchlist Persistence
=====================

Save and load ticker watchlists to/from disk.
Supports multiple named lists and default list.

Storage: JSON files in data/watchlists/

Usage:
    from alpha_lab.watchlist import Watchlist
    
    wl = Watchlist()
    wl.add("NVDA", "TSLA", "AMD")
    wl.save()
    
    # Later:
    wl = Watchlist()
    tickers = wl.load()
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional


WATCHLIST_DIR = os.path.join(os.path.dirname(__file__), '../../data/watchlists')


class Watchlist:
    """
    Manages persistent watchlists with metadata.
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.tickers: List[str] = []
        self.metadata: Dict = {}
        self._filepath = os.path.join(WATCHLIST_DIR, f"{name}.json")
        
        os.makedirs(WATCHLIST_DIR, exist_ok=True)
        
        # Auto-load if exists
        if os.path.exists(self._filepath):
            self.load()
    
    def add(self, *tickers: str) -> 'Watchlist':
        """Add tickers to watchlist."""
        for ticker in tickers:
            ticker = ticker.upper().strip()
            if ticker and ticker not in self.tickers:
                self.tickers.append(ticker)
        return self
    
    def remove(self, *tickers: str) -> 'Watchlist':
        """Remove tickers from watchlist."""
        for ticker in tickers:
            ticker = ticker.upper().strip()
            if ticker in self.tickers:
                self.tickers.remove(ticker)
        return self
    
    def clear(self) -> 'Watchlist':
        """Clear all tickers."""
        self.tickers = []
        return self
    
    def save(self) -> bool:
        """Save watchlist to disk."""
        try:
            data = {
                'name': self.name,
                'tickers': self.tickers,
                'updated_at': datetime.now().isoformat(),
                'metadata': self.metadata
            }
            
            with open(self._filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving watchlist: {e}")
            return False
    
    def load(self) -> List[str]:
        """Load watchlist from disk."""
        try:
            if os.path.exists(self._filepath):
                with open(self._filepath, 'r') as f:
                    data = json.load(f)
                
                self.tickers = data.get('tickers', [])
                self.metadata = data.get('metadata', {})
            
            return self.tickers
        except Exception as e:
            print(f"Error loading watchlist: {e}")
            return []
    
    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in self.tickers
    
    def __len__(self) -> int:
        return len(self.tickers)
    
    def __iter__(self):
        return iter(self.tickers)
    
    def __repr__(self):
        return f"Watchlist('{self.name}', {len(self.tickers)} tickers)"


# Convenience functions

def load_watchlist(name: str = "default") -> List[str]:
    """Load a watchlist by name."""
    return Watchlist(name).load()


def save_watchlist(tickers: List[str], name: str = "default") -> bool:
    """Save a list of tickers as a watchlist."""
    wl = Watchlist(name)
    wl.tickers = [t.upper().strip() for t in tickers]
    return wl.save()


def list_watchlists() -> List[str]:
    """List all saved watchlists."""
    if not os.path.exists(WATCHLIST_DIR):
        return []
    
    return [
        f.replace('.json', '') 
        for f in os.listdir(WATCHLIST_DIR) 
        if f.endswith('.json')
    ]


def get_all_watchlists() -> Dict[str, List[str]]:
    """Get all watchlists as a dictionary."""
    result = {}
    for name in list_watchlists():
        result[name] = load_watchlist(name)
    return result


# Predefined watchlists

PRESET_WATCHLISTS = {
    'mega_tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
    'semiconductors': ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM', 'TSM', 'MU', 'AMAT'],
    'fintech': ['SQ', 'PYPL', 'COIN', 'HOOD', 'SOFI', 'AFRM', 'UPST'],
    'ev_clean': ['TSLA', 'RIVN', 'LCID', 'NIO', 'XPEV', 'ENPH', 'FSLR'],
    'meme': ['GME', 'AMC', 'BBBY', 'KOSS', 'BB'],
    'biotech': ['MRNA', 'BNTX', 'NVAX', 'REGN', 'VRTX', 'BIIB'],
    'cyclicals': ['CAT', 'DE', 'BA', 'GE', 'HON', 'UNP', 'UPS'],
    'defensive': ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'COST', 'MCD'],
    'reits': ['O', 'SPG', 'AMT', 'PLD', 'EQIX', 'DLR'],
}


def create_preset_watchlists():
    """Create all preset watchlists."""
    for name, tickers in PRESET_WATCHLISTS.items():
        save_watchlist(tickers, name)
    print(f"Created {len(PRESET_WATCHLISTS)} preset watchlists")


class WatchlistManager:
    """
    Interactive watchlist manager for CLI use.
    """
    
    def __init__(self):
        self.current = Watchlist("default")
    
    def interactive(self):
        """Run interactive watchlist manager."""
        print("\nWatchlist Manager")
        print("="*50)
        
        while True:
            print(f"\nCurrent: {self.current.name} ({len(self.current)} tickers)")
            print("\nCommands:")
            print("  1. Show tickers")
            print("  2. Add tickers")
            print("  3. Remove tickers")
            print("  4. Switch watchlist")
            print("  5. List all watchlists")
            print("  6. Create preset watchlists")
            print("  0. Exit")
            
            choice = input("\nSelect: ").strip()
            
            if choice == "1":
                if self.current.tickers:
                    print(f"\n{', '.join(self.current.tickers)}")
                else:
                    print("\nWatchlist is empty")
                    
            elif choice == "2":
                tickers = input("Enter tickers (comma-separated): ").strip()
                if tickers:
                    self.current.add(*tickers.split(','))
                    self.current.save()
                    print(f"Added. Now {len(self.current)} tickers.")
                    
            elif choice == "3":
                tickers = input("Enter tickers to remove: ").strip()
                if tickers:
                    self.current.remove(*tickers.split(','))
                    self.current.save()
                    print(f"Removed. Now {len(self.current)} tickers.")
                    
            elif choice == "4":
                lists = list_watchlists()
                print(f"\nAvailable: {', '.join(lists) if lists else 'none'}")
                name = input("Watchlist name: ").strip()
                if name:
                    self.current = Watchlist(name)
                    print(f"Switched to {name}")
                    
            elif choice == "5":
                all_lists = get_all_watchlists()
                print("\nAll Watchlists:")
                for name, tickers in all_lists.items():
                    print(f"  {name}: {len(tickers)} tickers")
                    
            elif choice == "6":
                create_preset_watchlists()
                
            elif choice == "0":
                break


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "create-presets":
            create_preset_watchlists()
        elif cmd == "list":
            for name in list_watchlists():
                wl = Watchlist(name)
                print(f"{name}: {', '.join(wl.tickers[:5])}{'...' if len(wl) > 5 else ''}")
        elif cmd == "show":
            name = sys.argv[2] if len(sys.argv) > 2 else "default"
            tickers = load_watchlist(name)
            print(f"{name}: {', '.join(tickers)}")
        else:
            print("Usage: watchlist.py [create-presets|list|show <name>]")
    else:
        # Interactive mode
        manager = WatchlistManager()
        manager.interactive()

