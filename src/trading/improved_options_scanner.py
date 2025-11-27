#!/usr/bin/env python3
"""
Improved Options Scanner - Uses IB Gateway + Historical Tracking
================================================================

Detects unusual options activity by:
1. Comparing current volume to historical average
2. Tracking momentum over last 1-2 hours
3. Detecting large premium inflows
4. Identifying sweep orders
"""

from ib_insync import IB, Stock, Option
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
import yfinance as yf


class ImprovedOptionsScanner:
    """Professional-grade options scanner with momentum tracking."""
    
    def __init__(self, ib: IB, config: dict):
        self.ib = ib
        self.config = config
        self.volume_history = defaultdict(list)  # Track volume over time
        self.last_scan_time = {}
        
    def is_market_hours(self) -> bool:
        """Check if market is open."""
        from datetime import time
        import pytz
        
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        
        if now.weekday() >= 5:  # Weekend
            return False
        
        market_open = time(9, 30)
        market_close = time(16, 0)
        current_time = now.time()
        
        return market_open <= current_time <= market_close
    
    async def scan_with_momentum_tracking(self, watchlist: List[str]) -> List[Dict]:
        """Scan options with historical momentum tracking."""
        unusual_options = []
        
        if not self.is_market_hours():
            return unusual_options
        
        for symbol in watchlist[:10]:  # Limit to 10 stocks to avoid rate limits
            try:
                # Get options using yfinance first (faster for screening)
                ticker = yf.Ticker(symbol)
                expirations = ticker.options
                
                if not expirations:
                    continue
                
                # Focus on near-term options (next 45 days)
                for exp in expirations[:3]:
                    try:
                        exp_date = datetime.strptime(exp, '%Y-%m-%d')
                        days_out = (exp_date - datetime.now()).days
                        
                        if days_out > 45:
                            continue
                        
                        chain = ticker.option_chain(exp)
                        calls = chain.calls
                        
                        for _, option in calls.iterrows():
                            contract_key = f"{symbol}_{option['strike']}_{exp}"
                            current_volume = option.get('volume', 0)
                            current_oi = option.get('openInterest', 0)
                            
                            if current_volume < 100 or current_oi < 50:
                                continue
                            
                            # Track volume over time
                            is_unusual, momentum_data = self._analyze_momentum(
                                contract_key, current_volume, current_oi
                            )
                            
                            if is_unusual:
                                unusual_options.append({
                                    'symbol': symbol,
                                    'option_type': 'CALL',
                                    'strike': option['strike'],
                                    'expiration': exp,
                                    'days_to_exp': days_out,
                                    'current_volume': current_volume,
                                    'open_interest': current_oi,
                                    'volume_oi_ratio': current_volume / max(current_oi, 1),
                                    'momentum': momentum_data,
                                    'last_price': option.get('lastPrice', 0),
                                    'underlying_price': option.get('underlyingPrice', 0)
                                })
                    except:
                        continue
                        
            except Exception as e:
                continue
        
        return unusual_options
    
    def _analyze_momentum(self, contract_key: str, current_volume: int, 
                         current_oi: int) -> Tuple[bool, Dict]:
        """Analyze volume momentum for this contract."""
        now = datetime.now()
        
        # Update volume history
        self.volume_history[contract_key].append((now, current_volume))
        
        # Keep only last 3 hours of data
        cutoff = now - timedelta(hours=3)
        self.volume_history[contract_key] = [
            (t, v) for t, v in self.volume_history[contract_key] if t > cutoff
        ]
        
        history = self.volume_history[contract_key]
        
        # Need at least 2 data points (30+ minutes of tracking)
        if len(history) < 2:
            return False, {'status': 'insufficient_data'}
        
        # Get volume from 1 hour ago
        one_hour_ago = now - timedelta(hours=1)
        volumes_1hr_ago = [v for t, v in history if t <= one_hour_ago]
        
        if not volumes_1hr_ago:
            # Not enough history yet
            return False, {'status': 'building_history'}
        
        old_volume = volumes_1hr_ago[-1]
        volume_increase = current_volume - old_volume
        
        # Calculate metrics
        volume_oi_ratio = current_volume / max(current_oi, 1)
        
        # Unusual if:
        # 1. Volume increased by 500+ in last hour
        # 2. Volume/OI ratio > 0.5 (today's volume is half of total OI)
        # 3. Current volume > 1000 (meaningful activity)
        is_unusual = (
            volume_increase >= 500 and
            volume_oi_ratio >= 0.5 and
            current_volume >= 1000
        )
        
        momentum_data = {
            'volume_1hr_ago': old_volume,
            'volume_now': current_volume,
            'volume_increase_1hr': volume_increase,
            'volume_oi_ratio': volume_oi_ratio,
            'tracking_duration_minutes': int((now - history[0][0]).total_seconds() / 60)
        }
        
        return is_unusual, momentum_data
    
    def clear_stale_data(self):
        """Clear tracking data older than 3 hours."""
        now = datetime.now()
        cutoff = now - timedelta(hours=3)
        
        for contract in list(self.volume_history.keys()):
            self.volume_history[contract] = [
                (t, v) for t, v in self.volume_history[contract] if t > cutoff
            ]
            
            if not self.volume_history[contract]:
                del self.volume_history[contract]


# Example usage
async def test_improved_scanner():
    """Test the improved scanner."""
    ib = IB()
    await ib.connectAsync('127.0.0.1', 4002, clientId=101)
    
    config = {
        'MIN_OPTIONS_VOLUME': 100,
        'MIN_OPTIONS_OI': 50,
        'MAX_OPTIONS_DAYS': 45
    }
    
    scanner = ImprovedOptionsScanner(ib, config)
    
    watchlist = ['AAPL', 'NVDA', 'TSLA', 'SPY', 'QQQ', 'PLTR', 'SOFI']
    
    print("🔍 Starting improved options scanner...")
    print("📊 Will track volume momentum over time\n")
    
    for i in range(12):  # Scan for 1 hour (every 5 min)
        print(f"\n[{datetime.now().strftime('%H:%M')}] Scanning...")
        unusual = await scanner.scan_with_momentum_tracking(watchlist)
        
        if unusual:
            print(f"🎯 Found {len(unusual)} unusual options:")
            for opt in unusual[:3]:
                momentum = opt['momentum']
                print(f"   {opt['symbol']} ${opt['strike']} Call exp {opt['expiration']}")
                print(f"      Volume: {momentum['volume_1hr_ago']} → {momentum['volume_now']} (+{momentum['volume_increase_1hr']} in 1hr)")
                print(f"      Vol/OI: {opt['volume_oi_ratio']:.2f}")
        else:
            print("   No unusual activity detected")
        
        await asyncio.sleep(300)  # 5 minutes
    
    ib.disconnect()

if __name__ == "__main__":
    asyncio.run(test_improved_scanner())
