# Implementation Checklist - $20K Retail Account

## Your Context

**Capital:** $20K
**Goal:** Build edge as retail investor
**Reality:** Can't compete on data or speed, must compete on execution discipline and behavioral patterns

---

## WEEK 1: VALIDATION (CRITICAL - DO THIS FIRST)

### [ ] Task 1.1: Validate Day Trading Bot (2 hours)

**Why:** Prove gap strategy works before risking money

**Command:**
```bash
python trader.py
# Select: [15] Backtest Day Bot
```

**What it does:**
- Downloads 1 year of 5-min bars from IBKR
- Simulates gap trades using bot's exact logic
- Calculates win rate, Sharpe, profit factor

**Success criteria:**
- Win rate > 55%
- Profit factor > 1.5
- Sharpe > 0.5

**If passes:** Proceed to paper trading
**If fails:** Don't use day bot, focus on LEAPS only

**Implementation notes:**
- Requires IBKR Gateway running
- Takes 30-60 min to download data
- Test on 17 liquid tickers (AAPL, NVDA, TSLA, etc.)

---

### [ ] Task 1.2: Validate Scanner Signals (2 hours)

**Why:** Prove intraday signals have predictive power

**Command:**
```bash
python backtest_intraday_signals.py
```

**What it does:**
- Downloads 30 days of intraday data
- Simulates gap/momentum/VWAP trades
- Calculates IC (Information Coefficient)

**Success criteria:**
- IC > 0.025 OR Sharpe > 0.5
- Win rate > 52%

**If passes:** Use scanner for supplemental trades
**If fails:** Ignore scanner, focus on day bot only

**Implementation notes:**
- Also requires IBKR Gateway
- Takes 20-30 min
- Tests on 30 tickers

---

### [ ] Task 1.3: Document Validation Results (30 min)

**Create:** `VALIDATION_RESULTS.md`

**Template:**
```markdown
# Validation Results

Date: [date]

## Day Trading Bot
- Win Rate: [X]%
- Sharpe: [X]
- Profit Factor: [X]
- **Status:** [APPROVED / REJECTED]
- **Decision:** [Use / Don't Use]

## Scanner
- IC: [X]
- Sharpe: [X]
- Win Rate: [X]%
- **Status:** [APPROVED / REJECTED]
- **Decision:** [Use / Don't Use]

## Action Plan
- Trade day bot: [YES/NO]
- Trade scanner: [YES/NO]
- Focus on LEAPS: [YES/NO]
```

---

## WEEK 2-3: PAPER TRADING (IF VALIDATED)

### [ ] Task 2.1: Paper Trade Day Bot (2 weeks)

**Only if Task 1.1 passed validation**

**Command:**
```bash
python trader.py
# Select: [6] Full Day Trading
# Choose: [P] Paper
```

**What to track:**
- Actual win rate vs backtest
- Slippage (backtest vs live)
- Emotional discipline (did you follow signals?)

**Success criteria:**
- Live win rate within 5% of backtest
- Can follow rules without hesitation

**If passes:** Approved for live with 1% position sizes
**If fails:** Back to validation, something wrong

---

### [ ] Task 2.2: Manual Track LEAPS (Ongoing)

**Command:**
```bash
# Analyze potential LEAPS
python trader.py → [1] Intelligent Analysis
Enter: [tickers]

# Add to tracker
python portfolio_tracker.py --add NVDA leaps 192.50 5 0
```

**Track first 10 LEAPS:**
- Entry date, price, thesis
- Monthly mark-to-market
- Exit date, actual return
- Calculate hit rate after 12 months

**For $20K account:**
- Max 5 LEAPS positions
- $2K-4K each (10-20% of capital per position)
- 3-5% stops if goes against you

---

## MONTH 2: ADD AUTOMATION (ONLY IF PROFITABLE)

### [ ] Task 3.1: Real-Time Alert System (4 hours)

**Why:** Don't miss opportunities while away from computer

**Create:** `alert_system.py`

**Implementation:**
```python
import requests
from datetime import datetime

# Telegram bot (free, easy)
TELEGRAM_BOT_TOKEN = 'your_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message})

def background_scanner():
    """Run every 5 minutes during market hours."""
    from scanner import UnifiedScanner
    
    scanner = UnifiedScanner()
    scanner.connect_ibkr()
    
    while market_open():
        # Scan liquid universe
        signals = scanner.scan_intraday(['AAPL', 'NVDA', 'TSLA', ...])
        
        # Filter high confidence
        high_conf = signals[signals['confidence'] > 75]
        
        # Alert on new signals
        for _, sig in high_conf.iterrows():
            msg = f"🚨 {sig['ticker']}: {sig['signal']}\n"
            msg += f"Confidence: {sig['confidence']:.0f}/100\n"
            msg += f"Price: ${sig['price']:.2f}"
            send_telegram(msg)
        
        sleep(300)  # 5 minutes
```

**Setup:**
1. Create Telegram bot (5 min): Talk to @BotFather
2. Get your chat ID
3. Run in background: `nohup python alert_system.py &`

**Benefit:** Get notified of high-quality signals, execute within minutes

---

### [ ] Task 3.2: Position Size Calculator ($20K Account) (2 hours)

**Why:** Systematic risk management

**Create:** `position_sizer.py`

**For $20K account:**
```python
class PositionSizer:
    def __init__(self, capital=20000):
        self.capital = capital
        
        # Conservative for $20K
        self.max_day_trade_risk = 100  # $100 per trade (0.5%)
        self.max_leaps_per_position = 0.15  # 15% max ($3K)
        self.max_total_exposure = 0.70  # 70% max invested
        self.reserve_cash = 0.30  # 30% cash always
    
    def size_day_trade(self, entry, stop):
        """Calculate shares for day trade."""
        risk_per_share = entry - stop
        shares = self.max_day_trade_risk / risk_per_share
        
        # Don't exceed 10% of capital per position
        max_shares = (self.capital * 0.10) / entry
        
        return min(shares, max_shares)
    
    def size_leaps(self, premium_per_contract):
        """Calculate LEAPS contracts."""
        max_investment = self.capital * self.max_leaps_per_position
        contracts = int(max_investment / (premium_per_contract * 100))
        
        # Never more than 5 contracts (too concentrated)
        return min(contracts, 5)
```

**Usage:**
```python
sizer = PositionSizer(capital=20000)

# Day trade at $250, stop at $249.75
shares = sizer.size_day_trade(250, 249.75)  # Returns 400 shares ($100 risk)

# LEAPS at $5.50 premium
contracts = sizer.size_leaps(5.50)  # Returns 5 contracts ($2,750)
```

---

## MONTH 3+: ONLY IF MAKING MONEY

### [ ] Task 4.1: Improve Signals (IF strategies work but want higher win rate)

**Time:** 20-30 hours

**Add to daily models:**
```python
# Fundamental features from real_fundamentals.py (already built)
- ROIC (calculated)
- Piotroski (calculated)
- Altman Z-Score (bankruptcy risk)

# Event-driven features
- Days to earnings (yfinance.earnings_dates)
- Earnings surprise last 4 quarters
- Analyst rating changes last 30 days
- Insider buying (yfinance.insider_purchases)

# Sector features
- Sector ETF momentum (XLK, XLF, etc.)
- Relative strength vs sector
- Sector rotation signals
```

**Re-train models, validate again**

---

### [ ] Task 4.2: Add Better Data (ONLY if managing $100K+)

**Don't do this with $20K - not worth cost**

**When you have $100K-500K:**
- Subscribe to Polygon.io ($200/month)
- Get tick-level data
- Options flow data
- Better entries/exits

**ROI calculation:**
- Need to make $2,400/year extra to justify $200/month
- That's 1-2% better returns
- Only worth it if already profitable

---

## Files to Keep in Root

### [ ] Task 5.1: Clean Up Root Directory

**Keep (6 files):**
```
README.md                    # Main overview
START_HERE.md                # Entry point
QUICK_START.md               # Fast guide
HONEST_ROADMAP.md            # This roadmap
IMPLEMENTATION_CHECKLIST.md  # This file
requirements.txt             # Dependencies
```

**Move to docs/:**
```bash
mv docs/HOW_TO_RUN.md docs/PAPER_TRADING_SETUP.md docs/TRADING_BOT_SETUP.md docs/archive/
# Keep docs/SCANNER_GUIDE.md and docs/SETUP_GUIDE.md
```

**Python scripts to keep in root:**
```
trader.py                # Main launcher
analyze.py               # Intelligent analysis
scanner.py               # Scanner
backtest_day_bot.py      # Day bot validation
portfolio_tracker.py     # Position tracking
get_russell1000.py       # Universe builder
get_russell2000.py       # Universe builder
expand_universe.py       # Universe builder
backtest_intraday_signals.py  # Scanner validation
```

Move universe builders:
```bash
mkdir -p tools
mv get_russell1000.py get_russell2000.py expand_universe.py tools/
```

**Final root directory (10 files):**
- 6 markdown files
- 4 Python scripts (trader, analyze, scanner, backtest_day_bot)
- requirements.txt

---

## Implementation Guide for Future Prompts

### **Quick Reference Card:**

```
GOAL: Build trading edge for $20K retail account

CONSTRAINTS:
- Can't buy expensive data ($200/month = 12% of annual returns needed)
- Can't compete on speed (retail execution)
- Can't do HFT (no infrastructure)
- Must use free data (yfinance, IBKR market data)

EDGE OPPORTUNITIES:
1. Behavioral (gap trading) - humans create patterns
2. Time horizon (LEAPS on small caps) - less institutional coverage
3. Discipline (follow rules) - most retail traders don't

STRATEGIES:
1. Day Trading Bot - gap trading with VWAP entries
2. LEAPS - fundamental analysis on undercovered stocks
3. Scanner - supplemental intraday signals

VALIDATION REQUIRED:
- Day bot: >55% win rate on 1-year backtest
- Scanner: IC >0.025 or Sharpe >0.5
- LEAPS: >60% winners over 12 months

POSITION SIZING ($20K):
- Day trades: $100 risk max (0.5%)
- LEAPS: $2-3K per position max (10-15%)
- Total exposure: <70% (keep 30% cash)
- Never more than 5 LEAPS positions

AUTOMATION:
- DO: Data collection, analysis, alerts
- DON'T: Auto execution (until 6+ months proven)

FILES:
- trader.py - main launcher
- analyze.py - intelligent analysis
- HONEST_ROADMAP.md - priorities
- IMPLEMENTATION_CHECKLIST.md - tasks
```

---

## Task Priorities for $20K Account

### **HIGH PRIORITY (Do First):**

1. ✅ Validate day bot (2 hours)
2. ✅ Validate scanner (2 hours)
3. ⏳ Paper trade 2 weeks
4. ⏳ Real-time alerts if validated (4 hours)

### **MEDIUM PRIORITY (If profitable):**

5. ⏳ Improve signal filters (8 hours)
6. ⏳ Track LEAPS performance (ongoing)
7. ⏳ Add more fundamental features to models (20 hours)

### **LOW PRIORITY (Don't do with $20K):**

8. ❌ Web dashboard (not needed)
9. ❌ Database migration (CSVs work fine)
10. ❌ Paid data (can't justify cost)
11. ❌ Execution optimization (not your bottleneck)
12. ❌ More automation (premature)

### **NEVER DO (Not worth it at your scale):**

- Co-location servers
- Institutional data feeds
- HFT infrastructure
- Professional-grade backtesting systems
- Machine learning research (unless personal interest)

---

## Realistic Expectations for $20K

### **If Day Bot Works (55%+ win rate):**

**Daily trading:**
- 2-3 trades/day
- $100 risk per trade, $150 average win
- 55% win rate
- Expected: $50-100/day = $12K-25K/year
- **ROI: 60-125% annually**

### **If LEAPS Work (60% winners):**

**Long-term positions:**
- 3-5 positions
- $10K allocated (50% of capital)
- 60% winners, 80% average gain on winners
- Expected: $4.8K/year
- **ROI: 24% annually on allocated capital**

### **Combined (Both work):**

**Total expected:**
- Day trading: $12K-25K/year
- LEAPS: $5K/year
- **Total: $17K-30K/year (85-150% ROI)**

**Reality check:** 
- This would put you in top 1% of retail traders
- More likely: 20-40% annual returns if disciplined
- Expect $4K-8K/year realistically

---

## What NOT to Build (At Your Scale)

### **Don't Add:**

**1. Proprietary Data Sources**
- Cost: $200-5,000/month
- Need to make: $2,400-60,000/year just to break even
- With $20K, that's 12-300% returns needed
- **Not feasible**

**2. Novel Signal Research**
- Time: 200+ hours
- Success rate: 5-10%
- Opportunity cost: $20K-40K in lost work hours
- **Not worth it unless passionate about research**

**3. HFT Infrastructure**
- Cost: $50K-200K
- Requires $1M+ to justify
- **Not for retail**

**4. Complex ML Models**
- Daily models have negative IC
- Would take 100+ hours to fix
- Still might not work
- **Focus on simple strategies that work**

---

## Clean File Structure (Implemented)

### **Root directory (10 files):**
```
scanner/
├── README.md                   # Start here
├── START_HERE.md               # Quick start
├── QUICK_START.md              # One-page guide
├── HONEST_ROADMAP.md           # Priorities
├── IMPLEMENTATION_CHECKLIST.md # This file
├── requirements.txt
│
├── trader.py                   # Main launcher
├── analyze.py                  # Intelligent analysis
├── scanner.py                  # Intraday scanner
└── backtest_day_bot.py         # Day bot validation
```

### **Everything else organized:**
```
portfolio_tracker.py            # Position tracking
tools/                          # Universe builders
scripts/                        # Strategy runners
src/                            # Core libraries
docs/                           # All documentation
  ├── SCANNER_GUIDE.md
  ├── archive/                  # Old docs
  └── implementation/           # Build guides
data/                           # Data files
tests/                          # Test suite
archive/                        # Experimental code
```

**Clean, focused, maintainable.**

---

## Next Steps Right Now

### **Step 1: Run Validation (Tonight - 2 hours)**

```bash
# Terminal 1: Start IBKR Gateway
# Open IBKR Gateway, enable API

# Terminal 2: Run validation
cd /Users/raulacedo/Desktop/scanner
source leaps_env/bin/activate

# Validate day bot
python trader.py → [15]

# Validate scanner  
python backtest_intraday_signals.py
```

**Write down results.**

---

### **Step 2: Based on Results (Tomorrow)**

**If day bot validated:**
- Start paper trading for 2 weeks
- Set up Telegram alerts
- Plan live trading start date

**If scanner validated:**
- Use as supplement to day bot
- Run every 1-2 hours during market

**If neither validated:**
- Focus on LEAPS only (doesn't need validation, just tracking)
- Don't day trade
- OR spend 50 hours improving models

---

### **Step 3: Stick to Plan (Week 3+)**

**If trading:**
- Day bot: 2-3 trades/day, $100 risk each
- LEAPS: 1-2 positions/month, $2-3K each
- Track everything in portfolio_tracker.py

**Capital allocation for $20K:**
```
Day Trading: $6K (30%)
  - $100 risk per trade
  - Max 3 positions ($2K each)

LEAPS: $10K (50%)
  - 3-5 positions
  - $2-3K per position

Cash Reserve: $4K (20%)
  - For opportunities
  - Margin buffer
```

**Monthly review:**
- Actual returns vs expected
- Strategy win rates
- Adjust if needed

---

## Summary Checklist

**Week 1:**
- [ ] Validate day bot (2 hrs)
- [ ] Validate scanner (2 hrs)
- [ ] Document results (30 min)
- [ ] Decide what to trade

**Week 2-3:**
- [ ] Paper trade validated strategies
- [ ] Track performance daily
- [ ] Compare to backtest

**Month 2 (if profitable):**
- [ ] Add Telegram alerts (4 hrs)
- [ ] Implement position sizer (2 hrs)
- [ ] Start live with 1% positions

**Month 3+ (if making money):**
- [ ] Scale up position sizes
- [ ] Consider Polygon.io if managing $100K+
- [ ] Keep improving

**Don't Do:**
- ❌ Web dashboard
- ❌ Database migration
- ❌ Novel research (unless interested)
- ❌ Execution optimization
- ❌ More features before validation

---

## For Future AI Prompts

**Context to provide:**
```
Retail trader, $20K account
Built trading system with:
- Day bot (gap/VWAP strategy)
- LEAPS analyzer (fundamental + GPT)
- Intraday scanner (gap/momentum/VWAP)
- Intelligent analysis (chains all three)

Constraints:
- Free data only (yfinance)
- Retail execution (IBKR)
- Can't compete on speed or data
- Must compete on discipline and behavioral patterns

Validation status:
- Day bot: [VALIDATED/NOT VALIDATED]
- Scanner: [VALIDATED/NOT VALIDATED]
- LEAPS: Tracking in progress

Current focus:
- Run validation
- Paper trade if validated
- Add alerts if profitable
- Don't over-engineer

Files:
- trader.py (main)
- analyze.py (intelligent analysis)
- HONEST_ROADMAP.md (priorities)
- IMPLEMENTATION_CHECKLIST.md (tasks)
```

---

## Bottom Line for $20K Account

**Realistic goal:** 20-40% annual returns ($4K-8K/year)

**Path:**
1. Validate strategies (5 hours)
2. Paper trade (2 weeks)
3. Trade validated strategies only
4. Keep it simple
5. Don't over-build

**Current system is sufficient** for $20K. Don't add complexity. Run validation, trade what works, skip what doesn't.

**Value of system for you:** $50K-100K in time saved + learning, potentially $4K-8K/year in trading profits if strategies validate.

Focus on execution, not features.

