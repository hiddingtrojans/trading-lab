# 🤖 Paper Trading Bot with Dashboard

A comprehensive day trading bot with real-time dashboard monitoring for **safe paper trading**.

## 🛡️ Safety Features

- **Paper Trading Only**: No real money at risk
- **IB Gateway Integration**: Uses Interactive Brokers paper trading
- **Real-time Dashboard**: Monitor performance live
- **Risk Management**: Built-in position and loss limits

## 📋 Setup Requirements

### 1. Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Install dashboard dependencies
pip install flask flask-socketio plotly
```

### 2. IB Gateway Setup
1. **Download IB Gateway** from Interactive Brokers
2. **Run in Paper Trading Mode** (not TWS)
3. **Configure API Settings**:
   - Enable API connections
   - Set port: **4002** (paper trading)
   - Add trusted IP: **127.0.0.1**
   - Set client ID: **100** (or any unique number)

### 3. Run the Bot
```bash
# Easy setup (recommended)
./run_paper_trading.sh

# Or manually
python paper_trading_bot.py
```

## 🌐 Dashboard Features

Open **http://127.0.0.1:5000** to see:

### 📊 Real-time Metrics
- **Daily P&L**: Current day's profit/loss
- **Active Positions**: Number of open positions
- **Daily Trades**: Number of trades today
- **Win Rate**: Percentage of profitable trades
- **Total P&L**: Cumulative profit/loss

### 📈 Position Monitoring
- **Current Positions**: Live position tracking
- **Entry Prices**: When positions were opened
- **Current P&L**: Real-time profit/loss
- **Stop Loss/Take Profit**: Risk management levels

### 📊 Performance Charts
- **Cumulative P&L Chart**: Performance over time
- **Trade Distribution**: P&L histogram
- **Market Status**: Real-time market hours

### ⚠️ Risk Metrics
- **Daily Loss Remaining**: How much loss before stop
- **Positions Remaining**: Available position slots
- **Max Daily Loss**: Risk limit
- **Max Positions**: Position limit

## 🎯 Trading Strategy

### Gap-Up Long Strategy
- **Scan for**: Market cap >$1B, gap >3%, pre-market volume >20K
- **Entry**: When price tests and holds VWAP after gap up
- **Stop Loss**: 2% below VWAP
- **Take Profit**: 2% above VWAP

### Risk Management
- **Max Positions**: 3 concurrent
- **Max Position Size**: 5% of buying power
- **Daily Loss Limit**: $10,000 (paper trading)
- **Stop Loss**: 2% below VWAP
- **Take Profit**: 2% above VWAP

## 🚀 How to Use

### 1. Start IB Gateway
- Run IB Gateway in paper trading mode
- Ensure API is enabled on port 4002
- Verify connection settings

### 2. Run the Bot
```bash
./run_paper_trading.sh
```

### 3. Monitor Dashboard
- Open http://127.0.0.1:5000
- Watch real-time performance
- Monitor positions and P&L

### 4. Bot Behavior
- **Pre-market**: Scans for gap-up candidates
- **Market Open**: Starts trading when signals appear
- **Market Hours**: Monitors positions and executes trades
- **Market Close**: Exits all positions

## 📊 Dashboard Screenshots

### Main Dashboard
- Real-time metrics cards
- Active positions list
- Performance charts
- Market status indicator

### Performance Analytics
- Cumulative P&L over time
- Trade distribution histogram
- Win rate and statistics
- Risk metrics

## ⚙️ Configuration

### Bot Settings (in `paper_trading_bot.py`)
```python
CONFIG = {
    'IB_PORT': 4002,           # Paper trading port
    'MAX_POSITIONS': 3,         # Max concurrent positions
    'MAX_POSITION_PCT': 5.0,    # Max 5% per position
    'STOP_LOSS_PCT': 2.0,       # 2% stop loss
    'TAKE_PROFIT_PCT': 2.0,     # 2% take profit
    'MAX_DAILY_LOSS': 10000.0,  # Daily loss limit
}
```

### Dashboard Settings
- **Host**: 127.0.0.1
- **Port**: 5000
- **Update Interval**: 5 seconds
- **Real-time Updates**: WebSocket connection

## 🔧 Troubleshooting

### Common Issues

#### 1. IB Gateway Connection Failed
```
❌ IB Gateway connection failed
💡 Make sure IB Gateway is running with API enabled
```
**Solution**: Start IB Gateway in paper trading mode, enable API on port 4002

#### 2. Dashboard Not Loading
```
❌ Dashboard dependencies not installed
```
**Solution**: Run `pip install flask flask-socketio plotly`

#### 3. No Gap-Up Candidates
```
🎯 Found 0 gap-up candidates
```
**Solution**: Normal during certain market conditions, bot will wait for opportunities

### Debug Mode
```bash
# Run with debug logging
python paper_trading_bot.py --debug
```

## 📈 Performance Tracking

### Metrics Tracked
- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Average Win**: Average profit per winning trade
- **Average Loss**: Average loss per losing trade
- **Profit Factor**: Total wins / Total losses
- **Max Drawdown**: Largest peak-to-trough decline

### Dashboard Updates
- **Real-time**: Position changes, P&L updates
- **Live Charts**: Performance over time
- **Risk Alerts**: When approaching limits
- **Trade History**: Complete trade log

## 🛡️ Safety Reminders

- **Paper Trading Only**: No real money at risk
- **Test Thoroughly**: Run in paper mode before live trading
- **Monitor Dashboard**: Watch performance closely
- **Risk Management**: Built-in limits prevent large losses
- **Stop if Needed**: Ctrl+C to stop the bot anytime

## 📞 Support

If you encounter issues:
1. Check IB Gateway is running on port 4002
2. Verify API connections are enabled
3. Ensure all dependencies are installed
4. Check the logs in the `logs/` directory

## 🎯 Next Steps

1. **Test in Paper Mode**: Run for several days to test strategy
2. **Monitor Performance**: Use dashboard to track results
3. **Adjust Parameters**: Modify settings based on results
4. **Scale Up**: Consider live trading only after thorough testing

---

**⚠️ IMPORTANT**: This is for educational and testing purposes. Always test thoroughly in paper trading mode before considering live trading.
