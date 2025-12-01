"""
Smart Research Alerts

Not trading noise. Research notifications:
- Price hits your buy/sell targets
- Earnings coming up for your watchlist
- New SEC filings (10-K, 10-Q, 8-K)
- Significant news on your stocks

Runs daily via cron and sends Telegram alerts.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.research.database import get_watchlist, get_price_alerts, get_research
from src.alpha_lab.telegram_alerts import send_message


def check_price_targets() -> List[Tuple[str, str, float, float]]:
    """Check if any watchlist stocks hit price targets."""
    alerts = get_price_alerts()
    triggered = []
    
    for stock in alerts:
        ticker = stock['ticker']
        try:
            info = yf.Ticker(ticker).info
            current = info.get('regularMarketPrice') or info.get('currentPrice', 0)
            
            if not current:
                continue
            
            buy_below = stock['buy_below']
            sell_above = stock['sell_above']
            
            if buy_below and current <= buy_below:
                triggered.append((ticker, 'buy', current, buy_below))
            elif sell_above and current >= sell_above:
                triggered.append((ticker, 'sell', current, sell_above))
                
        except:
            continue
    
    return triggered


def check_upcoming_earnings() -> List[Dict]:
    """Check for upcoming earnings in watchlist."""
    watchlist = get_watchlist()
    upcoming = []
    
    today = datetime.now().date()
    week_out = today + timedelta(days=7)
    
    for stock in watchlist:
        ticker = stock['ticker']
        try:
            info = yf.Ticker(ticker).info
            
            # Get earnings date
            earnings_ts = info.get('earningsTimestamp')
            if earnings_ts:
                earnings_date = datetime.fromtimestamp(earnings_ts).date()
                
                if today <= earnings_date <= week_out:
                    upcoming.append({
                        'ticker': ticker,
                        'name': stock['name'],
                        'date': earnings_date.strftime('%Y-%m-%d'),
                        'days_until': (earnings_date - today).days,
                    })
        except:
            continue
    
    # Sort by date
    upcoming.sort(key=lambda x: x['days_until'])
    return upcoming


def check_significant_moves() -> List[Dict]:
    """Check for significant price moves in watchlist."""
    watchlist = get_watchlist()
    moves = []
    
    for stock in watchlist:
        ticker = stock['ticker']
        try:
            info = yf.Ticker(ticker).info
            
            change_pct = info.get('regularMarketChangePercent', 0)
            current = info.get('regularMarketPrice', 0)
            
            if abs(change_pct) >= 5:  # 5%+ move
                moves.append({
                    'ticker': ticker,
                    'name': stock['name'],
                    'change_pct': change_pct,
                    'price': current,
                    'thesis': stock.get('thesis', ''),
                })
        except:
            continue
    
    # Sort by absolute change
    moves.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    return moves


def format_research_alert(
    price_alerts: List[Tuple],
    earnings: List[Dict],
    moves: List[Dict],
) -> str:
    """Format research alerts for Telegram."""
    lines = [
        f"📬 RESEARCH ALERT - {datetime.now().strftime('%b %d')}",
        "",
    ]
    
    has_content = False
    
    # Price targets hit
    if price_alerts:
        has_content = True
        lines.append("━━━ 🎯 PRICE TARGETS HIT ━━━")
        for ticker, action, current, target in price_alerts:
            emoji = "🟢" if action == 'buy' else "🔴"
            research = get_research(ticker)
            thesis = research.get('thesis', '')[:40] if research else ''
            
            lines.append(f"{emoji} {ticker} hit {action.upper()} zone")
            lines.append(f"   ${current:.2f} (target: ${target:.2f})")
            if thesis:
                lines.append(f"   Your thesis: {thesis}...")
            lines.append("")
    
    # Upcoming earnings
    if earnings:
        has_content = True
        lines.append("━━━ 📅 EARNINGS THIS WEEK ━━━")
        for e in earnings[:5]:
            lines.append(f"• {e['ticker']} - {e['date']} ({e['days_until']}d)")
        lines.append("")
        lines.append("💡 Review your thesis before earnings!")
        lines.append("")
    
    # Significant moves
    if moves:
        has_content = True
        lines.append("━━━ 📈 BIG MOVES IN WATCHLIST ━━━")
        for m in moves[:5]:
            emoji = "📈" if m['change_pct'] > 0 else "📉"
            lines.append(f"{emoji} {m['ticker']} {m['change_pct']:+.1f}% @ ${m['price']:.2f}")
            if m['thesis']:
                lines.append(f"   Thesis: {m['thesis'][:40]}...")
        lines.append("")
    
    if not has_content:
        return None
    
    lines.append("─────────────────")
    lines.append("python deep_research.py TICKER")
    
    return "\n".join(lines)


def run_research_alerts(send_telegram: bool = True):
    """Run all research alert checks."""
    print("\n📬 Running Research Alerts...")
    
    # Check all conditions
    price_alerts = check_price_targets()
    earnings = check_upcoming_earnings()
    moves = check_significant_moves()
    
    print(f"   Price targets: {len(price_alerts)} triggered")
    print(f"   Upcoming earnings: {len(earnings)}")
    print(f"   Significant moves: {len(moves)}")
    
    # Format alert
    alert = format_research_alert(price_alerts, earnings, moves)
    
    if alert:
        print("\n" + alert)
        
        if send_telegram:
            success = send_message(alert)
            print("\n✅ Sent to Telegram" if success else "\n❌ Telegram failed")
    else:
        print("\n📭 No alerts to send")
    
    return {
        'price_alerts': price_alerts,
        'earnings': earnings,
        'moves': moves,
    }


def send_weekly_digest():
    """Send weekly research digest."""
    watchlist = get_watchlist()
    
    if not watchlist:
        return
    
    lines = [
        f"📊 WEEKLY RESEARCH DIGEST",
        f"   {datetime.now().strftime('%B %d, %Y')}",
        "",
        f"Tracking {len(watchlist)} stocks",
        "",
    ]
    
    # Group by status
    buying = [s for s in watchlist if s['status'] == 'buying']
    holding = [s for s in watchlist if s['status'] == 'holding']
    watching = [s for s in watchlist if s['status'] == 'watching']
    
    if buying:
        lines.append(f"🟢 BUYING ({len(buying)})")
        for s in buying:
            lines.append(f"   • {s['ticker']}")
        lines.append("")
    
    if holding:
        lines.append(f"📦 HOLDING ({len(holding)})")
        for s in holding:
            lines.append(f"   • {s['ticker']}")
        lines.append("")
    
    if watching:
        lines.append(f"👀 WATCHING ({len(watching)})")
        for s in watching[:10]:
            lines.append(f"   • {s['ticker']}")
        if len(watching) > 10:
            lines.append(f"   ... and {len(watching)-10} more")
        lines.append("")
    
    # Check targets
    price_alerts = check_price_targets()
    if price_alerts:
        lines.append("⚠️ TARGETS HIT:")
        for ticker, action, current, target in price_alerts:
            lines.append(f"   {ticker}: {action} at ${current:.2f}")
    
    lines.append("")
    lines.append("─────────────────")
    lines.append("python deep_research.py --alerts")
    
    alert = "\n".join(lines)
    print(alert)
    
    send_message(alert)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--weekly', action='store_true', help='Send weekly digest')
    parser.add_argument('--no-telegram', action='store_true')
    
    args = parser.parse_args()
    
    if args.weekly:
        send_weekly_digest()
    else:
        run_research_alerts(send_telegram=not args.no_telegram)

