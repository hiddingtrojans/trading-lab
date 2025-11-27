# Complete LEAPS Analysis System

Professional-grade LEAPS (Long-term Equity Anticipation Securities) analysis system that integrates fundamentals, news sentiment, sector intelligence, GPT analysis, price prediction, and LEAPS strategy into one unified tool.

## 🎯 Main Tool: Complete LEAPS System

### **`complete_leaps_system.py` - The Unified Solution**
**Everything integrated into one systematic analysis:**
- 📊 **Comprehensive fundamentals** (growth, profitability, valuation)
- 📰 **News sentiment analysis** (recent developments, market sentiment)
- 🏭 **Sector intelligence** (tailwinds, competitive dynamics, policy impact)
- 🤖 **GPT analysis** (institutional-quality insights and recommendations)
- 🎯 **Price prediction** (12-month and 24-month targets with confidence levels)
- 📋 **LEAPS strategy** (optimal strikes, expiry dates, position sizing)

### **Supporting Tools:**
- **`ticker_check.py`** - Quick LEAPS availability check (when market open)
- **`leaps_analyzer.py`** - Detailed option analysis (when market open)

## Requirements

### Software Prerequisites
- Python 3.8 or higher
- Interactive Brokers TWS or IB Gateway
- Active IBKR account with market data subscriptions

### Python Dependencies
Install dependencies using pip:
```bash
pip install -r requirements.txt
```

Core dependencies:
- `ib_insync>=0.9.86` - IBKR API wrapper
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical computations
- `tabulate>=0.9.0` - Table formatting
- `pyyaml>=6.0` - Configuration files

## Setup Instructions

### 1. Configure Interactive Brokers Gateway

#### Option A: IB Gateway (Recommended for automated scanning)
1. Download and install IB Gateway from Interactive Brokers
2. Launch IB Gateway
3. Configure settings:
   - **Socket Port**: 4001 (default for live trading) or 7497 (paper trading)
   - **Enable API**: Check "Enable ActiveX and Socket Clients"
   - **Read-Only API**: Uncheck (we need market data access)
   - **Master API client ID**: Leave blank or set to 0
   - **Trusted IPs**: Add 127.0.0.1

#### Option B: TWS (Trader Workstation)
1. Launch TWS and log in
2. Go to **File > Global Configuration > API > Settings**
3. Configure:
   - **Enable ActiveX and Socket Clients**: Check
   - **Socket port**: 7497 (paper) or 7496 (live)
   - **Master API client ID**: 0
   - **Read-only API**: Uncheck

### 2. Market Data Subscriptions
Ensure your IBKR account has the necessary market data subscriptions:
- **US Securities Snapshot and Futures Value Bundle** (recommended)
- **US Equity and Options Add-On Streaming Bundle** (for real-time data)

### 3. Configure Scanner Settings
The scanner uses these default connection settings (modify in `scanner.py` if needed):
```python
host = '127.0.0.1'      # Local machine
port = 4001             # IB Gateway default (use 7497 for TWS paper)
client_id = 7           # Unique identifier for this connection
```

## Quick Start

### 1. Activate Virtual Environment:
```bash
cd /Users/raulacedo/Desktop/scanner
source venv/bin/activate
```
You should see `(venv)` in your terminal prompt.

### 2. Check if a ticker has LEAPS options:
```bash
python ticker_check.py TSLA
```

### 3. Analyze the best LEAPS options for a ticker:
```bash
python leaps_analyzer.py TSLA
```

### 4. Batch scan multiple tickers:
```bash
# Scan specific tickers
python leaps_analyzer.py --batch TSLA NVDA SOFI GRAB

# Scan entire universe for excellent options (score ≥ 7.0)
python leaps_analyzer.py --from-csv --min-score 7.0

# Lower threshold for more results
python leaps_analyzer.py --from-csv --min-score 6.5
```

### Example Output:
```
🏆 BEST LEAPS OPTION SUMMARY
Best Option: $260 strike (June 2026) - Score 6.6
Premium: $108.62, Delta: 0.80, IV: 54%
Only needs 10% upside to breakeven 🟢
Tight 1.3% bid-ask spread 🟢  
High delta (0.80) = excellent leverage 🟢
Low liquidity: 0 open interest 🔴
Rich time value: 9.9% of stock price 🟡
```

## Tool Details

### Ticker Checker Features:
- ✅ Stock contract verification
- ✅ Current price lookup  
- ✅ Option chain availability
- ✅ LEAPS expiry identification
- ⚡ Fast screening (5 seconds)

### LEAPS Analyzer Features:
- 📊 **Real-time pricing** with bid/ask/mid
- 📈 **Greeks calculation** (delta, gamma, theta, vega, IV)
- 💰 **Key metrics**: intrinsic value, time value, breakeven
- 🎯 **Smart scoring** based on delta fit, liquidity, spreads
- 🚨 **Arbitrage detection** for pricing violations
- 🏆 **Clean summary** with color-coded recommendations

### Analysis Criteria:
- **Delta Range**: 0.50 - 0.90 (relaxed for small caps)
- **Maximum Spread**: 25% (realistic for small caps)  
- **Minimum Open Interest**: 5 contracts
- **Minimum Days to Expiry**: 270 days (LEAPS definition)

## Quick Start Guide

### 🚀 One-Click Analysis:
```bash
# Double-click this file in Finder:
./run_leaps_finder.sh

# Or run manually:
cd /Users/raulacedo/Desktop/scanner
source venv/bin/activate
export OPENAI_API_KEY='your-openai-api-key'
```

### 🎯 Complete Analysis Commands:

#### **Single Ticker (Full Analysis):**
```bash
python complete_leaps_system.py TICKER
```
**Output**: Complete systematic analysis with price predictions and LEAPS strategy

#### **Multiple Tickers:**
```bash
python complete_leaps_system.py --batch BCRX AIRO LUNR
```

#### **Quick LEAPS Check (Market Hours Only):**
```bash
python ticker_check.py TICKER
python leaps_analyzer.py TICKER
```

## System Components Integration

### **What the Complete System Does:**
1. **📊 Fundamental Analysis** - Revenue growth, profitability, analyst targets
2. **📰 News Sentiment** - Recent developments and market sentiment
3. **🏭 Sector Intelligence** - Industry outlook and competitive dynamics  
4. **🤖 GPT Analysis** - Professional-grade insights and recommendations
5. **🎯 Price Prediction** - 12-month and 24-month targets with confidence
6. **📋 LEAPS Strategy** - Specific strikes, expiries, and position sizing

### **Example Output:**
```
🚀 STRONG BUY LEAPS (Score: 81/100)
12-Month Target: $25.50 (+31%)
24-Month Target: $35.75 (+84%)
Optimal Strike: $18.50
Expected Return: 85%
Position Size: 4.0% of portfolio
```

## Customization

### Modifying Filter Criteria
Edit the `__init__` method in `LEAPSScanner` class:
```python
self.min_delta = 0.65           # Minimum delta
self.max_delta = 0.85           # Maximum delta
self.max_spread_pct = 8.0       # Maximum bid-ask spread %
self.min_oi = 500               # Minimum open interest
self.max_breakeven_upside = 30.0 # Maximum breakeven upside %
```

### Adjusting Scoring Weights
Modify the `calculate_score` method to change scoring emphasis:
```python
score = (
    2.0 * delta_fit +          # Delta importance
    2.0 * time_value_eff +     # Time value importance
    1.5 * iv_rel +             # IV importance
    1.0 * spread_score +       # Spread importance
    1.5 * breakeven_score +    # Breakeven importance
    1.0 * liquidity            # Liquidity importance
)
```

### Adding New Tickers
Edit `leaps_universe_ibkr.csv` to add new tickers:
```csv
Ticker,Sector,Theme
NVDA,Technology,AI/Semiconductors
TSLA,Automotive,Electric Vehicles
```

## Troubleshooting

### Connection Issues
- **"Failed to connect to IBKR Gateway"**: Ensure IB Gateway is running and API is enabled
- **Port conflicts**: Check if port 4001 (or your configured port) is available
- **Authentication errors**: Verify your IBKR account is logged in and active

### Market Data Issues
- **"No market data"**: Check your market data subscriptions in IBKR account
- **Delayed/missing Greeks**: Some options may not have model Greeks available
- **Missing open interest**: Data may not be available for all contracts

### Performance Optimization
- **Slow scanning**: Reduce the ticker universe or implement parallel processing
- **Memory usage**: Process tickers in batches for large universes
- **API limits**: Add delays between requests to avoid rate limiting

### Common Error Messages
- **"Could not qualify stock"**: Ticker may be delisted or not available
- **"No option chains found"**: Stock may not have options or LEAPS available
- **"No qualifying options found"**: All options filtered out by criteria

## API Rate Limits

The scanner includes built-in delays to respect IBKR API limits:
- 0.1 second delay between expiries
- 0.2 second delay between tickers
- 1-2 second delays for market data requests

For large universes, consider running during off-market hours for better performance.

## Disclaimer

This tool is for educational and research purposes only. Options trading involves substantial risk and may not be suitable for all investors. Past performance does not guarantee future results. Always conduct your own analysis and consult with financial professionals before making investment decisions.

The arbitrage detection feature identifies potential pricing inconsistencies but does not guarantee profitable arbitrage opportunities due to transaction costs, liquidity constraints, and market dynamics.

## License

This project is provided as-is for educational purposes. Use at your own risk.
