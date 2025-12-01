"""
Signal Enricher - Add actionable context to raw scanner results.

Takes a basic mover (ticker, change%, volume) and enriches with:
- Technical levels (support/resistance from recent price action)
- Trade thesis (WHY is this moving)
- Suggested trade type (day trade, swing, LEAPS)
- Risk/reward levels
- News catalyst if available
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import numpy as np


def get_technical_levels(ticker: str) -> Dict:
    """
    Calculate support/resistance from recent price action.
    
    Uses:
    - Recent swing highs/lows
    - Volume-weighted average price (VWAP) levels
    - Moving average confluence
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='3mo')
        
        if len(hist) < 20:
            return {}
        
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        volume = hist['Volume']
        
        current_price = close.iloc[-1]
        
        # Moving averages
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma_20
        
        # Recent range
        recent_high = high.iloc[-20:].max()
        recent_low = low.iloc[-20:].min()
        
        # 52-week high/low
        week52_high = high.max()
        week52_low = low.min()
        
        # Find key support levels (recent lows with high volume)
        supports = []
        resistances = []
        
        # Look for swing points
        for i in range(5, len(hist) - 5):
            # Swing low (support)
            if low.iloc[i] == low.iloc[i-5:i+5].min():
                supports.append(low.iloc[i])
            # Swing high (resistance)
            if high.iloc[i] == high.iloc[i-5:i+5].max():
                resistances.append(high.iloc[i])
        
        # Get nearest levels
        supports = sorted([s for s in supports if s < current_price], reverse=True)
        resistances = sorted([r for r in resistances if r > current_price])
        
        support = supports[0] if supports else recent_low
        resistance = resistances[0] if resistances else recent_high
        
        # ATR for stop placement
        tr = np.maximum(
            high - low,
            np.maximum(
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            )
        )
        atr = tr.rolling(14).mean().iloc[-1]
        
        # Suggested stop (2 ATR below current)
        suggested_stop = round(current_price - (2 * atr), 2)
        
        # Suggested target (at nearest resistance or 3x risk)
        risk = current_price - suggested_stop
        suggested_target = round(min(resistance, current_price + (3 * risk)), 2)
        
        return {
            'current_price': round(current_price, 2),
            'sma_20': round(sma_20, 2),
            'sma_50': round(sma_50, 2),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'recent_high': round(recent_high, 2),
            'recent_low': round(recent_low, 2),
            'week52_high': round(week52_high, 2),
            'week52_low': round(week52_low, 2),
            'atr': round(atr, 2),
            'suggested_stop': suggested_stop,
            'suggested_target': suggested_target,
            'above_sma20': current_price > sma_20,
            'above_sma50': current_price > sma_50,
            'near_52w_high': current_price >= week52_high * 0.95,
            'near_52w_low': current_price <= week52_low * 1.05,
        }
    except Exception as e:
        return {'error': str(e)}


def determine_trade_type(
    change_pct: float,
    volume_ratio: float,
    levels: Dict,
    market_cap_b: float = None,
) -> str:
    """
    Suggest trade type based on characteristics.
    
    - day_trade: High volatility, high volume, quick scalp
    - swing: Trend continuation, hold 2-10 days
    - leaps: Quality company at good levels, hold months
    """
    # Day trade: High intraday move with volume spike
    if abs(change_pct) > 5 and volume_ratio > 3:
        return 'day_trade'
    
    # LEAPS: Quality stock (>$10B), above MAs, not extended
    if market_cap_b and market_cap_b > 10:
        if levels.get('above_sma20') and levels.get('above_sma50'):
            if not levels.get('near_52w_high'):
                return 'leaps'
    
    # Swing: Everything else with reasonable setup
    if levels.get('above_sma20') or abs(change_pct) > 3:
        return 'swing'
    
    return 'swing'  # Default


def generate_thesis(
    ticker: str,
    change_pct: float,
    volume_ratio: float,
    levels: Dict,
    catalyst: str = None,
) -> str:
    """
    Generate a concise thesis for WHY this trade.
    """
    parts = []
    
    # Direction
    direction = "up" if change_pct > 0 else "down"
    
    # Main thesis based on setup
    if abs(change_pct) > 10:
        parts.append(f"Massive {abs(change_pct):.0f}% move {direction}")
    elif abs(change_pct) > 5:
        parts.append(f"Strong {abs(change_pct):.0f}% move {direction}")
    else:
        parts.append(f"Moving {abs(change_pct):.1f}% {direction}")
    
    # Volume context
    if volume_ratio > 5:
        parts.append("on extreme volume")
    elif volume_ratio > 2:
        parts.append("on elevated volume")
    
    # Technical context
    if levels.get('near_52w_high'):
        parts.append("near 52w high (breakout potential)")
    elif levels.get('near_52w_low'):
        parts.append("near 52w low (bounce potential)")
    elif levels.get('above_sma20') and levels.get('above_sma50'):
        parts.append("above key MAs (trend intact)")
    elif not levels.get('above_sma20'):
        parts.append("below 20 SMA (pullback)")
    
    # Catalyst
    if catalyst:
        parts.append(f"| Catalyst: {catalyst}")
    
    return " ".join(parts)


def get_recent_news(ticker: str) -> Optional[str]:
    """Get most recent news headline as potential catalyst."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if news and len(news) > 0:
            # Get most recent headline
            latest = news[0]
            title = latest.get('title', '')
            
            # Check if it's from today
            pub_time = latest.get('providerPublishTime', 0)
            pub_date = datetime.fromtimestamp(pub_time)
            
            if (datetime.now() - pub_date).days < 2:
                return title[:100]  # Truncate
        
        return None
    except:
        return None


def enrich_signal(
    ticker: str,
    change_pct: float,
    volume_ratio: float = 1.0,
    market_cap_b: float = None,
    entry_price: float = None,
) -> Dict:
    """
    Fully enrich a signal with actionable details.
    
    Returns complete signal ready for DB and alert.
    """
    # Get technical levels
    levels = get_technical_levels(ticker)
    
    if 'error' in levels:
        return {'error': levels['error'], 'ticker': ticker}
    
    # Get catalyst
    catalyst = get_recent_news(ticker)
    
    # Determine trade type
    trade_type = determine_trade_type(
        change_pct,
        volume_ratio,
        levels,
        market_cap_b,
    )
    
    # Generate thesis
    thesis = generate_thesis(
        ticker,
        change_pct,
        volume_ratio,
        levels,
        catalyst,
    )
    
    # Use entry price or current
    price = entry_price or levels.get('current_price', 0)
    
    # Determine signal type
    if abs(change_pct) > 5 and volume_ratio > 2:
        signal_type = 'momentum'
    elif levels.get('near_52w_high'):
        signal_type = 'breakout'
    elif volume_ratio > 3:
        signal_type = 'volume_spike'
    else:
        signal_type = 'momentum'
    
    # Calculate risk/reward
    target = levels.get('suggested_target', price * 1.1)
    stop = levels.get('suggested_stop', price * 0.95)
    
    upside = target - price
    downside = price - stop
    risk_reward = round(upside / downside, 2) if downside > 0 else 0
    
    return {
        'ticker': ticker,
        'signal_type': signal_type,
        'trade_type': trade_type,
        'entry_price': price,
        'thesis': thesis,
        'catalyst': catalyst,
        'market_cap_b': market_cap_b,
        'volume_ratio': volume_ratio,
        'change_pct': change_pct,
        'support': levels.get('support'),
        'resistance': levels.get('resistance'),
        'target_price': target,
        'stop_loss': stop,
        'risk_reward': risk_reward,
        'sma_20': levels.get('sma_20'),
        'sma_50': levels.get('sma_50'),
        'atr': levels.get('atr'),
        'near_52w_high': levels.get('near_52w_high'),
        'above_sma20': levels.get('above_sma20'),
    }


def format_actionable_alert(enriched: Dict) -> str:
    """
    Format enriched signal as actionable Telegram alert.
    """
    ticker = enriched['ticker']
    trade_type = enriched.get('trade_type', 'swing').upper().replace('_', ' ')
    change = enriched.get('change_pct', 0)
    price = enriched.get('entry_price', 0)
    thesis = enriched.get('thesis', '')
    
    # Direction emoji
    direction = "📈" if change > 0 else "📉"
    
    # Trade type emoji
    type_emoji = {
        'DAY TRADE': '⚡',
        'SWING': '🔄',
        'LEAPS': '🎯',
    }.get(trade_type, '📊')
    
    # Format change
    change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
    
    lines = [
        f"{direction} **{ticker}** {change_str} @ ${price:.2f}",
        f"{type_emoji} {trade_type}",
        f"",
        f"💡 {thesis}",
    ]
    
    # Add levels if swing or LEAPS
    if enriched.get('trade_type') in ['swing', 'leaps']:
        target = enriched.get('target_price', 0)
        stop = enriched.get('stop_loss', 0)
        rr = enriched.get('risk_reward', 0)
        
        if target and stop:
            lines.append("")
            lines.append(f"🎯 Target: ${target:.2f}")
            lines.append(f"🛑 Stop: ${stop:.2f}")
            lines.append(f"⚖️ R/R: {rr:.1f}:1")
    
    # Add support/resistance
    support = enriched.get('support')
    resistance = enriched.get('resistance')
    if support and resistance:
        lines.append(f"📊 S: ${support:.2f} | R: ${resistance:.2f}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    print("Testing signal enricher...")
    
    enriched = enrich_signal(
        ticker="NVDA",
        change_pct=-3.5,
        volume_ratio=2.1,
        market_cap_b=3000,
    )
    
    print("\nEnriched signal:")
    for k, v in enriched.items():
        print(f"  {k}: {v}")
    
    print("\nFormatted alert:")
    print(format_actionable_alert(enriched))

