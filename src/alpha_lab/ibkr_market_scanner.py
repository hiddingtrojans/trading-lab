"""
IBKR Market Scanner - Scans ENTIRE US Market

Uses IB Gateway's scanner API to find unusual activity
across thousands of stocks - NO hardcoded lists.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from ib_insync import IB, Stock, ScannerSubscription


class IBKRMarketScanner:
    """Scan entire US market via IBKR."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4002):
        self.host = host
        self.port = port
        self.ib = IB()
        
    def connect(self) -> bool:
        """Connect to IB Gateway."""
        try:
            self.ib.connect(self.host, self.port, clientId=20)
            print(f"✅ Connected to IBKR on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from IB Gateway."""
        if self.ib.isConnected():
            self.ib.disconnect()
            
    def scan_hot_by_volume(self, top_n: int = 10) -> List[Dict]:
        """
        Scan for stocks with highest volume rate.
        
        This scans ALL US stocks and returns those with
        unusually high volume relative to normal.
        """
        print("\n📊 Scanning: Hot by Volume (entire US market)...")
        
        scanner = ScannerSubscription(
            instrument='STK',
            locationCode='STK.US.MAJOR',  # All major US exchanges
            scanCode='HOT_BY_VOLUME',     # Highest volume rate
            numberOfRows=top_n,
            abovePrice=5,                 # Min $5
            belowPrice=500,               # Max $500
            marketCapAbove=100000000,     # Min $100M market cap
        )
        
        results = self._run_scan(scanner)
        return results
        
    def scan_high_volume_gainers(self, top_n: int = 10) -> List[Dict]:
        """
        Scan for stocks up significantly on high volume.
        """
        print("\n📈 Scanning: High Volume Gainers (entire US market)...")
        
        scanner = ScannerSubscription(
            instrument='STK',
            locationCode='STK.US.MAJOR',
            scanCode='TOP_PERC_GAIN',    # Top % gainers
            numberOfRows=top_n,
            abovePrice=5,
            marketCapAbove=100000000,
            aboveVolume=500000,          # Min 500K volume
        )
        
        results = self._run_scan(scanner)
        return results
        
    def scan_near_52_week_high(self, top_n: int = 10) -> List[Dict]:
        """
        Scan for stocks near 52-week high with volume.
        """
        print("\n🔝 Scanning: Near 52-Week High (entire US market)...")
        
        scanner = ScannerSubscription(
            instrument='STK',
            locationCode='STK.US.MAJOR',
            scanCode='HIGH_VS_52W_HL',   # Near 52-week high
            numberOfRows=top_n,
            abovePrice=5,
            marketCapAbove=100000000,
        )
        
        results = self._run_scan(scanner)
        return results
        
    def scan_most_active(self, top_n: int = 10) -> List[Dict]:
        """
        Most active by dollar volume.
        """
        print("\n💰 Scanning: Most Active (entire US market)...")
        
        scanner = ScannerSubscription(
            instrument='STK',
            locationCode='STK.US.MAJOR',
            scanCode='MOST_ACTIVE_USD',  # Most active by $ volume
            numberOfRows=top_n,
            abovePrice=5,
            marketCapAbove=100000000,
        )
        
        results = self._run_scan(scanner)
        return results
        
    def scan_unusual_volume(self, top_n: int = 10) -> List[Dict]:
        """
        Stocks with volume surge vs average.
        """
        print("\n🚨 Scanning: Unusual Volume (entire US market)...")
        
        scanner = ScannerSubscription(
            instrument='STK',
            locationCode='STK.US.MAJOR',
            scanCode='HOT_BY_VOLUME',
            numberOfRows=top_n * 2,  # Get extra to filter
            abovePrice=5,
            marketCapAbove=200000000,  # $200M+ (skip tiny caps)
        )
        
        results = self._run_scan(scanner)
        
        # Filter to stocks NOT in top mega-caps (the boring ones)
        mega_caps = {'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.A', 'BRK.B'}
        filtered = [r for r in results if r['ticker'] not in mega_caps]
        
        return filtered[:top_n]
        
    def _run_scan(self, scanner: ScannerSubscription) -> List[Dict]:
        """Execute a scanner subscription and return results."""
        results = []
        
        try:
            scan_data = self.ib.reqScannerData(scanner)
            
            for item in scan_data:
                contract = item.contractDetails.contract
                ticker = contract.symbol
                
                # Get current price
                self.ib.qualifyContracts(contract)
                ticker_data = self.ib.reqMktData(contract)
                self.ib.sleep(0.5)  # Wait for data
                
                price = ticker_data.last or ticker_data.close or 0
                
                results.append({
                    'ticker': ticker,
                    'name': item.contractDetails.longName[:30] if item.contractDetails.longName else ticker,
                    'price': round(price, 2),
                    'rank': item.rank,
                })
                
                self.ib.cancelMktData(contract)
                
        except Exception as e:
            print(f"  Scan error: {e}")
            
        return results
        
    def get_top_unusual_activity(self, top_n: int = 3) -> List[Dict]:
        """
        Main function: Get top N stocks with unusual activity.
        
        Combines multiple scans to find the best opportunities.
        """
        if not self.ib.isConnected():
            if not self.connect():
                return []
                
        # Run unusual volume scan
        unusual = self.scan_unusual_volume(top_n=top_n)
        
        return unusual


def run_ibkr_scan(top_n: int = 3, send_telegram: bool = True):
    """Run IBKR market scan and send results."""
    from src.alpha_lab.telegram_alerts import send_message
    
    scanner = IBKRMarketScanner()
    
    if not scanner.connect():
        print("Failed to connect to IBKR")
        return []
        
    try:
        # Get regime first
        import yfinance as yf
        spy = yf.Ticker('SPY')
        vix = yf.Ticker('^VIX')
        spy_price = spy.history(period='1d')['Close'].iloc[-1]
        spy_change = spy.history(period='2d')['Close'].pct_change().iloc[-1] * 100
        vix_price = vix.history(period='1d')['Close'].iloc[-1]
        
        if vix_price < 20 and spy_change > -1:
            regime = 'GREEN'
            emoji = '🟢'
        elif vix_price > 25 or spy_change < -2:
            regime = 'RED'
            emoji = '🔴'
        else:
            regime = 'YELLOW'
            emoji = '🟡'
            
        # Run scans
        unusual = scanner.scan_unusual_volume(top_n=top_n)
        
        # Build message
        lines = [
            f"🔍 MARKET SCAN - {datetime.now().strftime('%b %d %H:%M')}",
            "",
            f"{emoji} {regime} | SPY ${spy_price:.2f} ({spy_change:+.1f}%) | VIX {vix_price:.1f}",
            "",
            "━━━ UNUSUAL VOLUME (Full Market Scan) ━━━",
        ]
        
        if unusual:
            for i, stock in enumerate(unusual, 1):
                lines.append(f"{i}. {stock['ticker']} - ${stock['price']} - {stock['name']}")
        else:
            lines.append("No unusual activity detected")
            
        message = "\n".join(lines)
        
        print("\n" + "="*50)
        print(message)
        print("="*50)
        
        if send_telegram:
            send_message(message)
            print("\n✅ Sent to Telegram")
            
        return unusual
        
    finally:
        scanner.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="IBKR Full Market Scanner")
    parser.add_argument("--top", type=int, default=3, help="Number of results")
    parser.add_argument("--no-telegram", action="store_true", help="Don't send to Telegram")
    parser.add_argument("--scan-type", choices=['volume', 'gainers', 'high', 'active'], 
                        default='volume', help="Type of scan")
    
    args = parser.parse_args()
    
    scanner = IBKRMarketScanner()
    
    if scanner.connect():
        if args.scan_type == 'volume':
            results = scanner.scan_unusual_volume(args.top)
        elif args.scan_type == 'gainers':
            results = scanner.scan_high_volume_gainers(args.top)
        elif args.scan_type == 'high':
            results = scanner.scan_near_52_week_high(args.top)
        elif args.scan_type == 'active':
            results = scanner.scan_most_active(args.top)
            
        print(f"\n{'='*50}")
        print(f"Found {len(results)} stocks:")
        for r in results:
            print(f"  {r['ticker']:6} ${r['price']:>8.2f} - {r['name']}")
        print(f"{'='*50}")
        
        scanner.disconnect()

