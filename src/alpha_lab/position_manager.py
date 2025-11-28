"""
Position Manager - Track open positions and risk exposure
=========================================================

Simple position tracking:
- What are you holding?
- Total $ at risk
- Sector concentration
- Daily P&L

Usage:
    from alpha_lab.position_manager import PositionManager
    
    pm = PositionManager()
    pm.add_position('NVDA', 100, 450.00, 430.00, 500.00)
    pm.show_dashboard()
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import yfinance as yf

# Position database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/positions.json')

# Sector mapping for common tickers
SECTOR_MAP = {
    # Tech
    'NVDA': 'Technology', 'AMD': 'Technology', 'AAPL': 'Technology', 'MSFT': 'Technology',
    'GOOGL': 'Technology', 'META': 'Technology', 'AMZN': 'Technology', 'TSLA': 'Technology',
    'CRM': 'Technology', 'NOW': 'Technology', 'SNOW': 'Technology', 'PLTR': 'Technology',
    'NET': 'Technology', 'CRWD': 'Technology', 'ZS': 'Technology', 'DDOG': 'Technology',
    'MDB': 'Technology', 'DOCN': 'Technology', 'GTLB': 'Technology', 'APP': 'Technology',
    'SMCI': 'Technology', 'ARM': 'Technology', 'IONQ': 'Technology', 'SOUN': 'Technology',
    
    # Fintech
    'SQ': 'Fintech', 'PYPL': 'Fintech', 'SOFI': 'Fintech', 'HOOD': 'Fintech',
    'COIN': 'Fintech', 'AFRM': 'Fintech', 'UPST': 'Fintech',
    
    # Crypto adjacent
    'MARA': 'Crypto', 'RIOT': 'Crypto', 'CLSK': 'Crypto', 'HUT': 'Crypto',
    
    # Consumer
    'LULU': 'Consumer', 'DECK': 'Consumer', 'CROX': 'Consumer', 'ANF': 'Consumer',
    'CAVA': 'Consumer', 'CMG': 'Consumer', 'SHAK': 'Consumer', 'WING': 'Consumer',
    
    # Healthcare/Biotech
    'MRNA': 'Healthcare', 'EXAS': 'Healthcare', 'NTRA': 'Healthcare', 'ILMN': 'Healthcare',
    'VKTX': 'Healthcare', 'AKRO': 'Healthcare', 'BEAM': 'Healthcare',
    
    # Travel/Leisure
    'ABNB': 'Travel', 'UBER': 'Travel', 'LYFT': 'Travel', 'DASH': 'Travel',
    
    # Media/Entertainment
    'NFLX': 'Media', 'ROKU': 'Media', 'SPOT': 'Media', 'SNAP': 'Media', 'PINS': 'Media',
    
    # Energy
    'FSLR': 'Energy', 'ENPH': 'Energy', 'SEDG': 'Energy',
}


class PositionManager:
    """Track open positions and risk."""
    
    def __init__(self, db_path: str = None, account_size: float = 100000):
        self.db_path = db_path or DB_PATH
        self.account_size = account_size
        self.positions = self._load_positions()
    
    def _load_positions(self) -> Dict:
        """Load positions from JSON."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'positions': [], 'closed': [], 'settings': {'account_size': self.account_size}}
    
    def _save_positions(self):
        """Save positions to JSON."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(self.positions, f, indent=2, default=str)
    
    def add_position(self, ticker: str, shares: int, entry: float, 
                     stop: float, target: float, notes: str = '') -> str:
        """
        Add a new position.
        
        Returns:
            Position ID
        """
        pos_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        risk_per_share = entry - stop
        total_risk = shares * risk_per_share
        reward = (target - entry) * shares
        
        position = {
            'id': pos_id,
            'ticker': ticker,
            'shares': shares,
            'entry': entry,
            'stop': stop,
            'target': target,
            'risk_per_share': round(risk_per_share, 2),
            'total_risk': round(total_risk, 2),
            'potential_reward': round(reward, 2),
            'rr_ratio': round(reward / total_risk, 1) if total_risk > 0 else 0,
            'sector': SECTOR_MAP.get(ticker, 'Other'),
            'opened_at': datetime.now().isoformat(),
            'notes': notes,
            'status': 'OPEN',
        }
        
        self.positions['positions'].append(position)
        self._save_positions()
        
        return pos_id
    
    def close_position(self, ticker: str, exit_price: float, reason: str = '') -> Optional[Dict]:
        """Close a position by ticker."""
        for pos in self.positions['positions']:
            if pos['ticker'] == ticker and pos['status'] == 'OPEN':
                pos['status'] = 'CLOSED'
                pos['exit_price'] = exit_price
                pos['closed_at'] = datetime.now().isoformat()
                pos['close_reason'] = reason
                
                # Calculate P&L
                pnl = (exit_price - pos['entry']) * pos['shares']
                pnl_pct = (exit_price - pos['entry']) / pos['entry'] * 100
                pos['pnl'] = round(pnl, 2)
                pos['pnl_pct'] = round(pnl_pct, 2)
                
                # Move to closed
                self.positions['closed'].append(pos)
                self.positions['positions'].remove(pos)
                self._save_positions()
                
                return pos
        return None
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions with current prices."""
        positions = []
        
        for pos in self.positions['positions']:
            if pos['status'] != 'OPEN':
                continue
            
            # Get current price
            try:
                stock = yf.Ticker(pos['ticker'])
                current = stock.history(period='1d')['Close'].iloc[-1]
            except:
                current = pos['entry']
            
            # Calculate unrealized P&L
            unrealized_pnl = (current - pos['entry']) * pos['shares']
            unrealized_pct = (current - pos['entry']) / pos['entry'] * 100
            
            # Distance to stop/target
            stop_distance = (current - pos['stop']) / current * 100
            target_distance = (pos['target'] - current) / current * 100
            
            positions.append({
                **pos,
                'current_price': round(current, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'unrealized_pct': round(unrealized_pct, 2),
                'stop_distance': round(stop_distance, 1),
                'target_distance': round(target_distance, 1),
                'position_value': round(current * pos['shares'], 2),
            })
        
        return positions
    
    def get_risk_summary(self) -> Dict:
        """Calculate total risk exposure."""
        positions = self.get_open_positions()
        
        total_risk = sum(p['total_risk'] for p in positions)
        total_value = sum(p['position_value'] for p in positions)
        total_unrealized = sum(p['unrealized_pnl'] for p in positions)
        
        # Sector breakdown
        sector_risk = {}
        sector_exposure = {}
        for p in positions:
            sector = p['sector']
            sector_risk[sector] = sector_risk.get(sector, 0) + p['total_risk']
            sector_exposure[sector] = sector_exposure.get(sector, 0) + p['position_value']
        
        return {
            'position_count': len(positions),
            'total_risk': round(total_risk, 2),
            'total_value': round(total_value, 2),
            'total_unrealized_pnl': round(total_unrealized, 2),
            'risk_pct_of_account': round(total_risk / self.account_size * 100, 1),
            'exposure_pct': round(total_value / self.account_size * 100, 1),
            'sector_risk': sector_risk,
            'sector_exposure': sector_exposure,
        }
    
    def check_alerts(self) -> List[str]:
        """Check for risk alerts."""
        alerts = []
        summary = self.get_risk_summary()
        positions = self.get_open_positions()
        
        # Total risk alert
        if summary['risk_pct_of_account'] > 10:
            alerts.append(f"HIGH RISK: {summary['risk_pct_of_account']}% of account at risk (>10%)")
        
        # Sector concentration
        for sector, exposure in summary['sector_exposure'].items():
            pct = exposure / self.account_size * 100
            if pct > 25:
                alerts.append(f"CONCENTRATION: {sector} is {pct:.0f}% of account (>25%)")
        
        # Individual position alerts
        for p in positions:
            # Near stop
            if p['stop_distance'] < 2:
                alerts.append(f"NEAR STOP: {p['ticker']} only {p['stop_distance']}% above stop")
            
            # Near target
            if p['target_distance'] < 2:
                alerts.append(f"NEAR TARGET: {p['ticker']} only {p['target_distance']}% from target")
            
            # Big unrealized loss
            if p['unrealized_pct'] < -5:
                alerts.append(f"DRAWDOWN: {p['ticker']} down {p['unrealized_pct']:.1f}%")
        
        return alerts
    
    def show_dashboard(self) -> str:
        """Generate position dashboard."""
        positions = self.get_open_positions()
        summary = self.get_risk_summary()
        alerts = self.check_alerts()
        
        lines = []
        lines.append("=" * 60)
        lines.append("POSITION DASHBOARD")
        lines.append("=" * 60)
        
        # Alerts first
        if alerts:
            lines.append("\n⚠️  ALERTS:")
            for alert in alerts:
                lines.append(f"   • {alert}")
        
        # Summary
        lines.append(f"\nACCOUNT SUMMARY (${self.account_size:,.0f} base):")
        lines.append(f"   Positions: {summary['position_count']}")
        lines.append(f"   Total Value: ${summary['total_value']:,.0f} ({summary['exposure_pct']}% deployed)")
        lines.append(f"   Total Risk: ${summary['total_risk']:,.0f} ({summary['risk_pct_of_account']}% of account)")
        lines.append(f"   Unrealized P&L: ${summary['total_unrealized_pnl']:+,.0f}")
        
        # Sector breakdown
        if summary['sector_exposure']:
            lines.append(f"\nSECTOR EXPOSURE:")
            for sector, value in sorted(summary['sector_exposure'].items(), key=lambda x: -x[1]):
                pct = value / self.account_size * 100
                lines.append(f"   {sector}: ${value:,.0f} ({pct:.0f}%)")
        
        # Individual positions
        if positions:
            lines.append(f"\nOPEN POSITIONS:")
            lines.append("-" * 60)
            
            for p in positions:
                pnl_emoji = "+" if p['unrealized_pct'] >= 0 else ""
                lines.append(f"""
{p['ticker']} ({p['shares']} shares)
   Entry: ${p['entry']} | Current: ${p['current_price']} | P&L: {pnl_emoji}{p['unrealized_pct']:.1f}%
   Stop: ${p['stop']} ({p['stop_distance']:+.1f}%) | Target: ${p['target']} ({p['target_distance']:.1f}% away)
   Risk: ${p['total_risk']} | Value: ${p['position_value']:,.0f}""")
        else:
            lines.append("\nNo open positions. Cash is a position.")
        
        return "\n".join(lines)
    
    def get_closed_stats(self, days: int = 30) -> Dict:
        """Get stats on closed positions."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        
        for p in self.positions['closed']:
            if p.get('closed_at'):
                closed_date = datetime.fromisoformat(p['closed_at'])
                if closed_date > cutoff:
                    recent.append(p)
        
        if not recent:
            return {'trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        wins = sum(1 for p in recent if p.get('pnl', 0) > 0)
        total_pnl = sum(p.get('pnl', 0) for p in recent)
        
        return {
            'trades': len(recent),
            'wins': wins,
            'losses': len(recent) - wins,
            'win_rate': round(wins / len(recent) * 100, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(total_pnl / len(recent), 2),
        }


def interactive_add():
    """Interactive position entry."""
    pm = PositionManager()
    
    print("\n📝 ADD NEW POSITION")
    print("-" * 30)
    
    ticker = input("Ticker: ").strip().upper()
    if not ticker:
        return
    
    try:
        shares = int(input("Shares: "))
        entry = float(input("Entry Price: $"))
        stop = float(input("Stop Price: $"))
        target = float(input("Target Price: $"))
    except ValueError:
        print("Invalid input.")
        return
    
    notes = input("Notes (optional): ").strip()
    
    pos_id = pm.add_position(ticker, shares, entry, stop, target, notes)
    print(f"\n✓ Position added: {pos_id}")
    
    # Show risk
    risk = (entry - stop) * shares
    reward = (target - entry) * shares
    print(f"   Risk: ${risk:.0f} | Reward: ${reward:.0f} | R:R = 1:{reward/risk:.1f}")


def interactive_close():
    """Interactive position close."""
    pm = PositionManager()
    positions = pm.get_open_positions()
    
    if not positions:
        print("No open positions to close.")
        return
    
    print("\n📝 CLOSE POSITION")
    print("-" * 30)
    print("Open positions:")
    for i, p in enumerate(positions, 1):
        print(f"   {i}. {p['ticker']} ({p['shares']} @ ${p['entry']})")
    
    try:
        choice = int(input("\nSelect position #: ")) - 1
        if choice < 0 or choice >= len(positions):
            return
    except ValueError:
        return
    
    pos = positions[choice]
    
    try:
        exit_price = float(input(f"Exit price for {pos['ticker']}: $"))
    except ValueError:
        return
    
    reason = input("Reason (hit stop/target/manual): ").strip()
    
    result = pm.close_position(pos['ticker'], exit_price, reason)
    if result:
        print(f"\n✓ Closed {pos['ticker']}: ${result['pnl']:+.0f} ({result['pnl_pct']:+.1f}%)")


if __name__ == "__main__":
    import sys
    
    pm = PositionManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'add':
            interactive_add()
        elif cmd == 'close':
            interactive_close()
        elif cmd == 'alerts':
            alerts = pm.check_alerts()
            if alerts:
                for a in alerts:
                    print(f"⚠️  {a}")
            else:
                print("No alerts. All good.")
        else:
            print(pm.show_dashboard())
    else:
        print(pm.show_dashboard())

