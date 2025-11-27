# Intelligent Cascading Analysis

## What You Asked For

You wanted the systems to work **sequentially** - if LEAPS finds a fundamentally strong stock, automatically check it with the scanner and day bot to find the best strategy.

**Now you have it.**

---

## How It Works

### One Command

```bash
python analyze.py NVDA TSLA PLTR
```

Or through the menu:
```bash
python trader.py
# Select: [1] Intelligent Analysis
# Enter: NVDA,TSLA,PLTR
```

### What Happens (Automatically)

```
STEP 1: FUNDAMENTAL ANALYSIS (LEAPS System)
├─ Runs complete LEAPS analysis
├─ Scores fundamentals out of 100
├─ Checks growth, margins, catalysts
└─ Determines: Strong (70+) | Moderate (50-69) | Weak (<50)

STEP 2: TECHNICAL ANALYSIS (Scanner)
├─ Checks for gap opportunities
├─ Looks for momentum breakouts
├─ Tests VWAP reversion setups
└─ Determines: Strong signal | Weak signal | No signal

STEP 3: DAY TRADING EVALUATION (Day Bot Criteria)
├─ Checks if meets gap requirements (1%+)
├─ Verifies technical setup exists
├─ Confirms news catalyst present
└─ Determines: Suitable | Not suitable

STEP 4: COMBINED RECOMMENDATION
└─ Tells you exactly what to do
```

---

## Example Output

```bash
python analyze.py NVDA
```

### Result:

```
================================================================================
STEP 1/3: FUNDAMENTAL ANALYSIS (LEAPS System)
================================================================================

✓ Fundamental Score: 82/100
  Recommendation: STRONG BUY
  12-Month Target: $575.00

================================================================================
STEP 2/3: TECHNICAL ANALYSIS (Intraday Scanner)
================================================================================

✓ Technical Signal: GAP_CONTINUATION
  Confidence: 75.3/100
  Price: $450.25

================================================================================
STEP 3/3: DAY TRADING EVALUATION
================================================================================

Day Trading Suitability:
  ✓ Gap: +2.5%
  ✓ Technical signal present
  ✓ Strong fundamentals (score: 82)

✓✓✓ SUITABLE FOR DAY TRADING

================================================================================
COMBINED RECOMMENDATION: NVDA
================================================================================

🎯 BEST SETUP: Strong on both fundamental and technical
   Recommended: Day trade for quick profit, hold LEAPS for long-term

RECOMMENDED STRATEGIES:

1. LEAPS (12-24 months)
   Reason: Strong fundamentals (score: 82/100)
   Action: Run: python scripts/run_leaps_analysis.py NVDA

2. Day Trading (30 minutes - 4 hours)
   Reason: Gap + technical setup
   Action: Add to day bot watchlist, monitor for VWAP entry

Analysis saved to: data/output/analysis_NVDA_20251009_143052.json
```

---

## The Four Outcomes

### 1. Strong Fundamental + Strong Technical 🎯

**Example:** Stock gaps up 3% on earnings beat, strong growth fundamentals

**What it says:**
```
🎯 BEST SETUP: Strong on both fundamental and technical
   Recommended: Day trade for quick profit, hold LEAPS for long-term

RECOMMENDED STRATEGIES:
1. Day Trading - Entry today on VWAP test
2. LEAPS - Jan 2026 calls for 12-18 month hold
```

**What you do:**
- Morning: Add to day bot watchlist
- Market open: Bot trades the gap automatically
- Evening: Run full LEAPS analysis, enter long-term position
- **Result:** Quick day trade profit + long-term wealth building

---

### 2. Strong Fundamental + Weak Technical 📊

**Example:** Great company but stock is flat, no gap or momentum

**What it says:**
```
📊 PATIENT SETUP: Strong fundamentals, weak technicals
   Recommended: Wait for technical entry, or enter LEAPS now

RECOMMENDED STRATEGIES:
1. LEAPS - Jan 2026 calls (fundamentals strong)
```

**What you do:**
- Skip day trading (no setup)
- Run LEAPS analysis
- Enter long-term position
- Set alerts for future gap opportunities
- **Result:** Long-term position, wait for day trade setup

---

### 3. Weak Fundamental + Strong Technical ⚡

**Example:** Stock gaps on news but poor fundamentals (unprofitable, declining growth)

**What it says:**
```
⚡ QUICK TRADE: Weak fundamentals, strong technicals
   Recommended: Day trade only, no long-term position

RECOMMENDED STRATEGIES:
1. Day Trading - Entry today, exit by close
```

**What you do:**
- Morning: Add to day bot watchlist
- Market open: Trade the gap
- **Exit before close** - don't hold overnight
- Skip LEAPS (fundamentals weak)
- **Result:** Quick profit, no long-term exposure

---

### 4. Weak Fundamental + Weak Technical ⏸

**Example:** Poor company, no movement, no catalyst

**What it says:**
```
⏸ PASS: Neither fundamental nor technical strength
   Recommended: Skip this ticker

NO STRATEGIES RECOMMENDED - SKIP
```

**What you do:**
- Nothing. Move on to next ticker.
- **Result:** Capital preserved for better opportunities

---

## Batch Analysis

Analyze multiple stocks at once:

```bash
python analyze.py NVDA TSLA PLTR COIN AMD
```

You get:
- Individual analysis for each
- Summary table at the end:

```
================================================================================
BATCH ANALYSIS SUMMARY
================================================================================

Ticker  Fund Score  Tech Signal  Day Trade  Strategies
NVDA    82/100      ✓            ✓          2
TSLA    75/100      ✓            ✓          2
PLTR    68/100      ✗            ✗          1
COIN    45/100      ✓            ✓          1
AMD     71/100      ✓            ✓          2
```

**Quick scan:** See which stocks have both fundamental and technical strength.

---

## How Systems Chain Together

### Uses Existing Scripts (No Duplication)

```python
# Fundamental analysis
from leaps.complete_leaps_system import CompleteLEAPSSystem
leaps = CompleteLEAPSSystem()
result = leaps.analyze_ticker(ticker)

# Technical analysis  
from alpha_lab.intraday_signals import IntradaySignalGenerator
scanner = IntradaySignalGenerator(ib)
gap_signal = scanner.detect_opening_gap(ticker)

# Day bot criteria (from CONFIG in day_trading_bot.py)
suitable = has_gap and has_signal and has_catalyst
```

**Smart:** Reuses all your existing code, just orchestrates it.

---

## Integration with Workflows

### Morning Routine

```bash
python trader.py → [5] Morning Routine
```

After morning routine shows you gap stocks:
```bash
python analyze.py NVDA TSLA AMD
```

Get combined analysis to decide which to trade.

---

### Evening Research

```bash
python trader.py → [7] Evening Analysis
```

After evening analysis shows after-hours movers:
```bash
python analyze.py COIN PLTR HOOD
```

Find which movers have strong fundamentals for LEAPS.

---

### Weekend Deep Dive

```bash
# Get week's biggest movers
cat data/output/after_hours_signals_*.csv

# Analyze top 10
python analyze.py NVDA TSLA PLTR COIN AMD HOOD SOFI RIVN LCID MSTR
```

Build watchlist for next week: day trades + LEAPS positions.

---

## Practical Examples

### Example 1: Earnings Play

**Morning:** Stock gaps 4% on earnings beat

```bash
python analyze.py XYZ
```

**Result:**
```
Strong fundamentals (score: 78)
Strong technical (gap: 4%, signal: GAP_CONTINUATION)
Suitable for day trading

STRATEGIES:
1. Day Trade - Enter on VWAP test
2. LEAPS - Strong quarter, enter 18-month calls
```

**Action:**
- 9:30 AM: Day bot trades the gap → $400 profit
- 5:00 PM: Enter LEAPS position for long-term → Hold for 50%+ gain

**Result:** Quick profit + long-term position

---

### Example 2: Weak Company, Big Move

**Morning:** Stock gaps 5% on speculation, no fundamentals

```bash
python analyze.py ABC
```

**Result:**
```
Weak fundamentals (score: 42)
Strong technical (gap: 5%, high volume)
Suitable for day trading

STRATEGIES:
1. Day Trade ONLY - Exit by close
```

**Action:**
- 9:30 AM: Day bot trades the gap → $350 profit
- 3:45 PM: Exit completely, don't hold
- Skip LEAPS (fundamentals weak)

**Result:** Quick profit, no long-term risk

---

### Example 3: Great Company, No Setup

**Morning:** Solid company but flat price action

```bash
python analyze.py DEF
```

**Result:**
```
Strong fundamentals (score: 81)
Weak technical (no gap, no momentum)
Not suitable for day trading

STRATEGIES:
1. LEAPS - Enter Jan 2026 calls
```

**Action:**
- Skip day trading (no setup)
- Evening: Run full LEAPS analysis
- Enter long-term position
- Set alerts for future gap

**Result:** Long-term position, wait for day trade opportunity

---

## Command Reference

**Single ticker:**
```bash
python analyze.py NVDA
```

**Multiple tickers:**
```bash
python analyze.py NVDA TSLA PLTR
```

**Without IBKR (basic mode):**
```bash
python analyze.py --no-ibkr NVDA
```

**Through menu:**
```bash
python trader.py
[1] Intelligent Analysis
Enter: NVDA,TSLA,PLTR
```

---

## Output Files

Each analysis saved to:
```
data/output/analysis_TICKER_timestamp.json
```

Contains complete results for later review.

---

## Benefits

### 1. No Guesswork

Don't wonder "should I day trade this or hold long-term?"
**The system tells you exactly what to do.**

### 2. Uses All Your Tools

Chains together all three systems automatically:
- LEAPS for fundamentals
- Scanner for technicals  
- Day bot criteria for suitability

### 3. Objective Decisions

No emotional trading. Clear criteria:
- Fund score > 70 = LEAPS
- Gap + signal = day trade
- Both = do both
- Neither = skip

### 4. Fast Screening

Analyze 10 stocks in 5 minutes, see which have:
- Strong fundamentals (LEAPS candidates)
- Strong technicals (day trade setups)
- Both (best opportunities)

---

## Bottom Line

**You asked:** "Can the LEAPS system automatically check if the stock is technically good for day trading?"

**You got:** One command that runs all three systems sequentially and tells you exactly what strategy to use.

```bash
python analyze.py NVDA
```

Gets you:
- Fundamental score (LEAPS)
- Technical signals (Scanner)
- Day trade suitability (Bot criteria)
- **Combined recommendation**

No more navigating between scripts. One analysis, complete picture, clear action.

**Start here:**
```bash
python trader.py → [1] Intelligent Analysis
```

Enter any ticker, get the complete picture.

