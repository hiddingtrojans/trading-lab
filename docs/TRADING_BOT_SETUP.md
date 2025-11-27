# Day Trading Bot - Setup & Usage Guide

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
# Navigate to the directory
cd /Users/raulacedo/Desktop/scanner

# Activate virtual environment (already created)
source leaps_env/bin/activate

# The bot is ready to run!
```

### 2. **Configure IB Gateway**

#### **Download & Install IB Gateway**
1. Download from: https://www.interactivebrokers.com/en/trading/ib-api.php
2. Install IB Gateway (not TWS)
3. Create paper trading account if needed

#### **Configure API Settings**
1. Open IB Gateway
2. Login with your credentials
3. Go to **Configure → API → Settings**
4. Enable **"Enable ActiveX and Socket Clients"**
5. Set **Socket port** to **4002** (paper) or **4001** (live)
6. Add **127.0.0.1** to **Trusted IPs**
7. Click **OK** and restart Gateway

### 3. **Test Connection**
```bash
# Test if IB Gateway is accessible
python trading_config.py
```

### 4. **Run the Bot**

#### **Paper Trading (Recommended for testing)**
```bash
# Run with default paper trading settings
python day_trading_bot.py
```

#### **Live Trading (Only when ready!)**
```bash
# Edit trading_config.py first:
# Set USE_PAPER_TRADING = False
# Set IB_PORT = 4001

python day_trading_bot.py
```

## 📊 **Bot Features**

### **What It Does:**
1. **🔍 Pre-Market Scanning**
   - Scans for stocks with market cap >$1B
   - Finds overnight gaps >3%
   - Checks pre-market volume >20K

2. **📈 Technical Analysis**
   - Calculates real-time VWAP (2min, 5min bars)
   - Identifies support/resistance levels
   - Monitors volume confirmation

3. **🎯 VWAP Long Strategy**
   - Enters long when price tests and holds VWAP after gap up
   - Stop loss: 5-min close below VWAP
   - Take profit: 2% above VWAP

4. **🛡️ Risk Management**
   - Position sizing based on buying power
   - Daily loss limits
   - Maximum position limits
   - End-of-day position closure

5. **📝 Comprehensive Logging**
   - All trades logged with timestamps
   - Real-time market analysis
   - Daily P&L tracking
   - Error handling and recovery

## ⚙️ **Configuration Options**

### **Edit `trading_config.py` to customize:**

#### **Trading Parameters**
```python
'MAX_POSITION_PCT': 10.0,     # Max % of buying power per trade
'STOP_LOSS_PCT': 2.0,         # Stop loss percentage
'TAKE_PROFIT_PCT': 2.0,       # Take profit percentage
'MAX_DAILY_LOSS': 1000.0,     # Daily loss limit
```

#### **Scanning Criteria**
```python
'MIN_MARKET_CAP': 1e9,        # $1B minimum market cap
'MIN_GAP_PCT': 3.0,           # 3% minimum gap
'MIN_PREMARKET_VOLUME': 20000, # 20K volume threshold
```

#### **Risk Limits**
```python
'MAX_POSITIONS': 3,           # Max concurrent positions
'MAX_DAILY_TRADES': 10,       # Max trades per day
```

## 🔧 **Troubleshooting**

### **Common Issues:**

#### **"Connection failed"**
- ✅ Check IB Gateway is running
- ✅ Verify API is enabled in Gateway settings
- ✅ Confirm port 4002 (paper) or 4001 (live)
- ✅ Check trusted IPs include 127.0.0.1

#### **"No candidates found"**
- ✅ Run during pre-market hours (4:00-9:30 AM ET)
- ✅ Check if there are actual gap-up stocks today
- ✅ Lower scanning criteria if needed

#### **"Order rejected"**
- ✅ Check account has sufficient buying power
- ✅ Verify stock is tradeable in your account
- ✅ Check position size limits

### **Safety Features:**
- ✅ **Paper trading by default** - No real money at risk
- ✅ **Daily loss limits** - Auto-stop on excessive losses
- ✅ **Position limits** - Prevents over-exposure
- ✅ **End-of-day closure** - No overnight positions
- ✅ **Comprehensive logging** - Full audit trail

## 📱 **Email Alerts (Optional)**

### **Setup Email Notifications:**
1. Edit `trading_config.py`:
```python
EMAIL_CONFIG = {
    'ENABLE_EMAIL_ALERTS': True,
    'EMAIL_USER': 'your_email@gmail.com',
    'EMAIL_PASS': 'your_app_password',  # Not regular password!
    'EMAIL_TO': 'alerts@yourdomain.com',
}
```

2. **For Gmail**: Generate app password at https://myaccount.google.com/apppasswords

## 🎯 **Usage Examples**

### **Morning Routine:**
```bash
# 1. Start IB Gateway (paper trading)
# 2. Activate environment
source leaps_env/bin/activate

# 3. Run bot (will scan pre-market, then trade during market hours)
python day_trading_bot.py
```

### **Monitor Progress:**
- Watch console output for real-time updates
- Check `logs/trading_bot_YYYYMMDD.log` for detailed logs
- Monitor email alerts if enabled

### **End of Day:**
- Bot automatically closes all positions at market close
- Review daily summary in logs
- Check P&L and trade performance

## ⚠️ **Important Warnings**

### **Paper Trading First:**
- ✅ **Always test with paper trading** before live trading
- ✅ **Verify strategy performance** over multiple days
- ✅ **Understand all features** before risking real money

### **Live Trading Considerations:**
- ⚠️ **Real money at risk** - only use funds you can afford to lose
- ⚠️ **Market conditions vary** - past performance doesn't guarantee future results
- ⚠️ **Monitor actively** - automated trading requires supervision
- ⚠️ **Start small** - use conservative position sizing initially

## 📈 **Strategy Details**

### **VWAP Long Strategy:**
1. **Pre-market**: Scan for gap-up candidates
2. **Market open**: Wait for VWAP establishment
3. **Entry**: Price tests and holds VWAP with volume
4. **Management**: Stop below VWAP, profit above VWAP
5. **Exit**: End of day or signal-based

### **Risk Management:**
- **Position sizing**: Max 10% of buying power
- **Stop loss**: 2% below VWAP
- **Daily limits**: Max loss and trade count
- **Time limits**: No overnight positions

---

**The bot is production-ready with professional risk management and comprehensive logging. Start with paper trading to validate performance!** 🎯

