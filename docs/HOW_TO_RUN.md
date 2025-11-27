# How to Run the Day Trading Bot

## 🎯 **Complete Step-by-Step Guide**

### **Step 1: Environment Setup** ✅ READY
```bash
# Navigate to the scanner directory
cd /Users/raulacedo/Desktop/scanner

# Activate the virtual environment (already set up)
source leaps_env/bin/activate
```

### **Step 2: Verify Setup**
```bash
# Test that everything is working
python test_trading_setup.py
```

**Expected output:**
- ✅ Dependencies: PASS
- ❌ IB Gateway Connection: FAIL (until you start Gateway)
- ✅ Market Data: PASS  
- ✅ Configuration: PASS

### **Step 3: Start IB Gateway**

#### **For Paper Trading (Recommended):**
1. **Download IB Gateway** from Interactive Brokers website
2. **Install and launch** IB Gateway
3. **Login** with your IB credentials
4. **Configure API**:
   - Go to **Configure → API → Settings**
   - Check **"Enable ActiveX and Socket Clients"**
   - Set **Socket port** to **4002**
   - Add **127.0.0.1** to **Trusted IPs**
   - Click **OK**

#### **For Live Trading (Advanced):**
- Same steps but use **port 4001**
- ⚠️ **WARNING: Real money at risk!**

### **Step 4: Run the Trading Bot**

#### **Basic Usage:**
```bash
# Run with default settings (paper trading)
python day_trading_bot.py
```

#### **Advanced Usage:**
```bash
# Test connection first
python trading_config.py

# Run bot with custom settings (edit trading_config.py first)
python day_trading_bot.py
```

## 📊 **What Happens When You Run It**

### **Pre-Market (4:00-9:30 AM ET):**
```
🤖 ROBUST DAY TRADING BOT
==================================================
📅 Date: 2025-09-17 08:00:00
🔌 Target: IB Gateway 127.0.0.1:4002
📊 Strategy: VWAP Long on Gap-Up Stocks
💰 Max Position: 10.0% of buying power
🛑 Stop Loss: 2.0% below VWAP
🎯 Take Profit: 2.0% above VWAP
==================================================

🔌 Connecting to IB Gateway...
✅ Connected to IB Gateway successfully
📊 Trading Account: DU123456

🌅 Pre-market: Scanning for candidates...
🔍 Scanning for gap-up candidates...
✅ Candidate: NVDA - Gap: 4.2%, Volume: 25,000
✅ Candidate: CRM - Gap: 3.8%, Volume: 32,000
🎯 Found 2 gap-up candidates

⏰ Waiting for market hours...
```

### **Market Hours (9:30 AM-4:00 PM ET):**
```
🔔 Market is open - Starting trading...

🎯 ENTRY SIGNAL: NVDA at $185.50
   Gap above resistance: True
   VWAP: $184.20
   Above VWAP: True

📈 LONG ENTRY: NVDA - 100 shares @ $185.55
📧 Alert sent: ENTRY NVDA

👁️ Monitoring positions...
📊 NVDA VWAP (5min): $184.85

📉 EXIT: NVDA - 100 shares @ $188.95
   Reason: Take profit: 2% above VWAP ($184.85)
   P&L: $340.00 (+1.8%)
   Daily P&L: $340.00
📧 Alert sent: EXIT NVDA
```

### **End of Day:**
```
🌅 Market closing - Exiting all positions...

📊 Daily Summary:
   Total Trades: 3
   Daily P&L: $245.50
   Candidates Scanned: 2

🏁 Trading session ended
```

## ⚙️ **Customization Options**

### **Edit `trading_config.py` for:**

#### **Risk Management:**
```python
'MAX_POSITION_PCT': 5.0,      # More conservative: 5% per position
'STOP_LOSS_PCT': 1.5,         # Tighter stop: 1.5%
'MAX_DAILY_LOSS': 500.0,      # Lower daily limit: $500
```

#### **Strategy Tuning:**
```python
'MIN_GAP_PCT': 2.0,           # Lower gap threshold: 2%
'TAKE_PROFIT_PCT': 1.5,       # Quicker profit taking: 1.5%
'MAX_POSITIONS': 5,           # More positions: 5
```

#### **Scanning Criteria:**
```python
'MIN_MARKET_CAP': 500e6,      # Smaller caps: $500M
'MAX_PRICE': 200.0,           # Lower price stocks: $200
'MIN_PREMARKET_VOLUME': 50000, # Higher volume: 50K
```

## 📁 **File Structure**
```
scanner/
├── day_trading_bot.py          # Main trading bot
├── trading_config.py           # Configuration settings
├── test_trading_setup.py       # Setup verification
├── TRADING_BOT_SETUP.md        # Detailed setup guide
├── HOW_TO_RUN.md              # This file
├── logs/                       # Trading logs (auto-created)
│   └── trading_bot_20250917.log
└── leaps_env/                  # Virtual environment
```

## 🎯 **Quick Start Commands**

### **Daily Trading Routine:**
```bash
# 1. Navigate and activate
cd /Users/raulacedo/Desktop/scanner
source leaps_env/bin/activate

# 2. Start IB Gateway (outside terminal)
# 3. Run the bot
python day_trading_bot.py

# 4. Monitor logs (in another terminal)
tail -f logs/trading_bot_$(date +%Y%m%d).log
```

### **Testing & Validation:**
```bash
# Test setup
python test_trading_setup.py

# Test configuration
python trading_config.py

# Dry run (no actual trading)
# Edit day_trading_bot.py and set DRY_RUN = True
```

## 🛡️ **Safety Features Built-In**

- ✅ **Paper trading by default** - No real money risk
- ✅ **Daily loss limits** - Auto-stop on losses
- ✅ **Position limits** - Prevents over-exposure  
- ✅ **End-of-day closure** - No overnight risk
- ✅ **Comprehensive logging** - Full audit trail
- ✅ **Error recovery** - Handles disconnections
- ✅ **Real-time monitoring** - Continuous position management

## 🚨 **Important Notes**

### **Before Live Trading:**
1. **Test extensively** with paper trading
2. **Understand the strategy** completely
3. **Monitor for several days** to validate performance
4. **Start with small position sizes**
5. **Have risk management plan**

### **During Trading:**
- **Monitor actively** - automation requires supervision
- **Check logs regularly** for any issues
- **Be ready to intervene** if needed
- **Respect daily loss limits**

---

**The bot is production-ready with professional risk management. Start with paper trading to validate the strategy before risking real capital!** 🎯

