"""
Options Flow Scanner - Detect Smart Money via IBKR

Scans for unusual options activity that often precedes big moves:
- Large premium trades (>$50K)
- High volume/OI ratio (>3x normal)
- Far OTM aggressive buying

This is what Unusual Whales charges $40/mo for. We do it free with IBKR.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class OptionsFlow:
    """Represents an unusual options trade."""
    ticker: str
    strike: float
    expiry: str
    call_put: str  # 'C' or 'P'
    premium: float  # Total $ value
    volume: int
    open_interest: int
    vol_oi_ratio: float
    otm_pct: float  # How far out of the money
    spot_price: float
    signal_type: str  # 'LARGE_PREMIUM', 'HIGH_VOL_OI', 'OTM_SWEEP'
    timestamp: datetime


class OptionsFlowScanner:
    """
    Scans IBKR for unusual options activity.
    
    Detects:
    1. Large premium trades (>$50K single trade)
    2. High volume/OI ratio (>3x suggests new positioning)
    3. Far OTM buying (>20% OTM with high volume = speculative bet)
    """
    
    # Thresholds - tune these based on experience
    MIN_PREMIUM = 50000        # $50K minimum premium
    MIN_VOL_OI_RATIO = 3.0     # Volume > 3x open interest
    MIN_OTM_PCT = 15           # 15%+ out of the money
    MIN_OTM_VOLUME = 500       # Minimum volume for OTM alerts
    
    # Default universe - used ONLY if IBKR scanner unavailable
    # When IBKR works, we scan the ENTIRE market for unusual options activity
    FALLBACK_UNIVERSE = [
        # Most liquid options (fallback only)
        'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL',
        'AMD', 'NFLX', 'COIN', 'PLTR', 'SOFI',
    ]
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4002):
        self.host = host
        self.port = port
        self.ib = None
        self.flows: List[OptionsFlow] = []
        
    def connect(self) -> bool:
        """Connect to IBKR."""
        try:
            from ib_insync import IB
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=30, timeout=15)
            print(f"✅ Connected to IBKR - Full market scanning enabled")
            return True
        except Exception as e:
            print(f"⚠️ IBKR unavailable: {e}")
            print(f"   Using fallback universe ({len(self.FALLBACK_UNIVERSE)} tickers)")
            return False
    
    def get_most_active_options_ibkr(self, top_n: int = 20) -> List[str]:
        """
        Use IBKR scanner to find stocks with most active options.
        Returns tickers with unusual options volume - NOT a hardcoded list.
        """
        if not self.ib or not self.ib.isConnected():
            return self.FALLBACK_UNIVERSE
        
        try:
            from ib_insync import ScannerSubscription
            
            print("  📡 Scanning FULL market for active options...")
            
            # Scan for most active options by volume
            scanner = ScannerSubscription(
                instrument='STK',
                locationCode='STK.US.MAJOR',
                scanCode='OPT_VOLUME_MOST_ACTIVE',  # Most active by options volume
                numberOfRows=top_n,
                abovePrice=5,
            )
            
            results = self.ib.reqScannerData(scanner)
            
            tickers = []
            for item in results:
                ticker = item.contractDetails.contract.symbol
                tickers.append(ticker)
            
            if tickers:
                print(f"  ✅ Found {len(tickers)} stocks with active options")
                return tickers
            else:
                print("  ⚠️ Scanner returned empty, using fallback")
                return self.FALLBACK_UNIVERSE
                
        except Exception as e:
            print(f"  ⚠️ IBKR scanner failed: {e}")
            return self.FALLBACK_UNIVERSE
            
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            
    def get_spot_price(self, ticker: str) -> Optional[float]:
        """Get current stock price - uses yfinance for reliability."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            if price:
                return float(price)
            # Fallback to historical
            hist = stock.history(period='1d')
            if len(hist) > 0:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return None
            
    def scan_ticker_options(self, ticker: str) -> List[OptionsFlow]:
        """Scan a single ticker for unusual options activity using yfinance."""
        flows = []
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            # Get spot price
            spot = self.get_spot_price(ticker)
            if not spot:
                return flows
            
            # Get available expirations
            try:
                expirations = stock.options
            except:
                return flows
                
            if not expirations:
                return flows
            
            # Check next 2 expirations
            today = datetime.now()
            for exp_str in expirations[:3]:
                try:
                    exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                    if exp_date < today:
                        continue
                    if exp_date > today + timedelta(days=45):
                        continue
                        
                    # Get option chain
                    chain = stock.option_chain(exp_str)
                    
                    # Check calls
                    for _, row in chain.calls.iterrows():
                        flow = self._check_option_row(
                            ticker, spot, exp_str, 'C', row
                        )
                        if flow:
                            flows.append(flow)
                    
                    # Check puts  
                    for _, row in chain.puts.iterrows():
                        flow = self._check_option_row(
                            ticker, spot, exp_str, 'P', row
                        )
                        if flow:
                            flows.append(flow)
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
            
        return flows
    
    def _check_option_row(
        self, ticker: str, spot: float, expiry: str, right: str, row
    ) -> Optional[OptionsFlow]:
        """Check a single option for unusual activity."""
        try:
            strike = float(row['strike'])
            volume = int(row.get('volume', 0) or 0)
            open_interest = int(row.get('openInterest', 0) or 0)
            last_price = float(row.get('lastPrice', 0) or 0)
            
            if volume < 100 or last_price <= 0:
                return None
            
            # Calculate metrics
            premium = last_price * volume * 100
            vol_oi_ratio = volume / open_interest if open_interest > 0 else 0
            
            if right == 'C':
                otm_pct = ((strike - spot) / spot) * 100
            else:
                otm_pct = ((spot - strike) / spot) * 100
            
            # Check for signals
            signal_type = None
            
            # Large premium (>$50K)
            if premium >= self.MIN_PREMIUM:
                signal_type = 'LARGE_PREMIUM'
            
            # High vol/OI ratio (new positions opening)
            elif vol_oi_ratio >= self.MIN_VOL_OI_RATIO and volume >= 500:
                signal_type = 'HIGH_VOL_OI'
            
            # Far OTM with volume (speculative bets)
            elif otm_pct >= self.MIN_OTM_PCT and volume >= self.MIN_OTM_VOLUME:
                signal_type = 'OTM_SWEEP'
            
            if signal_type:
                return OptionsFlow(
                    ticker=ticker,
                    strike=strike,
                    expiry=expiry.replace('-', ''),
                    call_put=right,
                    premium=premium,
                    volume=volume,
                    open_interest=open_interest,
                    vol_oi_ratio=vol_oi_ratio,
                    otm_pct=otm_pct,
                    spot_price=spot,
                    signal_type=signal_type,
                    timestamp=datetime.now()
                )
        except:
            pass
        return None
        
    def scan_all(self, tickers: List[str] = None) -> List[OptionsFlow]:
        """Scan all tickers for unusual activity."""
        if tickers is None:
            # Try to get most active from IBKR, fallback to universe
            tickers = self.get_most_active_options_ibkr(top_n=20)
            
        all_flows = []
        
        print(f"\n🔍 Scanning {len(tickers)} tickers for unusual options flow...")
        
        for i, ticker in enumerate(tickers):
            print(f"  [{i+1}/{len(tickers)}] {ticker}...", end=' ')
            flows = self.scan_ticker_options(ticker)
            if flows:
                print(f"Found {len(flows)} signals!")
                all_flows.extend(flows)
            else:
                print("clean")
                
            # Rate limiting
            time.sleep(0.5)
            
        # Sort by premium (highest first)
        all_flows.sort(key=lambda x: x.premium, reverse=True)
        
        self.flows = all_flows
        return all_flows
        
    def format_alert(self, flow: OptionsFlow) -> str:
        """Format a single flow for display."""
        emoji = '🟢' if flow.call_put == 'C' else '🔴'
        direction = 'CALL' if flow.call_put == 'C' else 'PUT'
        
        return (
            f"{emoji} {flow.ticker} {flow.strike}{flow.call_put} {flow.expiry[:4]}-{flow.expiry[4:6]}-{flow.expiry[6:]}\n"
            f"   ${flow.premium/1000:.0f}K | Vol: {flow.volume:,} | {flow.signal_type}"
        )
        
    def generate_telegram_alert(self) -> str:
        """Generate Telegram alert for all unusual flows."""
        if not self.flows:
            return None
            
        lines = [
            f"🚨 OPTIONS FLOW ALERT - {datetime.now().strftime('%b %d %H:%M')}",
            "",
        ]
        
        # Group by signal type
        large_premium = [f for f in self.flows if f.signal_type == 'LARGE_PREMIUM']
        high_vol_oi = [f for f in self.flows if f.signal_type == 'HIGH_VOL_OI']
        otm_sweeps = [f for f in self.flows if f.signal_type == 'OTM_SWEEP']
        
        if large_premium:
            lines.append("━━━ LARGE PREMIUM (>$50K) ━━━")
            for flow in large_premium[:5]:
                lines.append(self.format_alert(flow))
            lines.append("")
            
        if high_vol_oi:
            lines.append("━━━ HIGH VOL/OI (New Positions) ━━━")
            for flow in high_vol_oi[:5]:
                lines.append(self.format_alert(flow))
            lines.append("")
            
        if otm_sweeps:
            lines.append("━━━ OTM SWEEPS (Speculative) ━━━")
            for flow in otm_sweeps[:5]:
                lines.append(self.format_alert(flow))
                
        # Summary
        calls = len([f for f in self.flows if f.call_put == 'C'])
        puts = len([f for f in self.flows if f.call_put == 'P'])
        total_premium = sum(f.premium for f in self.flows)
        
        lines.append("")
        lines.append(f"📊 Summary: {calls} calls / {puts} puts | ${total_premium/1000000:.1f}M total")
        
        return '\n'.join(lines)


def run_options_flow_scan(send_telegram: bool = True):
    """Run the options flow scanner."""
    # Load telegram config
    telegram_env = os.path.join(os.path.dirname(__file__), '../../configs/telegram.env')
    if os.path.exists(telegram_env):
        with open(telegram_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    
    scanner = OptionsFlowScanner()
    
    if not scanner.connect():
        print("Failed to connect to IBKR")
        return []
        
    try:
        # Scan for unusual activity
        flows = scanner.scan_all()
        
        if flows:
            alert = scanner.generate_telegram_alert()
            print("\n" + "="*50)
            print(alert)
            print("="*50)
            
            if send_telegram:
                from src.alpha_lab.telegram_alerts import send_message
                send_message(alert)
                print("\n✅ Sent to Telegram")
        else:
            print("\n📭 No unusual options activity detected")
            
        return flows
        
    finally:
        scanner.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Options Flow Scanner")
    parser.add_argument("--no-telegram", action="store_true", help="Don't send Telegram alert")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers to scan")
    
    args = parser.parse_args()
    
    if args.tickers:
        scanner = OptionsFlowScanner()
        if scanner.connect():
            flows = scanner.scan_all(args.tickers.split(','))
            scanner.disconnect()
    else:
        run_options_flow_scan(send_telegram=not args.no_telegram)
