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
        Scan entire market for unusual volume via IBKR.
        
        Returns top N stocks with:
        - Volume > 2x average
        - Price > $10
        - Market cap > $500M
        """
        results = []
        
        if not self.ib or not self.ib.isConnected():
            print("  IBKR not connected, using fallback scan...")
            return self._fallback_volume_scan(top_n)
            
        try:
            from ib_insync import ScannerSubscription
            
            # Create scanner for unusual volume
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode='HIGH_VS_13W_HL',  # High relative to 13-week high/low
                numberOfRows=50,
                abovePrice=10,
                marketCapAbove=500000000,  # $500M+
            )
            
            # Run scan
            scan_data = self.ib.reqScannerData(scanner)
            
            for item in scan_data[:top_n * 3]:  # Get extra to filter
                contract = item.contractDetails.contract
                ticker = contract.symbol
                
                # Get additional data
                vol_ratio = self._get_volume_ratio(ticker)
                setup = self._check_setup(ticker)
                
                if vol_ratio and vol_ratio > 2.0:
                    results.append({
                        'ticker': ticker,
                        'vol_ratio': vol_ratio,
                        'setup': setup,
                        'price': self._get_price(ticker),
                    })
                    
                if len(results) >= top_n:
                    break
                    
            self.ib.cancelScannerSubscription(scanner)
            
        except Exception as e:
            print(f"  IBKR scan error: {e}")
            return self._fallback_volume_scan(top_n)
            
        return results[:top_n]
        
    def _fallback_volume_scan(self, top_n: int = 3) -> List[Dict]:
        """Fallback using yfinance if IBKR unavailable."""
        import yfinance as yf
        
        # Broader universe for scanning
        universe = [
            # Mid-caps with potential
            'HUBS', 'AXON', 'CELH', 'DUOL', 'TOST', 'RKLB', 'IONQ', 'AFRM',
            'SOFI', 'HOOD', 'RIVN', 'LCID', 'DNA', 'PATH', 'CFLT', 'MDB',
            'SNOW', 'NET', 'DDOG', 'ZS', 'CRWD', 'PANW', 'FTNT', 'OKTA',
            'BILL', 'PCTY', 'PAYC', 'GDDY', 'TWLO', 'TTD', 'ROKU', 'SPOT',
            'PINS', 'SNAP', 'MTCH', 'BMBL', 'DASH', 'ABNB', 'EXPE', 'BKNG',
            'WDAY', 'NOW', 'TEAM', 'ADSK', 'ANSS', 'CDNS', 'SNPS', 'KLAC',
            'LRCX', 'AMAT', 'ASML', 'TER', 'ENTG', 'MKSI', 'ONTO', 'FORM',
            # Small caps
            'SMCI', 'VRT', 'AEHR', 'ACLS', 'CAMT', 'ALGM', 'POWI', 'WOLF',
            'ASTS', 'RDW', 'LUNR', 'BWXT', 'KTOS', 'PLTR', 'BBAI', 'SOUN',
        ]
        
        results = []
        
        for ticker in universe:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='3mo')
                
                if len(hist) < 20:
                    continue
                    
                # Calculate volume ratio
                current_vol = hist['Volume'].iloc[-1]
                avg_vol = hist['Volume'].iloc[-20:].mean()
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
                
                # Check if near 52-week high
                current_price = hist['Close'].iloc[-1]
                high_52w = hist['High'].max()
                pct_from_high = (high_52w - current_price) / high_52w * 100
                
                # Filter: unusual volume + near highs
                if vol_ratio > 2.0 and pct_from_high < 10:
                    results.append({
                        'ticker': ticker,
                        'vol_ratio': round(vol_ratio, 1),
                        'setup': 'near 52w high' if pct_from_high < 5 else 'consolidating',
                        'price': round(current_price, 2),
                        'pct_from_high': round(pct_from_high, 1),
                    })
                    
            except Exception:
                continue
                
        # Sort by volume ratio
        results.sort(key=lambda x: x['vol_ratio'], reverse=True)
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
        lines.append("━━━ UNUSUAL ACTIVITY ━━━")
        
        if unusual:
            for i, stock in enumerate(unusual, 1):
                lines.append(f"{i}. {stock['ticker']} - Vol {stock['vol_ratio']}x, {stock['setup']}")
        else:
            lines.append("No unusual activity detected")
            
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

