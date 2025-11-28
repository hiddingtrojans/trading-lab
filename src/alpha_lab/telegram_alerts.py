#!/usr/bin/env python3
"""
Unified Telegram Alert System
=============================

Single module for all Telegram notifications:
- Trade signals
- Options flow alerts
- Position alerts (stop/target hit)
- Regime changes
- EOD summaries

All alerts go through here for consistent formatting.

Usage:
    from alpha_lab.telegram_alerts import TelegramAlerter, AlertType
    
    alerter = TelegramAlerter()
    alerter.send_signal_alert(signals)
    alerter.send_position_alert(ticker, alert_type, details)
"""

import os
import urllib.request
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass


class AlertType(Enum):
    """Types of alerts."""
    SIGNAL = "signal"           # Trade signals
    OPTIONS_FLOW = "flow"       # Unusual options activity
    POSITION_STOP = "stop"      # Position hit stop
    POSITION_TARGET = "target"  # Position hit target
    POSITION_WARN = "warn"      # Position near stop/target
    REGIME_CHANGE = "regime"    # Market regime changed
    EOD_SUMMARY = "eod"         # End of day summary
    PERFORMANCE = "perf"        # Performance report


@dataclass
class Alert:
    """Alert data structure."""
    alert_type: AlertType
    title: str
    body: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TelegramAlerter:
    """Unified Telegram alerting system."""
    
    def __init__(self, token: str = None, chat_id: str = None):
        """
        Initialize alerter.
        
        Args:
            token: Bot token (defaults to env var)
            chat_id: Chat ID (defaults to env var)
        """
        self.token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
        
        # Load from config file if not in env
        if not self.token or not self.chat_id:
            self._load_from_config()
    
    def _load_from_config(self):
        """Load credentials from config file."""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '../../configs/telegram.env'
        )
        if os.path.exists(config_path):
            with open(config_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        if line.startswith('export '):
                            line = line[7:]
                        key, value = line.split('=', 1)
                        value = value.strip('"').strip("'")
                        if key == 'TELEGRAM_BOT_TOKEN':
                            self.token = value
                        elif key == 'TELEGRAM_CHAT_ID':
                            self.chat_id = value
    
    def is_configured(self) -> bool:
        """Check if Telegram is configured."""
        return bool(self.token and self.chat_id)
    
    def send(self, message: str, silent: bool = False) -> bool:
        """
        Send message to Telegram.
        
        Args:
            message: Message text
            silent: If True, send without notification sound
        
        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False
        
        try:
            url = f'https://api.telegram.org/bot{self.token}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'disable_notification': silent
            }
            encoded = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(url, data=encoded)
            urllib.request.urlopen(req, timeout=30)
            return True
        except Exception as e:
            print(f"Failed to send Telegram: {e}")
            return False
    
    def send_alert(self, alert: Alert) -> bool:
        """Send formatted alert."""
        # Format based on priority
        if alert.priority == 1:
            prefix = "🚨"
        elif alert.priority == 2:
            prefix = "⚡"
        else:
            prefix = "📋"
        
        message = f"{prefix} {alert.title}\n"
        message += f"{'=' * 30}\n"
        message += alert.body
        message += f"\n\n{alert.timestamp.strftime('%H:%M:%S')}"
        
        return self.send(message, silent=(alert.priority == 3))
    
    # ==================== SIGNAL ALERTS ====================
    
    def send_signal_alert(self, signals: List[Dict], regime: Dict = None) -> bool:
        """
        Send trade signals alert.
        
        Args:
            signals: List of signal dicts from TradeScanner
            regime: Market regime info
        """
        if not signals and not regime:
            return False
        
        lines = []
        
        # Regime header
        if regime:
            emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}.get(regime.get('status'), '⚪')
            lines.append(f"{emoji} {regime.get('status', 'UNKNOWN')} | SPY ${regime.get('spy_price', 0):.2f}")
            lines.append(f"{regime.get('action', '')}")
            lines.append("")
        
        # Signals
        if not signals:
            lines.append("No clean setups today.")
            lines.append("Cash is a position.")
        else:
            for s in signals:
                grade = s.get('grade', 'C')
                lines.append(f"[{grade}] {s['action']}: {s.get('name', s['ticker'])} ({s['ticker']})")
                lines.append(f"${s['price']} | 5D: {s.get('mom_5d', 0):+.1f}%")
                lines.append(f"Entry ${s['entry']} | Stop ${s['stop']} | Target ${s['target']}")
                lines.append(f"R:R 1:{s['rr_ratio']} | {s['shares']} sh (${s.get('risk_amount', 0):.0f} risk)")
                lines.append(f"{s['reason']}")
                if s.get('earnings_warning'):
                    lines.append(f"⚠️ {s['earnings_warning']}")
                lines.append("")
        
        alert = Alert(
            alert_type=AlertType.SIGNAL,
            title="TRADE SIGNALS",
            body="\n".join(lines),
            priority=1 if signals else 3
        )
        
        return self.send_alert(alert)
    
    # ==================== OPTIONS FLOW ALERTS ====================
    
    def send_flow_alert(self, flows: List) -> bool:
        """
        Send options flow alert.
        
        Args:
            flows: List of FlowAlert objects
        """
        if not flows:
            return False
        
        lines = []
        
        for flow in flows[:5]:  # Limit to 5
            emoji = "C" if flow.option_type == "CALL" else "P"
            lines.append(f"{flow.alert_type}")
            lines.append(f"{flow.ticker} ${flow.strike}{emoji} {flow.expiry[:6]}")
            lines.append(f"Premium: ${flow.premium:,.0f}")
            lines.append(f"Vol/OI: {flow.vol_oi_ratio:.1f}x | {flow.otm_pct:+.1f}% OTM")
            lines.append("")
        
        alert = Alert(
            alert_type=AlertType.OPTIONS_FLOW,
            title="OPTIONS FLOW",
            body="\n".join(lines),
            priority=1
        )
        
        return self.send_alert(alert)
    
    # ==================== POSITION ALERTS ====================
    
    def send_position_alert(self, ticker: str, alert_type: str, 
                           entry: float, current: float, 
                           stop: float = None, target: float = None,
                           pnl_pct: float = None) -> bool:
        """
        Send position alert (stop hit, target hit, warning).
        
        Args:
            ticker: Stock symbol
            alert_type: 'STOP_HIT', 'TARGET_HIT', 'NEAR_STOP', 'NEAR_TARGET'
            entry: Entry price
            current: Current price
            stop: Stop price
            target: Target price
            pnl_pct: P&L percentage
        """
        lines = []
        
        if alert_type == 'STOP_HIT':
            title = f"STOP HIT: {ticker}"
            lines.append(f"Entry: ${entry:.2f}")
            lines.append(f"Exit: ${current:.2f}")
            lines.append(f"P&L: {pnl_pct:+.1f}%")
            lines.append("")
            lines.append("Position closed at stop.")
            priority = 1
            
        elif alert_type == 'TARGET_HIT':
            title = f"TARGET HIT: {ticker}"
            lines.append(f"Entry: ${entry:.2f}")
            lines.append(f"Exit: ${current:.2f}")
            lines.append(f"P&L: {pnl_pct:+.1f}%")
            lines.append("")
            lines.append("Take profit!")
            priority = 1
            
        elif alert_type == 'NEAR_STOP':
            title = f"NEAR STOP: {ticker}"
            lines.append(f"Current: ${current:.2f}")
            lines.append(f"Stop: ${stop:.2f}")
            lines.append(f"Distance: {((current - stop) / current * 100):.1f}%")
            priority = 2
            
        elif alert_type == 'NEAR_TARGET':
            title = f"NEAR TARGET: {ticker}"
            lines.append(f"Current: ${current:.2f}")
            lines.append(f"Target: ${target:.2f}")
            lines.append(f"Distance: {((target - current) / current * 100):.1f}%")
            priority = 2
        else:
            return False
        
        alert = Alert(
            alert_type=AlertType.POSITION_STOP if 'STOP' in alert_type else AlertType.POSITION_TARGET,
            title=title,
            body="\n".join(lines),
            priority=priority
        )
        
        return self.send_alert(alert)
    
    # ==================== REGIME ALERTS ====================
    
    def send_regime_change(self, old_regime: str, new_regime: str, 
                          details: Dict = None) -> bool:
        """
        Send regime change alert.
        
        Args:
            old_regime: Previous regime (GREEN/YELLOW/RED)
            new_regime: New regime
            details: Additional details
        """
        emoji_map = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}
        old_emoji = emoji_map.get(old_regime, '⚪')
        new_emoji = emoji_map.get(new_regime, '⚪')
        
        lines = []
        lines.append(f"{old_emoji} {old_regime} → {new_emoji} {new_regime}")
        lines.append("")
        
        if details:
            lines.append(f"SPY: ${details.get('spy_price', 0):.2f}")
            lines.append(f"VIX: {details.get('vix', 0):.1f}")
            lines.append(f"Breadth: {details.get('breadth', 0):.0f}%")
        
        lines.append("")
        
        if new_regime == 'RED':
            lines.append("ACTION: No new longs. Tighten stops.")
        elif new_regime == 'YELLOW':
            lines.append("ACTION: Reduce size. Be selective.")
        else:
            lines.append("ACTION: Full size OK.")
        
        alert = Alert(
            alert_type=AlertType.REGIME_CHANGE,
            title="REGIME CHANGE",
            body="\n".join(lines),
            priority=1
        )
        
        return self.send_alert(alert)
    
    # ==================== EOD SUMMARY ====================
    
    def send_eod_summary(self, positions: List[Dict], regime: Dict,
                        daily_pnl: float = None) -> bool:
        """
        Send end-of-day summary.
        
        Args:
            positions: List of open positions
            regime: Current regime
            daily_pnl: Today's P&L
        """
        lines = []
        
        # Regime status
        emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}.get(regime.get('status'), '⚪')
        lines.append(f"Regime: {emoji} {regime.get('status', 'UNKNOWN')}")
        lines.append("")
        
        # Daily P&L
        if daily_pnl is not None:
            pnl_emoji = "+" if daily_pnl >= 0 else ""
            lines.append(f"Daily P&L: {pnl_emoji}${daily_pnl:,.0f}")
            lines.append("")
        
        # Positions summary
        if positions:
            lines.append(f"Open Positions: {len(positions)}")
            total_unrealized = sum(p.get('unrealized_pnl', 0) for p in positions)
            lines.append(f"Unrealized: ${total_unrealized:+,.0f}")
            lines.append("")
            
            for p in positions:
                pnl = p.get('unrealized_pct', 0)
                emoji = "+" if pnl >= 0 else ""
                lines.append(f"  {p['ticker']}: {emoji}{pnl:.1f}%")
        else:
            lines.append("No open positions.")
        
        alert = Alert(
            alert_type=AlertType.EOD_SUMMARY,
            title="EOD SUMMARY",
            body="\n".join(lines),
            priority=3
        )
        
        return self.send_alert(alert)
    
    # ==================== PERFORMANCE REPORT ====================
    
    def send_performance_report(self, stats: Dict) -> bool:
        """
        Send weekly performance report.
        
        Args:
            stats: Performance statistics
        """
        lines = []
        
        lines.append(f"Signals: {stats.get('total', 0)}")
        lines.append(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
        lines.append(f"Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}")
        lines.append(f"Avg P&L: {stats.get('avg_pnl', 0):+.2f}%")
        lines.append("")
        
        if stats.get('recent'):
            lines.append("Recent:")
            for s in stats['recent'][:5]:
                emoji = "+" if s.get('pnl', 0) > 0 else "-"
                lines.append(f"  {emoji} {s['ticker']}: {s.get('pnl', 0):+.1f}%")
        
        alert = Alert(
            alert_type=AlertType.PERFORMANCE,
            title="SIGNAL PERFORMANCE",
            body="\n".join(lines),
            priority=3
        )
        
        return self.send_alert(alert)


# Singleton instance for easy import
_alerter = None

def get_alerter() -> TelegramAlerter:
    """Get singleton alerter instance."""
    global _alerter
    if _alerter is None:
        _alerter = TelegramAlerter()
    return _alerter


# Convenience functions
def send_signal(signals: List[Dict], regime: Dict = None) -> bool:
    return get_alerter().send_signal_alert(signals, regime)

def send_flow(flows: List) -> bool:
    return get_alerter().send_flow_alert(flows)

def send_position(ticker: str, alert_type: str, **kwargs) -> bool:
    return get_alerter().send_position_alert(ticker, alert_type, **kwargs)

def send_regime(old: str, new: str, details: Dict = None) -> bool:
    return get_alerter().send_regime_change(old, new, details)

def send_eod(positions: List[Dict], regime: Dict, daily_pnl: float = None) -> bool:
    return get_alerter().send_eod_summary(positions, regime, daily_pnl)

def send_message(msg: str) -> bool:
    return get_alerter().send(msg)


if __name__ == "__main__":
    alerter = TelegramAlerter()
    
    if alerter.is_configured():
        print("Telegram configured. Sending test message...")
        alerter.send("Test alert from Trading System")
        print("Sent!")
    else:
        print("Telegram not configured.")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("Or create configs/telegram.env file")

