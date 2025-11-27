#!/usr/bin/env python3
"""
Alert System
============

Send notifications via Telegram (FREE), Email (SendGrid), or SMS (Twilio) when:
- Market regime changes (GREEN → YELLOW → RED)
- Whale activity detected (ACCUMULATION / DISTRIBUTION)
- High-conviction trade setups identified

Setup (Telegram - RECOMMENDED, FREE):
    1. Message @BotFather on Telegram, create bot, get token
    2. Message your bot, then visit: https://api.telegram.org/bot<TOKEN>/getUpdates
    3. Find your chat_id in the response
    4. Set environment variables:
       export TELEGRAM_BOT_TOKEN="your_bot_token"
       export TELEGRAM_CHAT_ID="your_chat_id"

Setup (Email - SendGrid):
    export SENDGRID_API_KEY="your_key"
    export ALERT_EMAIL="you@email.com"

Setup (SMS - Twilio):
    export TWILIO_ACCOUNT_SID="your_sid"
    export TWILIO_AUTH_TOKEN="your_token"
    export TWILIO_FROM_NUMBER="+1234567890"
    export ALERT_PHONE="+1234567890"

Free Tiers:
    - Telegram: Unlimited, FREE forever
    - SendGrid: 100 emails/day free forever
    - Twilio: $15 credit to start (SMS ~$0.0075 each)
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class AlertType(Enum):
    REGIME_CHANGE = "regime_change"
    WHALE_ACTIVITY = "whale_activity"
    TRADE_SETUP = "trade_setup"
    DAILY_BRIEFING = "daily_briefing"
    PRICE_ALERT = "price_alert"


class AlertPriority(Enum):
    LOW = 1      # Email only
    MEDIUM = 2   # Email
    HIGH = 3     # Email + SMS
    CRITICAL = 4 # Email + SMS immediately


@dataclass
class Alert:
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    data: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AlertManager:
    """
    Manages alert routing and delivery.
    Supports Telegram (FREE), Email (SendGrid), and SMS (Twilio).
    """
    
    def __init__(self):
        # Telegram (FREE - Recommended)
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        # Email (SendGrid)
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        self.alert_email = os.environ.get('ALERT_EMAIL')
        
        # SMS (Twilio)
        self.twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.twilio_from = os.environ.get('TWILIO_FROM_NUMBER')
        self.alert_phone = os.environ.get('ALERT_PHONE')
        
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.email_enabled = bool(self.sendgrid_key and self.alert_email)
        self.sms_enabled = bool(self.twilio_sid and self.twilio_token and self.alert_phone)
        
        # Alert history (in-memory, cleared on restart)
        self.history: List[Alert] = []
        
        # Deduplication window (don't send same alert twice in X minutes)
        self.dedup_window_minutes = 60
        self._recent_alerts: Dict[str, datetime] = {}
    
    def send(self, alert: Alert) -> bool:
        """
        Send an alert via appropriate channels based on priority.
        Returns True if at least one channel succeeded.
        """
        # Deduplication check
        alert_key = f"{alert.type.value}:{alert.title}"
        if alert_key in self._recent_alerts:
            last_sent = self._recent_alerts[alert_key]
            minutes_ago = (datetime.now() - last_sent).total_seconds() / 60
            if minutes_ago < self.dedup_window_minutes:
                print(f"  [Alert] Skipping duplicate: {alert.title} (sent {minutes_ago:.0f}m ago)")
                return False
        
        self.history.append(alert)
        self._recent_alerts[alert_key] = datetime.now()
        
        success = False
        
        # Telegram for all priorities (FREE, fast)
        if self.telegram_enabled:
            if self._send_telegram(alert):
                success = True
        
        # Email for all priorities
        if self.email_enabled:
            if self._send_email(alert):
                success = True
        
        # SMS for HIGH and CRITICAL only
        if alert.priority.value >= AlertPriority.HIGH.value and self.sms_enabled:
            if self._send_sms(alert):
                success = True
        
        # Fallback: Print to console if no channels configured
        if not self.telegram_enabled and not self.email_enabled and not self.sms_enabled:
            self._print_alert(alert)
            success = True
        
        return success
    
    def _send_telegram(self, alert: Alert) -> bool:
        """Send alert via Telegram bot (FREE)."""
        try:
            import urllib.request
            import urllib.parse
            
            # Format message (plain text to avoid markdown issues)
            priority_emoji = {
                AlertPriority.LOW: "📋",
                AlertPriority.MEDIUM: "📢",
                AlertPriority.HIGH: "🚨",
                AlertPriority.CRITICAL: "🔴"
            }
            
            emoji = priority_emoji.get(alert.priority, "📋")
            
            # Build message (plain text)
            lines = [
                f"{emoji} {alert.title}",
                f"[{alert.type.value.upper()}]",
                "",
                alert.message,
                "",
                "Details:"
            ]
            
            for key, value in alert.data.items():
                lines.append(f"  • {key}: {value}")
            
            lines.append(f"\n{alert.timestamp.strftime('%H:%M:%S')}")
            
            text = "\n".join(lines)
            
            # Send via Telegram API (no parse_mode for safety)
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id': self.telegram_chat_id,
                'text': text
            }).encode()
            
            req = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(req, timeout=10)
            result = json.loads(response.read().decode())
            
            if result.get('ok'):
                print(f"  [Telegram] Sent: {alert.title}")
                return True
            else:
                print(f"  [Telegram] Failed: {result.get('description', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"  [Telegram] Error: {e}")
            return False
    
    def _send_email(self, alert: Alert) -> bool:
        """Send email via SendGrid."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_key)
            
            # Format HTML body
            html_content = self._format_email_html(alert)
            
            message = Mail(
                from_email=Email("alerts@tradinglab.local", "Trading Lab"),
                to_emails=To(self.alert_email),
                subject=f"[{alert.priority.name}] {alert.title}",
                html_content=Content("text/html", html_content)
            )
            
            response = sg.send(message)
            print(f"  [Email] Sent: {alert.title} (Status: {response.status_code})")
            return response.status_code in [200, 201, 202]
            
        except ImportError:
            print("  [Email] SendGrid not installed. Run: pip install sendgrid")
            return False
        except Exception as e:
            print(f"  [Email] Failed: {e}")
            return False
    
    def _send_sms(self, alert: Alert) -> bool:
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_sid, self.twilio_token)
            
            # Short message for SMS
            body = f"{alert.title}\n{alert.message[:140]}"
            
            message = client.messages.create(
                body=body,
                from_=self.twilio_from,
                to=self.alert_phone
            )
            
            print(f"  [SMS] Sent: {alert.title} (SID: {message.sid})")
            return True
            
        except ImportError:
            print("  [SMS] Twilio not installed. Run: pip install twilio")
            return False
        except Exception as e:
            print(f"  [SMS] Failed: {e}")
            return False
    
    def _format_email_html(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        data_rows = ""
        for key, value in alert.data.items():
            data_rows += f"<tr><td style='padding:5px;font-weight:bold;'>{key}</td><td style='padding:5px;'>{value}</td></tr>"
        
        priority_colors = {
            AlertPriority.LOW: "#6c757d",
            AlertPriority.MEDIUM: "#ffc107",
            AlertPriority.HIGH: "#fd7e14",
            AlertPriority.CRITICAL: "#dc3545"
        }
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background: {priority_colors[alert.priority]}; color: white; padding: 10px 20px; border-radius: 5px;">
                <h2 style="margin: 0;">{alert.title}</h2>
                <small>{alert.type.value.upper()} | {alert.timestamp.strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            <div style="padding: 20px; background: #f8f9fa; margin-top: 10px; border-radius: 5px;">
                <p style="font-size: 16px;">{alert.message}</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    {data_rows}
                </table>
            </div>
            <p style="color: #6c757d; font-size: 12px; margin-top: 20px;">
                Trading Lab Alert System | Do your own due diligence
            </p>
        </body>
        </html>
        """
    
    def _print_alert(self, alert: Alert):
        """Print alert to console (fallback)."""
        print(f"\n{'='*60}")
        print(f"ALERT [{alert.priority.name}]: {alert.title}")
        print(f"Type: {alert.type.value}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        print(alert.message)
        print("-"*60)
        for k, v in alert.data.items():
            print(f"  {k}: {v}")
        print("="*60 + "\n")
    
    # Convenience methods for common alerts
    
    def regime_change(self, old_regime: str, new_regime: str, score: float):
        """Alert on market regime transition."""
        priority = AlertPriority.HIGH if new_regime == "RED" else AlertPriority.MEDIUM
        
        alert = Alert(
            type=AlertType.REGIME_CHANGE,
            priority=priority,
            title=f"Market Regime: {old_regime} → {new_regime}",
            message=f"The market regime has changed from {old_regime} to {new_regime}. "
                    f"Adjust your trading approach accordingly.",
            data={
                "Previous Regime": old_regime,
                "New Regime": new_regime,
                "Regime Score": f"{score:.1f}/100",
                "Action": "Reduce exposure" if new_regime == "RED" else "Normal trading"
            }
        )
        return self.send(alert)
    
    def whale_detected(self, ticker: str, status: str, confidence: str, details: str):
        """Alert on whale/institutional activity."""
        priority = AlertPriority.HIGH if status in ["ACCUMULATION", "DISTRIBUTION"] else AlertPriority.LOW
        
        alert = Alert(
            type=AlertType.WHALE_ACTIVITY,
            priority=priority,
            title=f"Whale Alert: {ticker} - {status}",
            message=f"Unusual institutional activity detected in {ticker}. {details}",
            data={
                "Ticker": ticker,
                "Signal": status,
                "Confidence": confidence,
                "Details": details
            }
        )
        return self.send(alert)
    
    def trade_setup(self, ticker: str, strategy: str, entry: float, stop: float, target: float, score: int):
        """Alert on high-conviction trade setup."""
        if score < 70:
            return False  # Don't alert on weak setups
        
        priority = AlertPriority.HIGH if score >= 85 else AlertPriority.MEDIUM
        risk_reward = abs(target - entry) / abs(entry - stop) if entry != stop else 0
        
        alert = Alert(
            type=AlertType.TRADE_SETUP,
            priority=priority,
            title=f"Trade Setup: {ticker} ({strategy})",
            message=f"High-conviction {strategy} setup identified for {ticker} with {score}/100 score.",
            data={
                "Ticker": ticker,
                "Strategy": strategy,
                "Entry": f"${entry:.2f}",
                "Stop": f"${stop:.2f}",
                "Target": f"${target:.2f}",
                "R:R": f"{risk_reward:.1f}:1",
                "Score": f"{score}/100"
            }
        )
        return self.send(alert)
    
    def daily_summary(self, regime: str, top_picks: List[Dict], alerts_count: int):
        """Send daily briefing summary."""
        picks_text = "\n".join([f"• {p['ticker']}: {p['action']} ({p['reason']})" for p in top_picks[:5]])
        
        alert = Alert(
            type=AlertType.DAILY_BRIEFING,
            priority=AlertPriority.LOW,
            title=f"Daily Briefing - {datetime.now().strftime('%b %d')}",
            message=f"Market Regime: {regime}\n\nTop Opportunities:\n{picks_text}",
            data={
                "Regime": regime,
                "Alerts Today": alerts_count,
                "Top Picks": len(top_picks)
            }
        )
        return self.send(alert)


# Singleton instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get or create the global AlertManager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


if __name__ == "__main__":
    # Test alerts
    manager = AlertManager()
    
    print("="*50)
    print("ALERT SYSTEM STATUS")
    print("="*50)
    print(f"  Telegram Enabled: {manager.telegram_enabled} {'(FREE!)' if manager.telegram_enabled else ''}")
    print(f"  Email Enabled: {manager.email_enabled}")
    print(f"  SMS Enabled: {manager.sms_enabled}")
    
    if not any([manager.telegram_enabled, manager.email_enabled, manager.sms_enabled]):
        print("\n  No alert channels configured. Alerts will print to console.")
        print("\n  To enable Telegram (FREE):")
        print("    1. Message @BotFather on Telegram")
        print("    2. Create a bot and get the token")
        print("    3. Message your bot, then visit:")
        print("       https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("    4. Find your chat_id in the response")
        print("    5. Set environment variables:")
        print("       export TELEGRAM_BOT_TOKEN='your_token'")
        print("       export TELEGRAM_CHAT_ID='your_chat_id'")
    
    print("\n" + "="*50)
    print("TESTING ALERTS (Console Output)")
    print("="*50)
    
    # Test regime change
    manager.regime_change("GREEN", "YELLOW", 45.0)
    
    # Test whale alert
    manager.whale_detected("NVDA", "ACCUMULATION", "HIGH", "5x volume spike at VWAP")
    
    # Test trade setup
    manager.trade_setup("AAPL", "Gap & Go", 180.50, 178.00, 185.00, 82)

