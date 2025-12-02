"""
Technical Analysis Module

Relative Strength, Support/Resistance, Seasonality, 52-Week Distance

Why this matters:
- Relative strength shows momentum vs market
- Support/resistance = key decision zones
- Seasonality = historical timing patterns
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
import yfinance as yf
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@dataclass
class TechnicalData:
    """Technical analysis data."""
    ticker: str
    company_name: str
    current_price: float
    
    # Relative Strength
    rs_vs_spy_1m: Optional[float]  # 1-month relative strength
    rs_vs_spy_3m: Optional[float]
    rs_vs_spy_6m: Optional[float]
    rs_vs_spy_ytd: Optional[float]
    rs_signal: str
    
    # 52-Week Analysis
    high_52w: float
    low_52w: float
    pct_from_high: float
    pct_from_low: float
    position_signal: str
    
    # Support/Resistance
    support_levels: List[float]
    resistance_levels: List[float]
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    support_distance: Optional[float]
    resistance_distance: Optional[float]
    
    # Seasonality
    best_months: List[Tuple[str, float]]  # (month_name, avg_return)
    worst_months: List[Tuple[str, float]]
    current_month_historical: Optional[float]
    seasonality_signal: str
    
    # Moving Averages
    sma_50: float
    sma_200: float
    above_50: bool
    above_200: bool
    golden_cross: bool  # 50 > 200
    ma_signal: str


class TechnicalAnalyzer:
    """
    Technical analysis for stocks.
    """
    
    MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self.hist = None
        self.spy_hist = None
    
    def analyze(self) -> TechnicalData:
        """Run full technical analysis."""
        
        company_name = self.info.get('shortName', self.ticker)
        
        # Get historical data
        self.hist = self.stock.history(period='2y')
        self.spy_hist = yf.Ticker('SPY').history(period='2y')
        
        current_price = self.hist['Close'].iloc[-1] if not self.hist.empty else 0
        
        # Calculate all metrics
        rs_data = self._calculate_relative_strength()
        week_data = self._calculate_52_week()
        sr_data = self._calculate_support_resistance()
        seasonality = self._calculate_seasonality()
        ma_data = self._calculate_moving_averages()
        
        return TechnicalData(
            ticker=self.ticker,
            company_name=company_name,
            current_price=current_price,
            **rs_data,
            **week_data,
            **sr_data,
            **seasonality,
            **ma_data,
        )
    
    def _calculate_relative_strength(self) -> Dict:
        """Calculate relative strength vs SPY."""
        result = {
            'rs_vs_spy_1m': None,
            'rs_vs_spy_3m': None,
            'rs_vs_spy_6m': None,
            'rs_vs_spy_ytd': None,
            'rs_signal': "⚪ Unable to calculate",
        }
        
        try:
            if self.hist.empty or self.spy_hist.empty:
                return result
            
            # Calculate returns for different periods
            periods = {
                '1m': 21,
                '3m': 63,
                '6m': 126,
            }
            
            stock_current = self.hist['Close'].iloc[-1]
            spy_current = self.spy_hist['Close'].iloc[-1]
            
            for period_name, days in periods.items():
                if len(self.hist) > days and len(self.spy_hist) > days:
                    stock_past = self.hist['Close'].iloc[-days]
                    spy_past = self.spy_hist['Close'].iloc[-days]
                    
                    stock_return = (stock_current / stock_past - 1) * 100
                    spy_return = (spy_current / spy_past - 1) * 100
                    
                    result[f'rs_vs_spy_{period_name}'] = stock_return - spy_return
            
            # YTD
            try:
                year_start = datetime(datetime.now().year, 1, 1)
                stock_ytd_start = self.hist.loc[self.hist.index >= str(year_start)]['Close'].iloc[0]
                spy_ytd_start = self.spy_hist.loc[self.spy_hist.index >= str(year_start)]['Close'].iloc[0]
                
                stock_ytd = (stock_current / stock_ytd_start - 1) * 100
                spy_ytd = (spy_current / spy_ytd_start - 1) * 100
                result['rs_vs_spy_ytd'] = stock_ytd - spy_ytd
            except:
                pass
            
            # Generate signal
            rs_3m = result['rs_vs_spy_3m']
            if rs_3m:
                if rs_3m > 15:
                    result['rs_signal'] = "🟢 Strong Outperformer"
                elif rs_3m > 5:
                    result['rs_signal'] = "🟢 Outperforming SPY"
                elif rs_3m > -5:
                    result['rs_signal'] = "🟡 In Line with Market"
                elif rs_3m > -15:
                    result['rs_signal'] = "🟠 Underperforming SPY"
                else:
                    result['rs_signal'] = "🔴 Significant Laggard"
            
            return result
            
        except Exception as e:
            return result
    
    def _calculate_52_week(self) -> Dict:
        """Calculate 52-week high/low analysis."""
        result = {
            'high_52w': 0,
            'low_52w': 0,
            'pct_from_high': 0,
            'pct_from_low': 0,
            'position_signal': "⚪ Unknown",
        }
        
        try:
            if self.hist.empty:
                return result
            
            # Get 52-week data
            hist_52w = self.hist.tail(252)  # ~252 trading days
            
            high_52w = hist_52w['High'].max()
            low_52w = hist_52w['Low'].min()
            current = hist_52w['Close'].iloc[-1]
            
            result['high_52w'] = high_52w
            result['low_52w'] = low_52w
            result['pct_from_high'] = ((current / high_52w) - 1) * 100
            result['pct_from_low'] = ((current / low_52w) - 1) * 100
            
            # Position in range
            range_position = (current - low_52w) / (high_52w - low_52w) * 100
            
            if range_position >= 90:
                result['position_signal'] = "🔴 Near 52-Week HIGH"
            elif range_position >= 70:
                result['position_signal'] = "🟠 Upper Range"
            elif range_position >= 30:
                result['position_signal'] = "🟡 Mid Range"
            elif range_position >= 10:
                result['position_signal'] = "🟢 Lower Range (potential value)"
            else:
                result['position_signal'] = "🟢 Near 52-Week LOW"
            
            return result
            
        except Exception as e:
            return result
    
    def _calculate_support_resistance(self) -> Dict:
        """Calculate support and resistance levels."""
        result = {
            'support_levels': [],
            'resistance_levels': [],
            'nearest_support': None,
            'nearest_resistance': None,
            'support_distance': None,
            'resistance_distance': None,
        }
        
        try:
            if self.hist.empty or len(self.hist) < 50:
                return result
            
            current = self.hist['Close'].iloc[-1]
            
            # Simple approach: Use recent pivots
            highs = self.hist['High'].tail(100)
            lows = self.hist['Low'].tail(100)
            
            # Find local maxima and minima
            resistance_candidates = []
            support_candidates = []
            
            window = 5
            for i in range(window, len(highs) - window):
                # Local max
                if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
                    resistance_candidates.append(highs.iloc[i])
                # Local min
                if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
                    support_candidates.append(lows.iloc[i])
            
            # Also add round numbers near current price
            round_levels = []
            base = int(current / 10) * 10
            for i in range(-3, 4):
                round_levels.append(base + i * 10)
            
            # Combine and filter
            all_resistance = [r for r in resistance_candidates if r > current]
            all_support = [s for s in support_candidates if s < current]
            
            # Get unique levels (cluster nearby levels)
            result['resistance_levels'] = self._cluster_levels(all_resistance)[:3]
            result['support_levels'] = self._cluster_levels(all_support)[:3]
            
            # Nearest levels
            if result['resistance_levels']:
                result['nearest_resistance'] = min(result['resistance_levels'])
                result['resistance_distance'] = ((result['nearest_resistance'] / current) - 1) * 100
            
            if result['support_levels']:
                result['nearest_support'] = max(result['support_levels'])
                result['support_distance'] = ((result['nearest_support'] / current) - 1) * 100
            
            return result
            
        except Exception as e:
            return result
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """Cluster nearby price levels."""
        if not levels:
            return []
        
        levels = sorted(levels)
        clustered = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if (level - current_cluster[-1]) / current_cluster[-1] < threshold:
                current_cluster.append(level)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]
        
        clustered.append(sum(current_cluster) / len(current_cluster))
        return clustered
    
    def _calculate_seasonality(self) -> Dict:
        """Calculate monthly seasonality patterns."""
        result = {
            'best_months': [],
            'worst_months': [],
            'current_month_historical': None,
            'seasonality_signal': "⚪ Insufficient data",
        }
        
        try:
            if self.hist.empty or len(self.hist) < 252:
                return result
            
            # Calculate monthly returns
            monthly = self.hist['Close'].resample('ME').last().pct_change() * 100
            
            # Group by month
            monthly_avg = {}
            for date, ret in monthly.items():
                if pd.notna(ret):
                    month = date.month
                    if month not in monthly_avg:
                        monthly_avg[month] = []
                    monthly_avg[month].append(ret)
            
            # Calculate averages
            month_performance = []
            for month, returns in monthly_avg.items():
                if len(returns) >= 2:
                    avg = sum(returns) / len(returns)
                    month_performance.append((self.MONTH_NAMES[month-1], avg))
            
            # Sort by performance
            month_performance.sort(key=lambda x: x[1], reverse=True)
            
            result['best_months'] = month_performance[:3]
            result['worst_months'] = month_performance[-3:]
            
            # Current month
            current_month = datetime.now().month
            for name, avg in month_performance:
                if name == self.MONTH_NAMES[current_month-1]:
                    result['current_month_historical'] = avg
                    break
            
            # Signal
            if result['current_month_historical']:
                if result['current_month_historical'] > 2:
                    result['seasonality_signal'] = "🟢 Historically Strong Month"
                elif result['current_month_historical'] > 0:
                    result['seasonality_signal'] = "🟡 Historically Average Month"
                elif result['current_month_historical'] > -2:
                    result['seasonality_signal'] = "🟠 Historically Weak Month"
                else:
                    result['seasonality_signal'] = "🔴 Historically Poor Month"
            
            return result
            
        except Exception as e:
            return result
    
    def _calculate_moving_averages(self) -> Dict:
        """Calculate moving average analysis."""
        result = {
            'sma_50': 0,
            'sma_200': 0,
            'above_50': False,
            'above_200': False,
            'golden_cross': False,
            'ma_signal': "⚪ Insufficient data",
        }
        
        try:
            if self.hist.empty or len(self.hist) < 200:
                if len(self.hist) >= 50:
                    result['sma_50'] = self.hist['Close'].tail(50).mean()
                return result
            
            current = self.hist['Close'].iloc[-1]
            sma_50 = self.hist['Close'].tail(50).mean()
            sma_200 = self.hist['Close'].tail(200).mean()
            
            result['sma_50'] = sma_50
            result['sma_200'] = sma_200
            result['above_50'] = current > sma_50
            result['above_200'] = current > sma_200
            result['golden_cross'] = sma_50 > sma_200
            
            # Signal
            if result['above_50'] and result['above_200'] and result['golden_cross']:
                result['ma_signal'] = "🟢 Bullish (above both MAs, golden cross)"
            elif result['above_200']:
                result['ma_signal'] = "🟡 Neutral-Bullish (above 200 SMA)"
            elif result['above_50']:
                result['ma_signal'] = "🟠 Mixed (above 50, below 200)"
            else:
                result['ma_signal'] = "🔴 Bearish (below both MAs)"
            
            return result
            
        except Exception as e:
            return result
    
    def format_report(self, data: TechnicalData) -> str:
        """Format technical analysis report."""
        lines = [
            "═" * 60,
            f"📈 TECHNICAL ANALYSIS: {data.ticker}",
            f"   {data.company_name}",
            "═" * 60,
            "",
            f"Current Price: ${data.current_price:.2f}",
            "",
        ]
        
        # Relative Strength
        lines.append("─" * 60)
        lines.append("💪 RELATIVE STRENGTH vs SPY")
        lines.append("─" * 60)
        lines.append(f"  Signal: {data.rs_signal}")
        lines.append("")
        
        if data.rs_vs_spy_1m is not None:
            emoji = "📈" if data.rs_vs_spy_1m > 0 else "📉"
            lines.append(f"  1 Month:  {emoji} {data.rs_vs_spy_1m:+.1f}%")
        if data.rs_vs_spy_3m is not None:
            emoji = "📈" if data.rs_vs_spy_3m > 0 else "📉"
            lines.append(f"  3 Month:  {emoji} {data.rs_vs_spy_3m:+.1f}%")
        if data.rs_vs_spy_6m is not None:
            emoji = "📈" if data.rs_vs_spy_6m > 0 else "📉"
            lines.append(f"  6 Month:  {emoji} {data.rs_vs_spy_6m:+.1f}%")
        if data.rs_vs_spy_ytd is not None:
            emoji = "📈" if data.rs_vs_spy_ytd > 0 else "📉"
            lines.append(f"  YTD:      {emoji} {data.rs_vs_spy_ytd:+.1f}%")
        
        lines.append("")
        
        # 52-Week Range
        lines.append("─" * 60)
        lines.append("📊 52-WEEK RANGE")
        lines.append("─" * 60)
        lines.append(f"  Signal: {data.position_signal}")
        lines.append("")
        lines.append(f"  52-Week High: ${data.high_52w:.2f} ({data.pct_from_high:+.1f}%)")
        lines.append(f"  52-Week Low:  ${data.low_52w:.2f} ({data.pct_from_low:+.1f}%)")
        lines.append("")
        
        # Moving Averages
        lines.append("─" * 60)
        lines.append("📉 MOVING AVERAGES")
        lines.append("─" * 60)
        lines.append(f"  Signal: {data.ma_signal}")
        lines.append("")
        
        ma_50_emoji = "✅" if data.above_50 else "❌"
        ma_200_emoji = "✅" if data.above_200 else "❌"
        lines.append(f"  50 SMA:  ${data.sma_50:.2f} {ma_50_emoji}")
        lines.append(f"  200 SMA: ${data.sma_200:.2f} {ma_200_emoji}")
        lines.append(f"  Golden Cross: {'Yes ✅' if data.golden_cross else 'No ❌'}")
        lines.append("")
        
        # Support/Resistance
        lines.append("─" * 60)
        lines.append("🎯 SUPPORT & RESISTANCE")
        lines.append("─" * 60)
        
        if data.nearest_resistance:
            lines.append(f"  Next Resistance: ${data.nearest_resistance:.2f} ({data.resistance_distance:+.1f}%)")
        if data.nearest_support:
            lines.append(f"  Next Support:    ${data.nearest_support:.2f} ({data.support_distance:+.1f}%)")
        
        if data.resistance_levels:
            lines.append(f"  Key Resistance:  {', '.join([f'${r:.0f}' for r in data.resistance_levels])}")
        if data.support_levels:
            lines.append(f"  Key Support:     {', '.join([f'${s:.0f}' for s in data.support_levels])}")
        lines.append("")
        
        # Seasonality
        lines.append("─" * 60)
        lines.append("📅 SEASONALITY")
        lines.append("─" * 60)
        lines.append(f"  Signal: {data.seasonality_signal}")
        lines.append("")
        
        if data.current_month_historical is not None:
            current_month = self.MONTH_NAMES[datetime.now().month - 1]
            lines.append(f"  {current_month} Historical Avg: {data.current_month_historical:+.1f}%")
        
        if data.best_months:
            lines.append(f"  Best Months:  {', '.join([f'{m} ({r:+.1f}%)' for m, r in data.best_months])}")
        if data.worst_months:
            lines.append(f"  Worst Months: {', '.join([f'{m} ({r:+.1f}%)' for m, r in data.worst_months])}")
        
        lines.append("")
        lines.append("═" * 60)
        
        return "\n".join(lines)


def check_technicals(ticker: str):
    """Run technical analysis for a ticker."""
    analyzer = TechnicalAnalyzer(ticker)
    data = analyzer.analyze()
    print(analyzer.format_report(data))
    return data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        check_technicals(ticker)
    else:
        print("Usage: python technical_analysis.py TICKER")
        print("\nExample: python technical_analysis.py AAPL")

