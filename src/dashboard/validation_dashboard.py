#!/usr/bin/env python3
"""
Validation Dashboard - Track Bot Performance Over 100 Days
===========================================================

Monitor bot accuracy and validate readiness for production.
"""

from flask import Flask, render_template_string, jsonify
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.trade_tracker import TradeTracker
from datetime import datetime, timedelta
import json

app = Flask(__name__)
tracker = TradeTracker()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Validation Dashboard - 1000 Trade Test</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 36px;
            margin: 10px 0;
        }
        .status-banner {
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 30px;
        }
        .status-approved { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .status-testing { background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%); }
        .status-failed { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .card h3 {
            margin-top: 0;
            font-size: 16px;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card .value {
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }
        .card .subtext {
            font-size: 14px;
            opacity: 0.7;
        }
        .green { color: #38ef7d; }
        .red { color: #f45c43; }
        .yellow { color: #f2c94c; }
        
        .trades-table {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th {
            background: rgba(255, 255, 255, 0.1);
            font-weight: bold;
        }
        .progress-bar {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            height: 30px;
            margin: 20px 0;
            overflow: hidden;
        }
        .progress-fill {
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: width 0.5s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Trading Bot Validation Dashboard</h1>
            <p>1000-Trade Performance Test - Production Readiness Validation</p>
            <p>Last Updated: <span id="timestamp"></span></p>
        </div>
        
        <div class="status-banner" id="statusBanner">
            <span id="statusText">Loading...</span>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Total Trades</h3>
                <div class="value" id="totalTradesDisplay">0</div>
                <div class="subtext">Target: 1000 trades</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="tradesProgress" style="width: 0%">0%</div>
                </div>
            </div>
            
            <div class="card">
                <h3>Accuracy</h3>
                <div class="value" id="accuracy">0%</div>
                <div class="subtext">Threshold: 55%</div>
            </div>
            
            <div class="card">
                <h3>Total Trades</h3>
                <div class="value" id="totalTrades">0</div>
                <div class="subtext"><span id="winners" class="green">0W</span> / <span id="losers" class="red">0L</span></div>
            </div>
            
            <div class="card">
                <h3>Total P&L</h3>
                <div class="value" id="totalPnl">$0</div>
                <div class="subtext">Avg: <span id="avgPnl">$0</span>/trade</div>
            </div>
            
            <div class="card">
                <h3>Win Rate</h3>
                <div class="value" id="winRate">0%</div>
                <div class="subtext">Profit Factor: <span id="profitFactor">0</span></div>
            </div>
            
            <div class="card">
                <h3>Max Drawdown</h3>
                <div class="value red" id="maxDrawdown">$0</div>
                <div class="subtext">Worst streak</div>
            </div>
        </div>
        
        <div class="trades-table">
            <h2>📊 Recent Trades</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Symbol</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Shares</th>
                        <th>Hold Time</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody id="tradesTable">
                    <tr><td colspan="9" style="text-align: center;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/validation_data')
                .then(response => response.json())
                .then(data => {
                    // Update timestamp
                    document.getElementById('timestamp').textContent = new Date().toLocaleString();
                    
                    // Update status banner
                    const status = data.validation.status;
                    const banner = document.getElementById('statusBanner');
                    const statusText = document.getElementById('statusText');
                    
                    const totalTrades = data.summary.total_trades || 0;
                    const targetTrades = 1000;
                    
                    if (status === 'APPROVED') {
                        banner.className = 'status-banner status-approved';
                        statusText.textContent = '✅ BOT APPROVED FOR PRODUCTION - Accuracy ' + data.summary.accuracy.toFixed(1) + '% ≥ 55%';
                    } else if (status === 'INSUFFICIENT_DATA' || totalTrades < targetTrades) {
                        banner.className = 'status-banner status-testing';
                        statusText.textContent = '⏳ TESTING IN PROGRESS - Trade ' + totalTrades + '/1000';
                    } else if (status === 'FAILED') {
                        banner.className = 'status-banner status-failed';
                        statusText.textContent = '❌ BELOW THRESHOLD - Accuracy ' + data.summary.accuracy.toFixed(1) + '% < 55%';
                    } else {
                        banner.className = 'status-banner status-testing';
                        statusText.textContent = '⏳ WAITING FOR DATA - Start trading to begin validation';
                    }
                    
                    // Update metrics
                    document.getElementById('totalTradesDisplay').textContent = totalTrades;
                    document.getElementById('accuracy').textContent = (data.summary.accuracy || 0).toFixed(1) + '%';
                    document.getElementById('totalTrades').textContent = totalTrades;
                    document.getElementById('winners').textContent = (data.summary.winning_trades || 0) + 'W';
                    document.getElementById('losers').textContent = (data.summary.losing_trades || 0) + 'L';
                    
                    const pnl = data.summary.total_pnl || 0;
                    const pnlElement = document.getElementById('totalPnl');
                    pnlElement.textContent = '$' + pnl.toFixed(2);
                    pnlElement.className = 'value ' + (pnl >= 0 ? 'green' : 'red');
                    
                    document.getElementById('avgPnl').textContent = '$' + (data.summary.avg_pnl_per_trade || 0).toFixed(2);
                    document.getElementById('winRate').textContent = (data.summary.win_rate || 0).toFixed(1) + '%';
                    document.getElementById('profitFactor').textContent = (data.summary.profit_factor || 0).toFixed(2);
                    document.getElementById('maxDrawdown').textContent = '$' + (data.summary.max_drawdown || 0).toFixed(2);
                    
                    // Update progress bar
                    const tradesProgress = Math.min(100, (totalTrades / targetTrades * 100));
                    document.getElementById('tradesProgress').style.width = tradesProgress + '%';
                    document.getElementById('tradesProgress').textContent = tradesProgress.toFixed(1) + '%';
                    
                    // Update trades table
                    const tbody = document.getElementById('tradesTable');
                    if (data.trades && data.trades.length > 0) {
                        tbody.innerHTML = data.trades.map(trade => {
                            const pnlClass = trade.pnl > 0 ? 'green' : trade.pnl < 0 ? 'red' : '';
                            return `
                                <tr>
                                    <td>${new Date(trade.entry_time).toLocaleDateString()}</td>
                                    <td><strong>${trade.symbol}</strong></td>
                                    <td>$${trade.entry_price.toFixed(2)}</td>
                                    <td>$${(trade.exit_price || 0).toFixed(2)}</td>
                                    <td>${trade.shares}</td>
                                    <td>${trade.hold_time_minutes || 0}m</td>
                                    <td class="${pnlClass}">$${(trade.pnl || 0).toFixed(2)}</td>
                                    <td class="${pnlClass}">${(trade.pnl_pct || 0).toFixed(2)}%</td>
                                    <td>${trade.exit_reason || 'Open'}</td>
                                </tr>
                            `;
                        }).join('');
                    } else {
                        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No trades yet - start trading to see data</td></tr>';
                    }
                });
        }
        
        // Update every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/validation_data')
def get_validation_data():
    """Get validation data for dashboard."""
    summary = tracker.get_performance_summary()  # All trades
    
    # Custom validation for 1000 trades
    total_trades = summary.get('total_trades', 0)
    accuracy = summary.get('accuracy', 0)
    
    if total_trades >= 1000:
        if accuracy >= 55:
            status = 'APPROVED'
            recommendation = '✅ Bot meets accuracy threshold - READY FOR PRODUCTION'
        else:
            status = 'FAILED'
            recommendation = f'❌ Bot accuracy {accuracy:.1f}% < 55% threshold'
    else:
        status = 'INSUFFICIENT_DATA'
        recommendation = f'Continue testing - {1000 - total_trades} more trades needed'
    
    validation = {
        'status': status,
        'recommendation': recommendation,
        'total_trades': total_trades,
        'target_trades': 1000
    }
    
    trades = tracker.get_all_trades(100)  # Last 100 trades
    
    return jsonify({
        'summary': summary,
        'validation': validation,
        'trades': trades,
        'timestamp': datetime.now().isoformat()
    })

def start_validation_dashboard(host='127.0.0.1', port=5001):
    """Start the validation dashboard."""
    print(f"\n🌐 Starting Validation Dashboard at http://{host}:{port}")
    print("📊 Monitor 100-day bot validation in real-time")
    print("🎯 Target: 55% accuracy for production approval\n")
    
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    start_validation_dashboard()
