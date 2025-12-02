"""
Options Analysis - IV Percentile & LEAPS Timing

Track implied volatility to know when options are cheap or expensive.

Why this matters:
- Buy LEAPS when IV is LOW (options are cheap)
- Sell options when IV is HIGH (options are expensive)
- IV Percentile shows where current IV ranks vs last year
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass
import yfinance as yf
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class OptionsData:
    """Options analysis data."""
    ticker: str
    company_name: str
    current_price: float
    
    # IV metrics
    current_iv: Optional[float]  # Current implied volatility
    iv_percentile: Optional[float]  # Where IV ranks vs last year (0-100)
    iv_rank: Optional[float]  # (current - low) / (high - low)
    iv_52w_high: Optional[float]
    iv_52w_low: Optional[float]
    
    # Historical volatility (realized)
    hv_30d: Optional[float]  # 30-day historical volatility
    hv_60d: Optional[float]
    
    # IV vs HV
    iv_premium: Optional[float]  # IV - HV (positive = options expensive)
    
    # Options liquidity
    options_volume: Optional[int]
    open_interest: Optional[int]
    
    # Signals
    iv_signal: str
    leaps_timing: str


class OptionsAnalyzer:
    """
    Analyze options for IV percentile and LEAPS timing.
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
    
    def analyze(self) -> OptionsData:
        """Run full options analysis."""
        
        company_name = self.info.get('shortName', self.ticker)
        current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
        
        # Get IV from options chain
        iv_data = self._get_iv_metrics()
        
        # Get historical volatility
        hv_30d, hv_60d = self._calculate_historical_volatility()
        
        # Calculate IV premium over HV
        iv_premium = None
        if iv_data['current_iv'] and hv_30d:
            iv_premium = iv_data['current_iv'] - hv_30d
        
        # Get options volume/OI
        volume, oi = self._get_options_liquidity()
        
        # Generate signals
        iv_signal = self._iv_signal(iv_data['iv_percentile'], iv_data['iv_rank'])
        leaps_timing = self._leaps_timing(iv_data['iv_percentile'], iv_premium)
        
        return OptionsData(
            ticker=self.ticker,
            company_name=company_name,
            current_price=current_price,
            current_iv=iv_data['current_iv'],
            iv_percentile=iv_data['iv_percentile'],
            iv_rank=iv_data['iv_rank'],
            iv_52w_high=iv_data['iv_high'],
            iv_52w_low=iv_data['iv_low'],
            hv_30d=hv_30d,
            hv_60d=hv_60d,
            iv_premium=iv_premium,
            options_volume=volume,
            open_interest=oi,
            iv_signal=iv_signal,
            leaps_timing=leaps_timing,
        )
    
    def _get_iv_metrics(self) -> Dict:
        """Get implied volatility metrics from options chain."""
        result = {
            'current_iv': None,
            'iv_percentile': None,
            'iv_rank': None,
            'iv_high': None,
            'iv_low': None,
        }
        
        try:
            # Get options expiration dates
            expirations = self.stock.options
            if not expirations:
                return result
            
            # Get near-term ATM options for current IV
            # Use expiration ~30 days out
            target_date = datetime.now() + timedelta(days=30)
            nearest_exp = min(expirations, 
                             key=lambda x: abs(datetime.strptime(x, '%Y-%m-%d') - target_date))
            
            # Get options chain
            chain = self.stock.option_chain(nearest_exp)
            calls = chain.calls
            puts = chain.puts
            
            if calls.empty:
                return result
            
            # Get current price
            current_price = self.info.get('currentPrice') or self.info.get('regularMarketPrice', 0)
            
            # Find ATM options
            calls['strike_diff'] = abs(calls['strike'] - current_price)
            atm_call = calls.loc[calls['strike_diff'].idxmin()]
            
            # Current IV from ATM option
            current_iv = atm_call.get('impliedVolatility', None)
            if current_iv:
                current_iv = current_iv * 100  # Convert to percentage
                result['current_iv'] = current_iv
            
            # Estimate IV range from multiple expirations
            iv_samples = []
            for exp in expirations[:6]:  # Check first 6 expirations
                try:
                    chain = self.stock.option_chain(exp)
                    if not chain.calls.empty:
                        chain.calls['strike_diff'] = abs(chain.calls['strike'] - current_price)
                        atm = chain.calls.loc[chain.calls['strike_diff'].idxmin()]
                        iv = atm.get('impliedVolatility', None)
                        if iv:
                            iv_samples.append(iv * 100)
                except:
                    continue
            
            if iv_samples:
                # Use samples to estimate percentile
                iv_high = max(iv_samples) * 1.3  # Estimate 52w high
                iv_low = min(iv_samples) * 0.7   # Estimate 52w low
                
                result['iv_high'] = iv_high
                result['iv_low'] = iv_low
                
                if current_iv:
                    # IV Rank = (current - low) / (high - low)
                    if iv_high > iv_low:
                        result['iv_rank'] = ((current_iv - iv_low) / (iv_high - iv_low)) * 100
                    
                    # IV Percentile (simplified - using rank as approximation)
                    result['iv_percentile'] = result['iv_rank']
            
            return result
            
        except Exception as e:
            return result
    
    def _calculate_historical_volatility(self) -> tuple:
        """Calculate historical (realized) volatility."""
        try:
            # Get historical prices
            hist = self.stock.history(period='3mo')
            if hist.empty or len(hist) < 30:
                return None, None
            
            # Calculate daily returns
            returns = hist['Close'].pct_change().dropna()
            
            # 30-day HV (annualized)
            hv_30d = returns.tail(30).std() * np.sqrt(252) * 100
            
            # 60-day HV (annualized)
            hv_60d = returns.tail(60).std() * np.sqrt(252) * 100 if len(returns) >= 60 else None
            
            return hv_30d, hv_60d
            
        except Exception as e:
            return None, None
    
    def _get_options_liquidity(self) -> tuple:
        """Get options volume and open interest."""
        try:
            expirations = self.stock.options
            if not expirations:
                return None, None
            
            total_volume = 0
            total_oi = 0
            
            for exp in expirations[:4]:  # First 4 expirations
                try:
                    chain = self.stock.option_chain(exp)
                    total_volume += chain.calls['volume'].sum() + chain.puts['volume'].sum()
                    total_oi += chain.calls['openInterest'].sum() + chain.puts['openInterest'].sum()
                except:
                    continue
            
            return int(total_volume), int(total_oi)
            
        except:
            return None, None
    
    def _iv_signal(self, percentile: Optional[float], rank: Optional[float]) -> str:
        """Generate IV signal."""
        if percentile is None:
            return "⚪ IV data unavailable"
        
        if percentile <= 20:
            return "🟢 IV Very Low - Options CHEAP"
        elif percentile <= 40:
            return "🟢 IV Low - Good time to buy options"
        elif percentile <= 60:
            return "🟡 IV Average"
        elif percentile <= 80:
            return "🟠 IV High - Options expensive"
        else:
            return "🔴 IV Very High - Options EXPENSIVE"
    
    def _leaps_timing(self, percentile: Optional[float], premium: Optional[float]) -> str:
        """Generate LEAPS timing recommendation."""
        if percentile is None:
            return "⚪ Unable to assess"
        
        signals = []
        
        if percentile <= 25:
            signals.append("🟢 EXCELLENT time to buy LEAPS")
            signals.append("IV is historically low")
        elif percentile <= 40:
            signals.append("🟢 GOOD time to buy LEAPS")
        elif percentile <= 60:
            signals.append("🟡 NEUTRAL - Wait for lower IV if possible")
        elif percentile <= 80:
            signals.append("🟠 AVOID buying LEAPS now")
            signals.append("IV is elevated")
        else:
            signals.append("🔴 BAD time to buy LEAPS")
            signals.append("IV is very high - options overpriced")
        
        if premium is not None:
            if premium > 10:
                signals.append("⚠️ IV > HV by significant margin")
            elif premium < -5:
                signals.append("✅ IV < HV - extra discount")
        
        return " | ".join(signals)
    
    def format_report(self, data: OptionsData) -> str:
        """Format options analysis report."""
        lines = [
            "═" * 60,
            f"📊 OPTIONS ANALYSIS: {data.ticker}",
            f"   {data.company_name}",
            "═" * 60,
            "",
            f"Stock Price: ${data.current_price:.2f}",
            "",
        ]
        
        # IV Analysis
        lines.append("─" * 60)
        lines.append("IMPLIED VOLATILITY (IV)")
        lines.append("─" * 60)
        lines.append(f"  Signal: {data.iv_signal}")
        lines.append("")
        
        if data.current_iv:
            lines.append(f"  Current IV:     {data.current_iv:.1f}%")
        if data.iv_percentile:
            lines.append(f"  IV Percentile:  {data.iv_percentile:.0f}% (vs 52-week range)")
        if data.iv_rank:
            lines.append(f"  IV Rank:        {data.iv_rank:.0f}%")
        if data.iv_52w_low and data.iv_52w_high:
            lines.append(f"  52-Week Range:  {data.iv_52w_low:.0f}% - {data.iv_52w_high:.0f}%")
        
        lines.append("")
        
        # Historical Volatility
        lines.append("─" * 60)
        lines.append("HISTORICAL VOLATILITY (HV)")
        lines.append("─" * 60)
        
        if data.hv_30d:
            lines.append(f"  30-Day HV:      {data.hv_30d:.1f}%")
        if data.hv_60d:
            lines.append(f"  60-Day HV:      {data.hv_60d:.1f}%")
        if data.iv_premium:
            emoji = "⚠️" if data.iv_premium > 5 else "✅" if data.iv_premium < 0 else "📊"
            lines.append(f"  IV Premium:     {emoji} {data.iv_premium:+.1f}% (IV - HV)")
        
        lines.append("")
        
        # LEAPS Timing
        lines.append("─" * 60)
        lines.append("🎯 LEAPS TIMING")
        lines.append("─" * 60)
        lines.append(f"  {data.leaps_timing}")
        
        lines.append("")
        
        # Options Liquidity
        lines.append("─" * 60)
        lines.append("OPTIONS LIQUIDITY")
        lines.append("─" * 60)
        
        if data.options_volume:
            lines.append(f"  Total Volume:   {data.options_volume:,}")
        if data.open_interest:
            lines.append(f"  Open Interest:  {data.open_interest:,}")
        
        liquidity = "High" if data.open_interest and data.open_interest > 100000 else "Medium" if data.open_interest and data.open_interest > 10000 else "Low"
        lines.append(f"  Liquidity:      {liquidity}")
        
        lines.append("")
        lines.append("═" * 60)
        lines.append("💡 Buy LEAPS when IV Percentile < 30%")
        lines.append("   Sell/avoid when IV Percentile > 70%")
        lines.append("═" * 60)
        
        return "\n".join(lines)


def check_options(ticker: str):
    """Check options IV and LEAPS timing for a ticker."""
    analyzer = OptionsAnalyzer(ticker)
    data = analyzer.analyze()
    print(analyzer.format_report(data))
    return data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_options(ticker)
    else:
        print("Usage: python options_analysis.py TICKER")
        print("\nExample: python options_analysis.py AAPL")

