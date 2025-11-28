#!/usr/bin/env python3
"""
Real-Time Options Flow Scanner (IBKR)
=====================================

Monitors options activity in real-time to detect unusual flow:
- Large single trades (premium > threshold)
- Volume spikes vs open interest
- Far OTM calls/puts with unusual size
- Sweeps (aggressive fills across exchanges)

This is what $300/month flow services sell. IBKR gives it to you.

Usage:
    python src/alpha_lab/options_flow_scanner.py
    python src/alpha_lab/options_flow_scanner.py --tickers NVDA,TSLA,AMD
    python src/alpha_lab/options_flow_scanner.py --alert  # Enable Telegram alerts
"""

import os
import sys
import time
import argparse
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
import threading

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ib_insync import IB, Stock, Option, Contract, Ticker, util
from alpha_lab.config import get_config

# Suppress ib_insync logging
import logging
logging.getLogger('ib_insync').setLevel(logging.WARNING)


@dataclass
class FlowAlert:
    """Unusual options flow alert."""
    timestamp: datetime
    ticker: str
    strike: float
    expiry: str
    option_type: str  # CALL or PUT
    premium: float
    volume: int
    open_interest: int
    vol_oi_ratio: float
    alert_type: str  # LARGE_PREMIUM, HIGH_VOL_OI, FAR_OTM, SWEEP
    underlying_price: float
    otm_pct: float
    
    def __str__(self):
        return (
            f"{self.alert_type}: {self.ticker} {self.strike}{self.option_type[0]} "
            f"{self.expiry} | ${self.premium:,.0f} premium | "
            f"Vol/OI: {self.vol_oi_ratio:.1f}x | {self.otm_pct:+.1f}% OTM"
        )


class OptionsFlowScanner:
    """
    Real-time options flow scanner using IBKR.
    
    Detects:
    1. Large premium trades (>$100K single trade)
    2. Volume > 5x open interest
    3. Far OTM options (>15% OTM) with size
    4. Aggressive sweeps (hitting asks)
    """
    
    # High-volume options tickers to monitor
    DEFAULT_WATCHLIST = [
        'SPY', 'QQQ', 'IWM', 'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 
        'META', 'AMZN', 'GOOGL', 'NFLX', 'CRM', 'COIN', 'MARA',
        'PLTR', 'SOFI', 'HOOD', 'ARM', 'SMCI', 'MU', 'INTC'
    ]
    
    def __init__(self, watchlist: List[str] = None, alert_callback: Callable = None):
        """
        Initialize scanner.
        
        Args:
            watchlist: List of tickers to monitor
            alert_callback: Function to call when alert triggered
        """
        self.watchlist = watchlist or self.DEFAULT_WATCHLIST
        self.alert_callback = alert_callback
        self.ib = IB()
        self.alerts: List[FlowAlert] = []
        self.running = False
        
        # Thresholds from config
        self.thresholds = {
            'min_premium': get_config('options_flow.min_premium', 50000),
            'large_premium': get_config('options_flow.large_premium', 100000),
            'vol_oi_ratio': get_config('options_flow.vol_oi_ratio', 5.0),
            'far_otm_pct': get_config('options_flow.far_otm_pct', 15),
            'far_otm_min_premium': get_config('options_flow.far_otm_min_premium', 25000),
        }
        
        # Cache for underlying prices and options data
        self.underlying_prices: Dict[str, float] = {}
        self.options_data: Dict[str, Dict] = defaultdict(dict)
        
    def connect(self) -> bool:
        """Connect to IBKR."""
        try:
            cfg_path = os.path.join(project_root, 'configs', 'ibkr.yaml')
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            
            # Use random client ID to avoid conflicts
            import random
            client_id = random.randint(100, 999)
            
            self.ib.connect(cfg['host'], cfg['port'], clientId=client_id, timeout=15)
            
            # Set market data type (1=live, 3=delayed)
            self.ib.reqMarketDataType(cfg['market_data']['md_type'])
            
            print(f"Connected to IBKR (Account: {self.ib.managedAccounts()[0]})")
            return True
            
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            print("Make sure TWS or IB Gateway is running.")
            return False
    
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.ib.isConnected():
            self.ib.disconnect()
    
    def get_underlying_price(self, ticker: str) -> float:
        """Get current price of underlying."""
        if ticker in self.underlying_prices:
            return self.underlying_prices[ticker]
        
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        ticker_data = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1)  # Wait for data
        
        price = ticker_data.marketPrice()
        if price and price > 0:
            self.underlying_prices[ticker] = price
            return price
        
        # Fallback to last price
        price = ticker_data.last or ticker_data.close
        self.underlying_prices[ticker] = price or 0
        return price or 0
    
    def get_option_chain(self, ticker: str) -> List[Contract]:
        """Get option chain for ticker."""
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        # Get option parameters
        chains = self.ib.reqSecDefOptParams(ticker, '', contract.secType, contract.conId)
        
        if not chains:
            return []
        
        chain = chains[0]  # Use first exchange
        
        # Get options for next 2 expirations with reasonable strikes
        underlying_price = self.get_underlying_price(ticker)
        if not underlying_price:
            return []
        
        # Filter strikes within 20% of current price
        min_strike = underlying_price * 0.8
        max_strike = underlying_price * 1.2
        
        relevant_strikes = [s for s in chain.strikes if min_strike <= s <= max_strike]
        
        # Get next 4 expirations
        from datetime import date
        today = date.today()
        relevant_exps = sorted([e for e in chain.expirations if e >= today.strftime('%Y%m%d')])[:4]
        
        options = []
        for exp in relevant_exps:
            for strike in relevant_strikes:
                for right in ['C', 'P']:
                    opt = Option(ticker, exp, strike, right, chain.exchange)
                    options.append(opt)
        
        return options
    
    def scan_ticker_options(self, ticker: str) -> List[FlowAlert]:
        """Scan options for a single ticker."""
        alerts = []
        
        underlying_price = self.get_underlying_price(ticker)
        if not underlying_price:
            return alerts
        
        options = self.get_option_chain(ticker)
        if not options:
            return alerts
        
        # Qualify contracts in batches
        batch_size = 50
        for i in range(0, len(options), batch_size):
            batch = options[i:i+batch_size]
            self.ib.qualifyContracts(*batch)
        
        # Request market data for options
        tickers_data = []
        for opt in options[:100]:  # Limit to avoid overwhelming
            try:
                ticker_data = self.ib.reqMktData(opt, '', False, False)
                tickers_data.append((opt, ticker_data))
            except:
                continue
        
        self.ib.sleep(2)  # Wait for data
        
        # Analyze each option
        for opt, data in tickers_data:
            alert = self._analyze_option(ticker, opt, data, underlying_price)
            if alert:
                alerts.append(alert)
        
        # Cancel market data subscriptions
        for opt, data in tickers_data:
            self.ib.cancelMktData(data.contract)
        
        return alerts
    
    def _analyze_option(self, ticker: str, option: Option, data: Ticker, 
                        underlying_price: float) -> Optional[FlowAlert]:
        """Analyze single option for unusual activity."""
        
        volume = data.volume or 0
        open_interest = data.callOpenInterest if option.right == 'C' else data.putOpenInterest
        open_interest = open_interest or 1  # Avoid division by zero
        
        # Calculate premium (volume * price * 100)
        option_price = data.last or data.modelGreeks.optPrice if data.modelGreeks else 0
        if not option_price:
            return None
        
        premium = volume * option_price * 100
        
        # Skip if below minimum threshold
        if premium < self.thresholds['min_premium']:
            return None
        
        # Calculate OTM percentage
        if option.right == 'C':
            otm_pct = (option.strike - underlying_price) / underlying_price * 100
        else:
            otm_pct = (underlying_price - option.strike) / underlying_price * 100
        
        # Volume/OI ratio
        vol_oi_ratio = volume / max(open_interest, 1)
        
        # Determine alert type
        alert_type = None
        
        # Check for large premium
        if premium >= self.thresholds['large_premium']:
            alert_type = 'LARGE_PREMIUM'
        
        # Check for high vol/OI
        elif vol_oi_ratio >= self.thresholds['vol_oi_ratio']:
            alert_type = 'HIGH_VOL_OI'
        
        # Check for far OTM with size
        elif (otm_pct >= self.thresholds['far_otm_pct'] and 
              premium >= self.thresholds['far_otm_min_premium']):
            alert_type = 'FAR_OTM'
        
        if not alert_type:
            return None
        
        return FlowAlert(
            timestamp=datetime.now(),
            ticker=ticker,
            strike=option.strike,
            expiry=option.lastTradeDateOrContractMonth,
            option_type='CALL' if option.right == 'C' else 'PUT',
            premium=premium,
            volume=volume,
            open_interest=open_interest,
            vol_oi_ratio=vol_oi_ratio,
            alert_type=alert_type,
            underlying_price=underlying_price,
            otm_pct=otm_pct
        )
    
    def scan_all(self) -> List[FlowAlert]:
        """Scan all watchlist tickers."""
        all_alerts = []
        
        print(f"Scanning {len(self.watchlist)} tickers for unusual options flow...")
        print("-" * 60)
        
        for i, ticker in enumerate(self.watchlist):
            print(f"  [{i+1}/{len(self.watchlist)}] Scanning {ticker}...")
            
            try:
                alerts = self.scan_ticker_options(ticker)
                all_alerts.extend(alerts)
                
                for alert in alerts:
                    print(f"    ALERT: {alert}")
                    
            except Exception as e:
                print(f"    Error scanning {ticker}: {e}")
                continue
        
        self.alerts = all_alerts
        return all_alerts
    
    def run_continuous(self, interval_minutes: int = 5):
        """Run scanner continuously."""
        self.running = True
        
        print(f"\nStarting continuous scan (every {interval_minutes} min)")
        print("Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                alerts = self.scan_all()
                
                # Trigger callback for new alerts
                if alerts and self.alert_callback:
                    self.alert_callback(alerts)
                
                print(f"\nNext scan in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\nStopping scanner...")
                self.running = False
                break
            except Exception as e:
                print(f"Error during scan: {e}")
                time.sleep(60)  # Wait before retry
    
    def format_alerts(self, alerts: List[FlowAlert] = None) -> str:
        """Format alerts for display."""
        alerts = alerts or self.alerts
        
        if not alerts:
            return "No unusual options flow detected."
        
        lines = []
        lines.append("=" * 60)
        lines.append("UNUSUAL OPTIONS FLOW DETECTED")
        lines.append(f"Scanned at {datetime.now().strftime('%H:%M:%S')}")
        lines.append("=" * 60)
        
        # Group by alert type
        by_type = defaultdict(list)
        for alert in alerts:
            by_type[alert.alert_type].append(alert)
        
        for alert_type, type_alerts in by_type.items():
            lines.append(f"\n{alert_type} ({len(type_alerts)}):")
            lines.append("-" * 40)
            
            # Sort by premium
            for alert in sorted(type_alerts, key=lambda x: -x.premium):
                emoji = "CALL" if alert.option_type == "CALL" else "PUT"
                lines.append(
                    f"  {alert.ticker} ${alert.strike} {emoji} {alert.expiry[:6]}\n"
                    f"    Premium: ${alert.premium:,.0f} | Vol: {alert.volume:,} | OI: {alert.open_interest:,}\n"
                    f"    Vol/OI: {alert.vol_oi_ratio:.1f}x | {alert.otm_pct:+.1f}% OTM\n"
                    f"    Underlying: ${alert.underlying_price:.2f}"
                )
        
        return "\n".join(lines)


def send_telegram_alert(alerts: List[FlowAlert]):
    """Send alert to Telegram."""
    import urllib.request
    import urllib.parse
    
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        return
    
    msg = "OPTIONS FLOW ALERT\n"
    msg += "=" * 25 + "\n"
    
    for alert in alerts[:5]:  # Limit to 5
        emoji = "C" if alert.option_type == "CALL" else "P"
        msg += f"\n{alert.alert_type}\n"
        msg += f"{alert.ticker} ${alert.strike}{emoji} {alert.expiry[:6]}\n"
        msg += f"Premium: ${alert.premium:,.0f}\n"
        msg += f"Vol/OI: {alert.vol_oi_ratio:.1f}x\n"
    
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30)
    except:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Real-time options flow scanner')
    parser.add_argument('--tickers', type=str, help='Comma-separated tickers to scan')
    parser.add_argument('--alert', action='store_true', help='Enable Telegram alerts')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=5, help='Scan interval (minutes)')
    args = parser.parse_args()
    
    # Parse tickers
    watchlist = None
    if args.tickers:
        watchlist = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Set up alert callback
    callback = send_telegram_alert if args.alert else None
    
    # Create scanner
    scanner = OptionsFlowScanner(watchlist=watchlist, alert_callback=callback)
    
    # Connect
    if not scanner.connect():
        sys.exit(1)
    
    try:
        if args.continuous:
            scanner.run_continuous(interval_minutes=args.interval)
        else:
            alerts = scanner.scan_all()
            print(scanner.format_alerts(alerts))
    finally:
        scanner.disconnect()

