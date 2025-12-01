"""
Morning Scan - Consolidated Daily Alert

Scans entire market via IBKR for unusual activity,
combines with SEC insider data, regime, and sentiment.

Sends ONE concise Telegram alert with top 3 opportunities.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alpha_lab.telegram_alerts import send_message


class MorningScan:
    """Consolidated morning market scan."""
    
    def __init__(self, use_ibkr: bool = True):
        self.use_ibkr = use_ibkr
        self.ib = None
        
    def connect_ibkr(self) -> bool:
        """Connect to IB Gateway."""
        if not self.use_ibkr:
            return False
            
        try:
            from ib_insync import IB
            self.ib = IB()
            # Paper trading port
            self.ib.connect('127.0.0.1', 4002, clientId=10)
            return True
        except Exception as e:
            print(f"IBKR connection failed: {e}")
            return False
            
    def scan_unusual_volume(self, top_n: int = 3) -> List[Dict]:
        """
        Scan ENTIRE US market for unusual volume via IBKR.
        
        NO hardcoded lists - scans thousands of stocks.
        """
        results = []
        
        if not self.ib or not self.ib.isConnected():
            print("  IBKR not connected - cannot scan full market")
            print("  (Run with IBKR to scan entire US market)")
            return []
            
        try:
            from ib_insync import ScannerSubscription
            
            print("  Scanning ENTIRE US market via IBKR...")
            
            # Scan for most active stocks across ALL US stocks
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',  # ALL major US exchanges
                scanCode='MOST_ACTIVE',       # Most active by volume
                numberOfRows=top_n * 5,       # Get extra to filter mega-caps
            )
            
            scan_data = self.ib.reqScannerData(scanner)
            
            # Filter out boring mega-caps everyone watches
            mega_caps = {'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.A', 'BRK.B', 'SPY', 'QQQ'}
            
            for item in scan_data:
                contract = item.contractDetails.contract
                ticker = contract.symbol
                
                if ticker in mega_caps:
                    continue
                    
                name = item.contractDetails.longName[:25] if item.contractDetails.longName else ticker
                
                results.append({
                    'ticker': ticker,
                    'name': name,
                    'vol_ratio': 'high',  # IBKR already filtered for high volume
                    'setup': 'volume surge',
                })
                    
                if len(results) >= top_n:
                    break
                    
        except Exception as e:
            print(f"  IBKR scan error: {e}")
            return []
            
        return results[:top_n]
        
        
    def _get_volume_ratio(self, ticker: str) -> Optional[float]:
        """Get volume ratio for a ticker."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1mo')
            if len(hist) < 5:
                return None
            current = hist['Volume'].iloc[-1]
            avg = hist['Volume'].iloc[:-1].mean()
            return round(current / avg, 1) if avg > 0 else None
        except:
            return None
            
    def _check_setup(self, ticker: str) -> str:
        """Check technical setup for a ticker."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3mo')
            if len(hist) < 20:
                return 'unknown'
                
            price = hist['Close'].iloc[-1]
            high = hist['High'].max()
            sma20 = hist['Close'].iloc[-20:].mean()
            
            if price >= high * 0.98:
                return 'breakout'
            elif price > sma20 and price < high * 0.95:
                return 'consolidating'
            elif price < sma20:
                return 'pullback'
            else:
                return 'neutral'
        except:
            return 'unknown'
            
    def _get_price(self, ticker: str) -> Optional[float]:
        """Get current price."""
        try:
            import yfinance as yf
            return round(yf.Ticker(ticker).history(period='1d')['Close'].iloc[-1], 2)
        except:
            return None
            
    def get_insider_trades(self) -> List[Dict]:
        """Get recent significant insider buys."""
        try:
            from src.alpha_lab.sec_scanner import InsiderTradeAlert
            alerter = InsiderTradeAlert()
            # Don't send telegram, just get data
            buys = alerter.scanner.scan_insider_buys(
                alerter.watchlist[:20],  # Check top 20
                min_value=100000
            )
            return buys[:3]  # Top 3
        except Exception as e:
            print(f"  Insider scan error: {e}")
            return []
            
    def get_regime(self) -> Dict:
        """Get current market regime."""
        try:
            import yfinance as yf
            
            spy = yf.Ticker('SPY')
            vix = yf.Ticker('^VIX')
            
            spy_hist = spy.history(period='5d')
            vix_hist = vix.history(period='1d')
            
            spy_price = spy_hist['Close'].iloc[-1]
            spy_change = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-2] - 1) * 100
            vix_price = vix_hist['Close'].iloc[-1]
            
            # Simple regime logic
            if vix_price < 20 and spy_change > -1:
                regime = 'GREEN'
            elif vix_price > 25 or spy_change < -2:
                regime = 'RED'
            else:
                regime = 'YELLOW'
                
            return {
                'regime': regime,
                'spy_price': round(spy_price, 2),
                'spy_change': round(spy_change, 2),
                'vix': round(vix_price, 1),
            }
        except Exception as e:
            print(f"  Regime check error: {e}")
            return {'regime': 'UNKNOWN', 'spy_price': 0, 'spy_change': 0, 'vix': 0}
            
    def get_sentiment(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get FinBERT sentiment for specific tickers."""
        # For now, skip heavy ML - would need news data
        # Placeholder for future enhancement
        return {}
        
    def generate_alert(self) -> str:
        """Generate the full morning alert message."""
        print("\n🔍 Running Morning Scan...")
        
        # Get all data
        print("  • Checking market regime...")
        regime = self.get_regime()
        
        print("  • Scanning for unusual activity...")
        unusual = self.scan_unusual_volume(top_n=3)
        
        print("  • Checking insider trades...")
        insiders = self.get_insider_trades()
        
        # Build message
        lines = [
            f"🔍 MORNING SCAN - {datetime.now().strftime('%b %d')}",
            "",
            "━━━ MARKET ━━━",
        ]
        
        # Regime
        regime_emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}.get(regime['regime'], '⚪')
        spy_dir = '+' if regime['spy_change'] >= 0 else ''
        lines.append(f"{regime_emoji} {regime['regime']} | SPY ${regime['spy_price']} ({spy_dir}{regime['spy_change']}%) | VIX {regime['vix']}")
        
        # Unusual activity
        lines.append("")
        
        if unusual:
            lines.append("━━━ UNUSUAL VOLUME (Full US Market) ━━━")
            for i, stock in enumerate(unusual, 1):
                name = stock.get('name', '')
                lines.append(f"{i}. {stock['ticker']} - {name}")
        else:
            # No IBKR = show this is a limitation
            lines.append("━━━ MARKET SCAN ━━━")
            lines.append("📡 IBKR offline - limited to SEC data")
            
        # Insider trades
        lines.append("")
        lines.append("━━━ INSIDER BUYING ━━━")
        
        if insiders:
            for trade in insiders:
                value = trade['total_value']
                if value >= 1_000_000:
                    val_str = f"${value/1_000_000:.1f}M"
                else:
                    val_str = f"${value/1_000:.0f}K"
                lines.append(f"• {trade['ticker']} - {trade['title'][:15]} bought {val_str}")
        else:
            lines.append("No significant insider buys")
            
        return "\n".join(lines)
        
    def run(self, send_telegram: bool = True) -> str:
        """Run the morning scan and optionally send to Telegram."""
        # Try IBKR connection
        if self.use_ibkr:
            self.connect_ibkr()
            
        # Generate alert
        alert = self.generate_alert()
        
        print("\n" + "="*50)
        print(alert)
        print("="*50)
        
        if send_telegram:
            print("\nSending to Telegram...")
            success = send_message(alert)
            print("✅ Sent!" if success else "❌ Failed to send")
            
        # Cleanup
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            
        return alert


def run_morning_scan(use_ibkr: bool = True, send_telegram: bool = True):
    """Run the morning scan."""
    scanner = MorningScan(use_ibkr=use_ibkr)
    return scanner.run(send_telegram=send_telegram)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Morning Market Scan")
    parser.add_argument("--no-ibkr", action="store_true", help="Skip IBKR connection")
    parser.add_argument("--no-telegram", action="store_true", help="Don't send Telegram")
    
    args = parser.parse_args()
    
    run_morning_scan(
        use_ibkr=not args.no_ibkr,
        send_telegram=not args.no_telegram
    )

