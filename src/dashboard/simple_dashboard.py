#!/usr/bin/env python3
"""
Simple Trading Dashboard - Unified Version
=======================================

A simplified but fully functional dashboard for the trading system.
Can run in two modes:
1. Live Bot Mode: Connects to a running trading bot instance
2. Analysis Viewer Mode: Displays latest results from unified_analyzer.py
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import pytz
import json
import os
import glob
import time as time_module
from datetime import time as dt_time
from typing import Dict, List, Optional
import logging

# Web dashboard dependencies
try:
    from flask import Flask, render_template_string, jsonify, request
    import threading
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    print("⚠️ Dashboard dependencies not installed. Run: pip install flask")

class SimpleTradingDashboard:
    """Simple but effective trading dashboard."""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.mode = 'LIVE' if bot_instance else 'VIEWER'
        self.trade_history = []
        self.performance_data = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
        self.latest_analysis = {}
        
    def update_trade_history(self, trade_data: Dict):
        """Update trade history with new trade."""
        trade_data['timestamp'] = datetime.now()
        self.trade_history.append(trade_data)
        
        # Update performance metrics
        pnl = trade_data.get('pnl', 0)
        self.performance_data['total_trades'] += 1
        self.performance_data['total_pnl'] += pnl
        
        if pnl > 0:
            self.performance_data['winning_trades'] += 1
        elif pnl < 0:
            self.performance_data['losing_trades'] += 1
            
        if self.performance_data['total_trades'] > 0:
            self.performance_data['win_rate'] = (
                self.performance_data['winning_trades'] / 
                self.performance_data['total_trades'] * 100
            )
    
    def update_live_pnl(self, symbol: str, pnl: float, current_price: float):
        """Update live P&L for a position."""
        # Update the position's live P&L
        if self.bot and symbol in self.bot.positions:
            self.bot.positions[symbol]['current_pnl'] = pnl
            self.bot.positions[symbol]['current_price'] = current_price
    
    def get_current_positions(self) -> List[Dict]:
        """Get current positions from bot."""
        if not self.bot:
            return []
        
        positions = []
        for symbol, position in self.bot.positions.items():
            current_pnl = position.get('current_pnl', 0)
            current_price = position.get('current_price', position['entry_price'])
            
            positions.append({
                'symbol': symbol,
                'shares': position['shares'],
                'entry_price': position['entry_price'],
                'current_price': current_price,
                'entry_time': position['entry_time'].isoformat(),
                'stop_price': position['stop_price'],
                'take_profit_price': position['take_profit_price'],
                'current_pnl': current_pnl,
                'pnl_pct': (current_pnl / (position['entry_price'] * position['shares']) * 100) if position['entry_price'] > 0 else 0
            })
        
        return positions

    def load_latest_analysis(self):
        """Load the most recent analysis JSON from data/output."""
        try:
            list_of_files = glob.glob('data/output/analysis_results_*.json') 
            if not list_of_files:
                return {}
            
            latest_file = max(list_of_files, key=os.path.getctime)
            with open(latest_file, 'r') as f:
                data = json.load(f)
                # If it's a list (batch analysis), wrapping it or taking first?
                # Unified analyzer outputs a list of results.
                return {'file': os.path.basename(latest_file), 'results': data}
        except Exception as e:
            print(f"Error loading analysis: {e}")
            return {}
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data."""
        current_positions = self.get_current_positions()
        self.latest_analysis = self.load_latest_analysis()
        
        # Calculate daily stats
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [t for t in self.trade_history 
                       if t['timestamp'].strftime('%Y-%m-%d') == today]
        
        daily_pnl = sum(t.get('pnl', 0) for t in today_trades)
        daily_trades = len(today_trades)
        
        # Market status with proper timezone handling
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        
        # Get today's market hours
        today_date = now.date()
        market_open = et_tz.localize(datetime.combine(today_date, dt_time(9, 30)))
        market_close = et_tz.localize(datetime.combine(today_date, dt_time(16, 0)))
        
        market_status = "CLOSED"
        if now.weekday() < 5:  # Weekday
            if market_open <= now <= market_close:
                market_status = "OPEN"
            elif now < market_open:
                market_status = "PRE-MARKET"
            elif now > market_close:
                market_status = "AFTER-HOURS"
        else:
            market_status = "WEEKEND"
        
        # Calculate time until market open/close
        time_until_open = ""
        time_until_close = ""
        
        if now.weekday() < 5:  # Weekday
            if now < market_open:
                time_diff = market_open - now
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                time_until_open = f"{hours}h {minutes}m until open"
            elif market_open <= now <= market_close:
                time_diff = market_close - now
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                time_until_close = f"{hours}h {minutes}m until close"
        
        return {
            'mode': self.mode,
            'timestamp': datetime.now().isoformat(),
            'market_status': market_status,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'market_open_time': market_open.strftime('%H:%M %Z'),
            'market_close_time': market_close.strftime('%H:%M %Z'),
            'time_until_open': time_until_open,
            'time_until_close': time_until_close,
            
            # Bot status
            'bot_connected': getattr(self.bot, 'connected', True) if self.bot else False,
            'active_positions': len(current_positions),
            'daily_pnl': daily_pnl,
            'daily_trades': daily_trades,
            'total_pnl': self.performance_data['total_pnl'],
            
            # Positions
            'positions': current_positions,
            
            # Performance
            'performance': self.performance_data,
            
            # Recent trades
            'recent_trades': self.trade_history[-10:],  # Last 10 trades
            
            # Analysis Data
            'analysis': self.latest_analysis
        }

# Simple Flask Dashboard
if DASHBOARD_AVAILABLE:
    app = Flask(__name__)
    
    # Global dashboard instance
    dashboard = None
    
    @app.route('/')
    def index():
        """Main dashboard page."""
        return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading System Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; color: #333; }
        .header { background: #1a252f; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header-info { text-align: right; font-size: 0.9em; }
        .container { display: grid; grid-template-columns: 300px 1fr; gap: 20px; }
        .sidebar { display: flex; flex-direction: column; gap: 20px; }
        .main-content { display: flex; flex-direction: column; gap: 20px; }
        
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .card h3 { margin-top: 0; border-bottom: 2px solid #f0f2f5; padding-bottom: 10px; color: #2c3e50; }
        
        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .metric-item { background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
        .metric-label { font-size: 0.8em; color: #7f8c8d; }
        
        .positive { color: #27ae60; }
        .negative { color: #e74c3c; }
        
        .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8em; font-weight: bold; color: white; }
        .status-open { background: #27ae60; }
        .status-closed { background: #e74c3c; }
        .status-premarket { background: #f39c12; }
        
        .analysis-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        .analysis-table th, .analysis-table td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        .analysis-table th { background-color: #f8f9fa; color: #7f8c8d; }
        .recommendation-buy { color: #27ae60; font-weight: bold; }
        .recommendation-hold { color: #f39c12; font-weight: bold; }
        .recommendation-avoid { color: #e74c3c; font-weight: bold; }
        
        .refresh-btn { background: #3498db; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
        .refresh-btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1 style="margin:0;">🚀 Trading System</h1>
            <div id="system-mode" style="font-size: 0.8em; opacity: 0.8;">Initializing...</div>
        </div>
        <div class="header-info">
            <div id="current-time">--:--:--</div>
            <div id="market-status"><span class="status-badge status-closed">Loading...</span></div>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="card">
                <h3>📊 Live Metrics</h3>
                <div class="metric-grid" id="metrics">
                    <!-- Populated by JS -->
                    <div style="grid-column: span 2; text-align: center;">Waiting for data...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🛠 Controls</h3>
                <button class="refresh-btn" onclick="updateDashboard()" style="width: 100%;">🔄 Refresh Data</button>
                <p style="font-size: 0.8em; color: #7f8c8d; margin-top: 10px; text-align: center;">
                    Auto-refreshes every 5s
                </p>
            </div>
        </div>
        
        <div class="main-content">
            <div class="card">
                <h3>🧠 Latest Analysis <span id="analysis-file" style="font-size: 0.6em; font-weight: normal; color: #95a5a6;"></span></h3>
                <div style="overflow-x: auto;">
                    <table class="analysis-table">
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Price</th>
                                <th>Rec</th>
                                <th>Conf</th>
                                <th>Strategy</th>
                                <th>Score</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="analysis-list">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>
    </div>
    
            <div class="card">
        <h3>📈 Active Positions</h3>
        <div id="positions-list">
                    <p style="color: #7f8c8d; text-align: center;">No active positions</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/dashboard_data')
                .then(response => response.json())
                .then(data => {
                    updateHeader(data);
                    updateMetrics(data);
                    updateAnalysis(data);
                    updatePositions(data);
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateHeader(data) {
            document.getElementById('system-mode').innerText = `Mode: ${data.mode} | Bot: ${data.bot_connected ? '🟢 Online' : '🔴 Offline'}`;
            document.getElementById('current-time').innerText = data.current_time;
            
            const statusDiv = document.getElementById('market-status');
            let statusClass = 'status-closed';
            if (data.market_status === 'OPEN') statusClass = 'status-open';
            if (data.market_status === 'PRE-MARKET') statusClass = 'status-premarket';
            
            statusDiv.innerHTML = `<span class="status-badge ${statusClass}">${data.market_status}</span>`;
            if (data.time_until_open) statusDiv.innerHTML += ` <small>${data.time_until_open}</small>`;
        }
        
        function updateMetrics(data) {
            const metrics = document.getElementById('metrics');
            metrics.innerHTML = `
                <div class="metric-item">
                    <div class="metric-value ${data.daily_pnl >= 0 ? 'positive' : 'negative'}">$${data.daily_pnl.toFixed(2)}</div>
                    <div class="metric-label">Daily P&L</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${data.active_positions}</div>
                    <div class="metric-label">Positions</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${data.daily_trades}</div>
                    <div class="metric-label">Trades</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${data.performance.win_rate.toFixed(1)}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
            `;
        }
        
        function updateAnalysis(data) {
            const list = document.getElementById('analysis-list');
            const fileLabel = document.getElementById('analysis-file');
            
            if (!data.analysis || !data.analysis.results) {
                list.innerHTML = '<tr><td colspan="7" style="text-align:center">No analysis data found</td></tr>';
                return;
            }
            
            fileLabel.innerText = `(${data.analysis.file})`;
            
            // Handle both single result (dict) and list of results
            let results = Array.isArray(data.analysis.results) ? data.analysis.results : [data.analysis.results];
            
            list.innerHTML = results.map(item => {
                const rec = item.recommendation || {};
                const fund = item.analyses?.fundamentals || {};
                const actionClass = (rec.action === 'BUY' || rec.action === 'STRONG_BUY') ? 'recommendation-buy' : 
                                  (rec.action === 'AVOID') ? 'recommendation-avoid' : 'recommendation-hold';
                
                return `
                    <tr>
                        <td><strong>${item.ticker}</strong></td>
                        <td>$${item.current_price?.toFixed(2) || 'N/A'}</td>
                        <td class="${actionClass}">${rec.action || 'N/A'}</td>
                        <td>${rec.confidence || '-'}</td>
                        <td>${rec.strategy || '-'}</td>
                        <td>${fund.score || 0}/100</td>
                        <td>
                            ${rec.action === 'BUY' ? '🚀' : ''}
                            ${rec.strategy === 'leaps' ? '📅' : ''}
                            ${rec.strategy === 'day_trade' ? '⚡' : ''}
                        </td>
                    </tr>
            `;
            }).join('');
        }
        
        function updatePositions(data) {
            const list = document.getElementById('positions-list');
            if (!data.positions || data.positions.length === 0) {
                list.innerHTML = '<p style="color: #7f8c8d; text-align: center;">No active positions</p>';
                return;
            }
            
            list.innerHTML = data.positions.map(pos => `
                <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                    <div style="display:flex; justify-content:space-between;">
                        <strong>${pos.symbol}</strong>
                        <span class="${pos.current_pnl >= 0 ? 'positive' : 'negative'}">$${pos.current_pnl.toFixed(2)} (${pos.pnl_pct.toFixed(2)}%)</span>
                    </div>
                    <div style="font-size: 0.9em; color: #666;">
                        ${pos.shares} shares @ $${pos.entry_price.toFixed(2)} → $${pos.current_price.toFixed(2)}
                    </div>
                </div>
            `).join('');
        }
        
        setInterval(updateDashboard, 5000);
        updateDashboard();
    </script>
</body>
</html>
        ''')
    
    @app.route('/api/dashboard_data')
    def api_dashboard_data():
        """API endpoint for dashboard data."""
        if not dashboard:
            return jsonify({'error': 'Dashboard not initialized'})
        
        data = dashboard.get_dashboard_data()
        return jsonify(data)


def start_simple_dashboard(dashboard_instance, host='127.0.0.1', port=5000):
    """Start the simple trading dashboard server."""
    global dashboard
    
    if not DASHBOARD_AVAILABLE:
        print("⚠️ Flask not installed. Dashboard will not start.")
        return
    
    dashboard = dashboard_instance
    
    print(f"🌐 Starting Trading Dashboard at http://{host}:{port}")
    # Suppress Flask logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)

def run_simple_dashboard():
    """Run the dashboard in standalone viewer mode."""
    if not DASHBOARD_AVAILABLE:
        print("❌ Dashboard dependencies not installed")
        return
    
    # Create dashboard in viewer mode (no bot)
    dash = SimpleTradingDashboard(bot_instance=None)
    
    print("🌐 Trading System Dashboard (Viewer Mode)")
    print(f"📂 Watching data/output/ for analysis results...")
    
    start_simple_dashboard(dash)

if __name__ == "__main__":
    run_simple_dashboard()
