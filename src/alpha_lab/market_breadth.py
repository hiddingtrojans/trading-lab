"""
Market Breadth Indicator
========================

Measures market health by checking what % of stocks are above their SMA50.

Rules:
- >60% above SMA50 = STRONG (full size longs)
- 40-60% = NEUTRAL (selective, smaller size)
- <40% = WEAK (avoid new longs)

Usage:
    from alpha_lab.market_breadth import get_market_breadth, is_market_healthy
    
    breadth = get_market_breadth()
    if is_market_healthy():
        # Take trades
"""

import yfinance as yf
from typing import Dict, Tuple
from alpha_lab.config import get_config


# Representative sample of S&P 500 for quick breadth check
BREADTH_SAMPLE = [
    # Tech (15)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'AMD',
    'ADBE', 'CSCO', 'INTC', 'QCOM', 'TXN',
    
    # Financials (10)
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'C', 'USB',
    
    # Healthcare (10)
    'UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'BMY', 'AMGN',
    
    # Consumer (10)
    'WMT', 'PG', 'KO', 'PEP', 'COST', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT',
    
    # Industrials (10)
    'CAT', 'HON', 'UPS', 'BA', 'GE', 'MMM', 'LMT', 'RTX', 'DE', 'UNP',
    
    # Energy (5)
    'XOM', 'CVX', 'COP', 'SLB', 'EOG',
]


def get_market_breadth(sample: list = None) -> Dict:
    """
    Calculate market breadth.
    
    Returns:
        Dict with breadth metrics
    """
    tickers = sample or BREADTH_SAMPLE
    
    above_sma50 = 0
    above_sma20 = 0
    total = 0
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3mo')
            
            if len(hist) < 50:
                continue
            
            price = hist['Close'].iloc[-1]
            sma50 = hist['Close'].rolling(50).mean().iloc[-1]
            sma20 = hist['Close'].rolling(20).mean().iloc[-1]
            
            total += 1
            if price > sma50:
                above_sma50 += 1
            if price > sma20:
                above_sma20 += 1
                
        except:
            continue
    
    if total == 0:
        return {'pct_above_sma50': 50, 'pct_above_sma20': 50, 'status': 'UNKNOWN', 'sample_size': 0}
    
    pct_50 = round(above_sma50 / total * 100, 1)
    pct_20 = round(above_sma20 / total * 100, 1)
    
    # Determine status
    if pct_50 >= 60:
        status = 'STRONG'
        action = 'Full size longs OK'
    elif pct_50 >= 40:
        status = 'NEUTRAL'
        action = 'Selective, smaller size'
    else:
        status = 'WEAK'
        action = 'Avoid new longs'
    
    return {
        'pct_above_sma50': pct_50,
        'pct_above_sma20': pct_20,
        'above_sma50': above_sma50,
        'above_sma20': above_sma20,
        'total': total,
        'status': status,
        'action': action,
    }


def is_market_healthy(min_breadth: float = None) -> Tuple[bool, str]:
    """
    Quick check if market breadth is healthy enough for new longs.
    
    Args:
        min_breadth: Minimum % above SMA50 (default from config)
    
    Returns:
        (is_healthy, reason)
    """
    threshold = min_breadth or get_config('regime.min_breadth', 40)
    
    breadth = get_market_breadth()
    pct = breadth['pct_above_sma50']
    
    if pct >= threshold:
        return True, f"Breadth OK: {pct}% above SMA50"
    else:
        return False, f"Breadth WEAK: Only {pct}% above SMA50 (<{threshold}%)"


def format_breadth_report() -> str:
    """Generate breadth report for display."""
    b = get_market_breadth()
    
    lines = []
    lines.append("=" * 40)
    lines.append("MARKET BREADTH REPORT")
    lines.append("=" * 40)
    lines.append(f"\nStatus: {b['status']}")
    lines.append(f"Action: {b['action']}")
    lines.append(f"\nStocks above SMA50: {b['pct_above_sma50']}% ({b['above_sma50']}/{b['total']})")
    lines.append(f"Stocks above SMA20: {b['pct_above_sma20']}% ({b['above_sma20']}/{b['total']})")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Calculating market breadth (this takes ~30 seconds)...")
    print(format_breadth_report())

