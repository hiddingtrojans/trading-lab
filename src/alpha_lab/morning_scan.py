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
        Scan for unusual volume/movers.
        
        Uses IBKR if available, falls back to yfinance premarket scan.
        """
        # Try IBKR first
        if self.ib and self.ib.isConnected():
            results = self._scan_ibkr(top_n)
            if results:
                return results
        
        # Fallback: yfinance premarket scan
        print("  Using yfinance premarket scan...")
        return self._scan_yfinance_premarket(top_n)
    
    def _scan_yfinance_premarket(self, top_n: int = 3) -> List[Dict]:
        """Scan for movers using yfinance."""
        import yfinance as yf
        
        results = []
        
        # Universe of liquid stocks
        universe = [
            # Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CRM',
            'ORCL', 'ADBE', 'NOW', 'SNOW', 'PLTR', 'CRWD', 'NET', 'DDOG', 'ZS', 'MDB',
            'PANW', 'FTNT', 'UBER', 'ABNB', 'SQ', 'SHOP', 'COIN', 'MARA', 'RIOT', 'MSTR',
            # Semiconductors
            'AVGO', 'QCOM', 'TXN', 'MU', 'LRCX', 'KLAC', 'AMAT', 'ASML', 'ARM', 'SMCI',
            # Healthcare
            'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY',
            # Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA',
            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'MPC', 'VLO', 'PSX',
            # Industrial
            'CAT', 'DE', 'BA', 'RTX', 'LMT', 'GE', 'HON', 'UNP', 'UPS', 'FDX',
            # Consumer
            'WMT', 'COST', 'HD', 'LOW', 'TGT', 'NKE', 'SBUX', 'MCD', 'DIS',
            # Recent movers (small/mid cap)
            'IONQ', 'RGTI', 'QUBT', 'KULR', 'RKLB', 'LUNR', 'RDW', 'ASTS', 'JOBY', 'HOOD',
        ]
        
        universe = list(set(universe))
        skip = {'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI'}
        
        for ticker in universe:
            if ticker in skip:
                continue
            try:
                stock = yf.Ticker(ticker)
                
                # Try premarket first
                info = stock.info
                pre_price = info.get('preMarketPrice')
                prev_close = info.get('previousClose', 0)
                
                if pre_price and prev_close:
                    # Premarket available
                    change_pct = ((pre_price - prev_close) / prev_close) * 100
                    price = pre_price
                    is_premarket = True
                else:
                    # Use regular market data
                    hist = stock.history(period='2d')
                    if len(hist) < 2:
                        continue
                    prev_close = hist['Close'].iloc[-2]
                    price = hist['Close'].iloc[-1]
                    change_pct = ((price - prev_close) / prev_close) * 100
                    is_premarket = False
                
                # Only significant movers (>2%)
                if abs(change_pct) < 2:
                    continue
                
                volume = info.get('volume', 0)
                avg_volume = info.get('averageVolume', 1)
                vol_ratio = volume / avg_volume if avg_volume > 0 else 0
                market_cap = info.get('marketCap', 0)
                name = info.get('shortName', ticker)[:30]
                
                results.append({
                    'ticker': ticker,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                    'vol_ratio': vol_ratio,
                    'market_cap_b': market_cap / 1e9 if market_cap else 0,
                    'premarket': is_premarket,
                })
            except:
                continue
        
        # Sort by absolute change
        results.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        return results[:top_n]
    
    def _scan_ibkr(self, top_n: int = 3) -> List[Dict]:
        """Scan via IBKR scanner - uses MOST_ACTIVE then filters with yfinance."""
        results = []
        
        if not self.ib or not self.ib.isConnected():
            return []
            
        try:
            from ib_insync import ScannerSubscription
            import yfinance as yf
            
            print("  Scanning ENTIRE US market via IBKR...")
            
            # Garbage to skip (leveraged ETFs, etc)
            skip_tickers = {
                'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI',
                'SOXS', 'SOXL', 'TQQQ', 'SQQQ', 'UVXY', 'SVXY', 'SPXU', 'SPXS',
                'LABU', 'LABD', 'NUGT', 'DUST', 'JNUG', 'JDST', 'TNA', 'TZA',
                'FAS', 'FAZ', 'ERX', 'ERY', 'GUSH', 'DRIP', 'BOIL', 'KOLD',
                'FNGU', 'FNGD', 'TECL', 'TECS', 'BULZ', 'BERZ', 'WEBL', 'WEBS',
                'NAIL', 'DRN', 'DRV', 'CURE', 'PILL', 'RETL', 'MIDU', 'MIDZ',
                'UDOW', 'SDOW', 'UPRO', 'YANG', 'YINN', 'EDC', 'EDZ',
                'MSTU', 'MSTX', 'MSTZ', 'CONL', 'CONY', 'TSLL', 'TSLS',
                'NVDL', 'NVDS', 'NVDX', 'AMDL', 'AMDS', 'GOOX', 'DRCT',
            }
            
            # Use MOST_ACTIVE - works better on paper accounts
            # (price/marketCap filters don't work on paper)
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode='MOST_ACTIVE',
                numberOfRows=50,
            )
            
            scan_data = self.ib.reqScannerData(scanner)
            print(f"  IBKR returned {len(scan_data)} tickers")
            
            candidates = []
            for item in scan_data:
                ticker = item.contractDetails.contract.symbol
                
                # Skip garbage
                if ticker in skip_tickers:
                    continue
                if any(c.isdigit() for c in ticker):
                    continue
                if ' ' in ticker or len(ticker) > 5:
                    continue
                    
                candidates.append(ticker)
            
            print(f"  Checking {len(candidates[:20])} candidates with yfinance...")
            
            # Get real data from yfinance for each candidate
            for ticker in candidates[:20]:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # Get prices - calculate change manually for accuracy
                    prev_close = info.get('previousClose', 0)
                    price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
                    
                    if not price or not prev_close or prev_close == 0:
                        continue
                    
                    change_pct = ((price - prev_close) / prev_close) * 100
                    market_cap = info.get('marketCap', 0)
                    volume = info.get('volume', 0)
                    avg_volume = info.get('averageVolume', 1)
                    name = info.get('shortName', ticker)[:30]
                    
                    # Filter: price > $5, market cap > $500M
                    if price < 5:
                        continue
                    if market_cap < 500_000_000:
                        continue
                    
                    vol_ratio = volume / avg_volume if avg_volume > 0 else 0
                    
                    # Only significant movers (>2% change OR >2x volume)
                    if abs(change_pct) < 2 and vol_ratio < 2:
                        continue
                    
                    results.append({
                        'ticker': ticker,
                        'name': name,
                        'price': round(price, 2),
                        'change_pct': round(change_pct, 1),
                        'vol_ratio': round(vol_ratio, 1),
                        'market_cap_b': round(market_cap / 1e9, 1),
                        'premarket': False,
                    })
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"  IBKR scan error: {e}")
            return []
            
        # Sort by absolute change % (biggest movers first)
        results.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
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
        """Get current market regime - uses premarket data when available."""
        try:
            import yfinance as yf
            
            spy = yf.Ticker('SPY')
            vix = yf.Ticker('^VIX')
            
            spy_info = spy.info
            vix_hist = vix.history(period='1d')
            
            # Get previous close for comparison
            prev_close = spy_info.get('previousClose', 0)
            
            # Use premarket price if available, otherwise regular market
            pre_price = spy_info.get('preMarketPrice')
            reg_price = spy_info.get('regularMarketPrice')
            
            if pre_price and prev_close:
                spy_price = pre_price
                spy_change = ((pre_price - prev_close) / prev_close) * 100
                is_premarket = True
            elif reg_price and prev_close:
                spy_price = reg_price
                spy_change = ((reg_price - prev_close) / prev_close) * 100
                is_premarket = False
            else:
                # Fallback to historical
                spy_hist = spy.history(period='5d')
                spy_price = spy_hist['Close'].iloc[-1]
                spy_change = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-2] - 1) * 100
                is_premarket = False
            
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
                'premarket': is_premarket if 'is_premarket' in dir() else False,
            }
        except Exception as e:
            print(f"  Regime check error: {e}")
            return {'regime': 'UNKNOWN', 'spy_price': 0, 'spy_change': 0, 'vix': 0, 'premarket': False}
            
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
        pre_tag = " 🌅" if regime.get('premarket') else ""
        lines.append(f"{regime_emoji} {regime['regime']} | SPY ${regime['spy_price']} ({spy_dir}{regime['spy_change']}%){pre_tag} | VIX {regime['vix']}")
        
        # Unusual activity
        lines.append("")
        
        if unusual:
            lines.append("━━━ 🔥 TOP MOVERS ━━━")
            for stock in unusual:
                ticker = stock['ticker']
                name = stock.get('name', '')[:20]
                price = stock.get('price', 0)
                change = stock.get('change_pct', 0)
                vol_ratio = stock.get('vol_ratio', 0)
                mcap = stock.get('market_cap_b', 0)
                is_pre = stock.get('premarket', False)
                
                # Format
                change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                vol_str = f"{vol_ratio:.1f}x vol" if vol_ratio > 1 else ""
                mcap_str = f"${mcap:.1f}B" if mcap >= 1 else f"${mcap*1000:.0f}M"
                pre_tag = " 🌅" if is_pre else ""
                
                lines.append(f"• {ticker} {change_str} @ ${price:.2f}{pre_tag}")
                lines.append(f"  {name} | {mcap_str} | {vol_str}")
        elif self.ib and self.ib.isConnected():
            lines.append("━━━ MARKET SCAN ━━━")
            lines.append("📴 Market closed - no movers")
        else:
            lines.append("━━━ MARKET SCAN ━━━")
            lines.append("📡 IBKR offline - run during market hours")
            
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

