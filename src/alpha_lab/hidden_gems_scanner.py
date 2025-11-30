#!/usr/bin/env python3
"""
HIDDEN GEMS SCANNER
===================

Finds stocks BEFORE they become mainstream.

Scans for:
1. Unusual volume in small/mid caps (institutions accumulating)
2. Insider buying in unknown companies (Form 4)
3. Breaking out of long consolidation (technical)
4. High short interest + catalyst (squeeze potential)

This is where the EDGE is - finding stocks nobody talks about yet.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class HiddenGem:
    """A potential hidden gem stock."""
    ticker: str
    name: str
    market_cap: float  # in millions
    price: float
    signal_type: str
    signal_strength: int  # 1-100
    why: str
    discovered_at: datetime


class HiddenGemsScanner:
    """
    Scans entire market for hidden opportunities.
    
    Focus: Small/mid caps ($200M - $10B) where retail can still get in early.
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4002):
        self.host = host
        self.port = port
        self.ib = None
        self.gems: List[HiddenGem] = []
        
    def connect(self) -> bool:
        """Connect to IBKR."""
        try:
            from ib_insync import IB
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=40, timeout=15)
            print(f"✅ Connected to IBKR")
            return True
        except Exception as e:
            print(f"❌ IBKR connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()

    def scan_unusual_volume_small_caps(self, top_n: int = 10) -> List[HiddenGem]:
        """
        Scan for unusual volume in small/mid caps.
        
        This catches institutional accumulation before it's obvious.
        Market cap: $200M - $10B (sweet spot for retail edge)
        """
        gems = []
        
        if not self.ib or not self.ib.isConnected():
            print("  IBKR required for full market scan")
            return gems
            
        print("\n🔍 Scanning: Unusual Volume in Small/Mid Caps...")
        
        try:
            from ib_insync import ScannerSubscription
            
            # Scan for volume leaders in small/mid cap range
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode='HOT_BY_VOLUME',
                numberOfRows=50,  # Get more to filter
                abovePrice=5,
                belowPrice=200,
                marketCapAbove=200000000,    # $200M min
                marketCapBelow=10000000000,  # $10B max
            )
            
            results = self.ib.reqScannerData(scanner)
            
            # Filter out well-known tickers
            known_tickers = {
                'AMC', 'GME', 'BBBY', 'BB', 'NOK', 'PLTR', 'SOFI', 'HOOD',
                'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'COIN', 'MARA', 'RIOT'
            }
            
            for item in results:
                contract = item.contractDetails.contract
                ticker = contract.symbol
                
                if ticker in known_tickers:
                    continue
                    
                name = item.contractDetails.longName[:40] if item.contractDetails.longName else ticker
                
                gems.append(HiddenGem(
                    ticker=ticker,
                    name=name,
                    market_cap=0,  # Would need separate call
                    price=0,
                    signal_type='UNUSUAL_VOLUME',
                    signal_strength=70,
                    why='Volume surge in small/mid cap - possible accumulation',
                    discovered_at=datetime.now()
                ))
                
                if len(gems) >= top_n:
                    break
                    
        except Exception as e:
            print(f"  Error: {e}")
            
        return gems
        
    def scan_breakout_consolidation(self, top_n: int = 10) -> List[HiddenGem]:
        """
        Scan for stocks breaking out of long consolidation.
        
        These often run hard once they break.
        """
        gems = []
        
        if not self.ib or not self.ib.isConnected():
            return gems
            
        print("\n🔍 Scanning: Breaking Multi-Month Consolidation...")
        
        try:
            from ib_insync import ScannerSubscription
            
            # Scan for 52-week high breakouts in small caps
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode='HIGH_VS_52W_HL',  # Near 52-week high
                numberOfRows=30,
                abovePrice=5,
                belowPrice=100,
                marketCapAbove=200000000,
                marketCapBelow=5000000000,
            )
            
            results = self.ib.reqScannerData(scanner)
            
            for item in results:
                contract = item.contractDetails.contract
                ticker = contract.symbol
                name = item.contractDetails.longName[:40] if item.contractDetails.longName else ticker
                
                gems.append(HiddenGem(
                    ticker=ticker,
                    name=name,
                    market_cap=0,
                    price=0,
                    signal_type='BREAKOUT',
                    signal_strength=65,
                    why='Breaking 52-week high - momentum starting',
                    discovered_at=datetime.now()
                ))
                
                if len(gems) >= top_n:
                    break
                    
        except Exception as e:
            print(f"  Error: {e}")
            
        return gems
        
    def scan_sec_insider_buying(self, top_n: int = 10) -> List[HiddenGem]:
        """
        Scan SEC Form 4 for insider buying in ALL companies.
        
        Not just mega caps - find unknown companies where insiders are loading up.
        """
        gems = []
        
        print("\n🔍 Scanning: SEC Insider Buying (All Companies)...")
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Get recent Form 4 filings
            url = "https://www.sec.gov/cgi-bin/browse-edgar"
            params = {
                'action': 'getcurrent',
                'type': '4',
                'company': '',
                'dateb': '',
                'owner': 'only',
                'count': 100,
                'output': 'atom'
            }
            
            headers = {
                'User-Agent': 'InvestmentScanner/1.0 (educational@example.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                entries = soup.find_all('entry')
                
                seen_tickers = set()
                
                for entry in entries[:50]:
                    title = entry.find('title')
                    if title and ' - ' in title.text:
                        parts = title.text.split(' - ')
                        if len(parts) >= 2:
                            # Extract company info
                            company = parts[0].strip()
                            
                            # Skip if we've seen this company
                            if company in seen_tickers:
                                continue
                            seen_tickers.add(company)
                            
                            # Check if it's a purchase (not just grant/exercise)
                            summary = entry.find('summary')
                            if summary and ('purchase' in summary.text.lower() or 'bought' in summary.text.lower()):
                                gems.append(HiddenGem(
                                    ticker='?',  # Would need to lookup
                                    name=company[:40],
                                    market_cap=0,
                                    price=0,
                                    signal_type='INSIDER_BUY',
                                    signal_strength=75,
                                    why='Insider open-market purchase',
                                    discovered_at=datetime.now()
                                ))
                                
                                if len(gems) >= top_n:
                                    break
                                    
        except Exception as e:
            print(f"  Error scanning SEC: {e}")
            
        return gems
        
    def scan_high_short_interest(self, top_n: int = 10) -> List[HiddenGem]:
        """
        Find stocks with high short interest that could squeeze.
        
        Combine with positive catalyst = potential explosive move.
        """
        gems = []
        
        print("\n🔍 Scanning: High Short Interest...")
        
        # This would ideally use a data provider like Ortex or S3 Partners
        # For now, use free data from Yahoo Finance
        
        try:
            import yfinance as yf
            
            # Get a list of small caps to check
            # In production, this would scan the entire market
            check_tickers = [
                'BYND', 'UPST', 'CVNA', 'W', 'PTON', 'FFIE', 'MULN',
                'GOEV', 'NKLA', 'RIDE', 'FSR', 'REV', 'BBIG', 'ATER',
                'GSAT', 'SKLZ', 'WISH', 'CLOV', 'WKHS', 'SPCE'
            ]
            
            for ticker in check_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    short_pct = info.get('shortPercentOfFloat', 0) or 0
                    
                    if short_pct > 20:  # >20% short interest
                        gems.append(HiddenGem(
                            ticker=ticker,
                            name=info.get('shortName', ticker)[:40],
                            market_cap=info.get('marketCap', 0) / 1e6,
                            price=info.get('currentPrice', 0),
                            signal_type='HIGH_SHORT',
                            signal_strength=60,
                            why=f'{short_pct:.0f}% short - squeeze potential',
                            discovered_at=datetime.now()
                        ))
                        
                        if len(gems) >= top_n:
                            break
                            
                except:
                    continue
                    
        except Exception as e:
            print(f"  Error: {e}")
            
        return gems

    def run_full_scan(self) -> List[HiddenGem]:
        """Run all scans and combine results."""
        all_gems = []
        
        # Try IBKR scans first
        ibkr_connected = self.connect() if not (self.ib and self.ib.isConnected()) else True
        
        if ibkr_connected:
            all_gems.extend(self.scan_unusual_volume_small_caps(5))
            all_gems.extend(self.scan_breakout_consolidation(5))
        
        # SEC scan (always works)
        all_gems.extend(self.scan_sec_insider_buying(5))
        
        # Short interest scan
        all_gems.extend(self.scan_high_short_interest(5))
        
        if ibkr_connected:
            self.disconnect()
            
        # Sort by signal strength
        all_gems.sort(key=lambda x: x.signal_strength, reverse=True)
        
        self.gems = all_gems
        return all_gems
        
    def format_telegram_alert(self) -> str:
        """Format gems for Telegram alert."""
        if not self.gems:
            return None
            
        lines = [
            f"💎 HIDDEN GEMS - {datetime.now().strftime('%b %d')}",
            "",
        ]
        
        # Group by signal type
        by_type = {}
        for gem in self.gems:
            if gem.signal_type not in by_type:
                by_type[gem.signal_type] = []
            by_type[gem.signal_type].append(gem)
            
        type_names = {
            'UNUSUAL_VOLUME': '📊 Unusual Volume (Accumulation)',
            'BREAKOUT': '🚀 Breaking Out',
            'INSIDER_BUY': '👔 Insider Buying',
            'HIGH_SHORT': '🩳 High Short Interest'
        }
        
        for signal_type, gems in by_type.items():
            lines.append(f"━━━ {type_names.get(signal_type, signal_type)} ━━━")
            for gem in gems[:3]:
                ticker_str = gem.ticker if gem.ticker != '?' else ''
                lines.append(f"• {ticker_str} {gem.name}")
                lines.append(f"  {gem.why}")
            lines.append("")
            
        lines.append("Run ./research.py <TICKER> for deep analysis")
        
        return '\n'.join(lines)


def run_hidden_gems_scan(send_telegram: bool = True):
    """Main function to run hidden gems scan."""
    # Load telegram config
    telegram_env = os.path.join(os.path.dirname(__file__), '../../configs/telegram.env')
    if os.path.exists(telegram_env):
        with open(telegram_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    
    print("=" * 50)
    print("  💎 HIDDEN GEMS SCANNER")
    print(f"  📅 {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print("=" * 50)
    
    scanner = HiddenGemsScanner()
    gems = scanner.run_full_scan()
    
    if gems:
        alert = scanner.format_telegram_alert()
        print("\n" + alert)
        
        if send_telegram:
            try:
                from src.alpha_lab.telegram_alerts import send_message
                send_message(alert)
                print("\n✅ Sent to Telegram")
            except Exception as e:
                print(f"\n⚠️ Telegram failed: {e}")
    else:
        print("\n📭 No hidden gems found today")
        
    return gems


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hidden Gems Scanner")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--volume", action="store_true", help="Only scan unusual volume")
    parser.add_argument("--insider", action="store_true", help="Only scan insider buying")
    parser.add_argument("--short", action="store_true", help="Only scan high short interest")
    
    args = parser.parse_args()
    
    run_hidden_gems_scan(send_telegram=not args.no_telegram)

