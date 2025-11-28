# Trading Research & Signal System

A personal trading assistant that scans the market daily and sends you actionable trade signals via Telegram. Built for people who want an edge but don't have time to watch screens all day.

---

## What This System Does

Every morning at 8:30 AM (before US market opens), you receive a Telegram message like this:

```
🟢 GREEN | SPY $679.68 (+0.7%) | VIX 13.5
Market breadth: OK (62% above SMA50)
Aggressive longs

[A] BUY NOW: Exact Sciences (EXAS)
$101.45 | 5D: +0.8%
Entry $101.45 | Stop $95.43 | Target $113.48
R:R 1:2.5 | 83 sh ($500 risk)
Breakout + Vol surge (6.2x)

[B] BUY PULLBACK: DigitalOcean (DOCN)
$44.86 | 5D: +2.1%
Entry $44.86 | Stop $40.67 | Target $52.20
R:R 1:1.8 | 119 sh ($499 risk)
Pullback to SMA20, uptrend intact
```

**In plain English:** The system tells you:
- Is today a good day to buy stocks? (GREEN = yes, RED = no)
- Is the broader market healthy? (breadth check)
- Which stocks look promising, graded by quality [A], [B], [C]
- Exactly where to buy, where to set your stop loss, and where to take profit
- How many shares to buy if you want to risk $500

### What's NEW in this version

| Feature | What it does |
|---------|--------------|
| **Signal Grading** | Signals rated A/B/C. Grade A = highest confidence setups |
| **Market Breadth** | Won't signal in weak markets (<40% stocks above SMA50) |
| **Earnings Blackout** | Won't signal stocks within 5 days of earnings |
| **Extension Filter** | Won't chase stocks that already ran 20%+ in 5 days |
| **Performance Tracking** | Track if past signals actually worked |
| **Position Management** | Track your open positions and risk exposure |
| **Config System** | All thresholds in one YAML file - tune without code changes |

---

## Key Concepts Explained

### What is "Regime"?

The market has moods. Sometimes it's happy (going up), sometimes it's scared (going down). We call this the "regime":

| Regime | What it means | What to do |
|--------|---------------|------------|
| 🟢 GREEN | Market is healthy, stocks going up | Buy with confidence |
| 🟡 YELLOW | Market is uncertain, some fear | Be selective, smaller positions |
| 🔴 RED | Market is scared, stocks falling | Don't buy, protect what you have |

**How we determine regime:**
- SPY (the S&P 500 ETF) price vs its 50-day average
- VIX (the "fear index") level - below 20 is calm, above 30 is panic

### What is "Entry", "Stop", and "Target"?

When you buy a stock, you need a plan:

- **Entry** = The price where you buy
- **Stop** = The price where you sell if it goes against you (limits your loss)
- **Target** = The price where you sell if it goes your way (takes your profit)

**Example:**
```
Entry $100 | Stop $95 | Target $115
```
- You buy at $100
- If it drops to $95, you sell (you lose $5 per share)
- If it rises to $115, you sell (you make $15 per share)

### What is "R:R" (Risk/Reward)?

R:R tells you if a trade is worth taking.

```
R:R 1:2.0
```

This means: For every $1 you risk, you could make $2.

- **1:1** = Break even trade (not great)
- **1:2** = Good trade (you risk $1 to make $2)
- **1:3** = Excellent trade (you risk $1 to make $3)

**Rule of thumb:** Only take trades with R:R of 1:2 or better.

### What is "Volume Surge"?

When a stock suddenly has way more trading activity than usual, it often means big investors (institutions, hedge funds) are buying. This is a good sign.

```
Vol surge (6.2x)
```

This means the stock is trading 6.2 times more than its average. That's huge - someone big is buying.

### What is a "Breakout" vs "Pullback"?

Two types of setups:

**BREAKOUT:**
- Stock is hitting new highs
- Momentum is strong
- Risk: You might be buying at the top

**PULLBACK:**
- Stock was going up, then dipped a bit
- You're buying "on sale"
- Risk: The dip might continue

### What is Signal Grading [A]/[B]/[C]?

Not all signals are equal. The system grades each one:

| Grade | Meaning | Criteria |
|-------|---------|----------|
| **[A]** | Highest confidence | R:R >= 2.5, Volume >= 2x, Extension <= 5% |
| **[B]** | Good setup | R:R >= 1.5, Volume >= 1.5x, Extension <= 10% |
| **[C]** | Marginal | Passes filters but lower quality |

**Focus on Grade A signals first.** They have the best risk/reward and aren't chasing.

### What is Market Breadth?

Breadth measures market health by checking how many stocks are in uptrends:

- **Strong (>60%)**: Most stocks going up - full size longs OK
- **Neutral (40-60%)**: Mixed market - be selective
- **Weak (<40%)**: Most stocks falling - **no signals generated**

The system won't send you signals in a weak market. This prevents buying into a falling market.

### What is the Earnings Blackout?

Stocks move unpredictably around earnings. The system will NOT signal any stock within 5 days of its earnings date. This avoids binary gambles.

---

## How to Use This System

### Step 1: Get Your Daily Alert

Every morning at 8:30 AM ET, you'll receive a Telegram message with:
- Market regime (GREEN/YELLOW/RED)
- Top 5 trade setups with exact entry/stop/target

### Step 2: Decide What to Do

**If regime is RED:**
- Don't buy anything new
- Consider selling weak positions

**If regime is GREEN or YELLOW:**
- Look at the trade signals
- Pick 1-2 that interest you
- Check if the entry price still makes sense (market moves fast)

### Step 3: Place Your Trade

In your broker (Robinhood, Schwab, Fidelity, etc.):

1. **Buy** the number of shares shown
2. **Set a stop-loss order** at the Stop price
3. **Set a limit sell order** at the Target price (optional)

**Example from the alert:**
```
BUY NOW: Exact Sciences (EXAS)
Entry $101.45 | Stop $95.43 | Target $113.48
83 sh ($500 risk)
```

In your broker:
- Buy 83 shares of EXAS at market price (~$101)
- Set stop-loss at $95.43
- Optionally set limit sell at $113.48

### Step 4: Manage Your Position

- If stop hits → You're out, small loss, move on
- If target hits → You're out, nice profit
- If neither → Check the next day's alert for updates

---

## Running Locally (Optional)

If you want to do deeper research beyond the daily alert:

### One-Time Setup

```bash
# 1. Open Terminal (Mac) or Command Prompt (Windows)

# 2. Navigate to the project folder
cd /path/to/scanner

# 3. Create a virtual environment (isolates dependencies)
python3 -m venv .venv

# 4. Activate it
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate     # Windows

# 5. Install required packages
pip install -r requirements.txt
```

### Daily Use

```bash
# Activate environment (every time you open terminal)
source .venv/bin/activate

# Launch the menu
python launcher.py
```

You'll see:

```
============================================================
   🚀  TRADING SYSTEM & RESEARCH LAB  🚀
============================================================

MAIN MENU:
   1. 📊  Open Dashboard (View Results)
   2. 🔎  Analyze a Stock (Deep Dive)
   3. 📡  Screen the Market (Find Ideas)
   4. 🧪  Run Backtest (Validate Strategy)
   5. 🏥  Portfolio Health Check
   6. ☕  Daily Briefing (One-Click Research)
   7. 🔧  Advanced Tools
   8. 🔭  Universe Scan (Find Edge)
   9. 📈  Performance Check (Did Signals Work?)
   0. ❌  Exit

Select an option:
```

### Menu Options Explained

**Option 2: Analyze a Stock**
- Enter any ticker (e.g., NVDA)
- Get fundamental analysis, technical levels, and trade setup

**Option 6: Daily Briefing**
- Same as the Telegram alert, but run locally
- Useful if you want to re-check during the day

**Option 8: Universe Scan**
- Full scan of 150+ stocks
- Takes 2-3 minutes
- Shows top opportunities with edge scores

**Option 9: Performance Check**
- See if recent signals actually worked
- Shows win rate and P&L for signals from 5 and 10 days ago
- Use this to validate the system is profitable

**Option 7: Advanced Tools**
- Position Dashboard (track open positions)
- Add/Close Position (log your trades)
- Watchlist management
- Options Greeks analysis

---

## Understanding the Scan Results

When you run a Universe Scan, you'll see something like:

```
EXAS - Exact Sciences Corporation
Price: $101.45 | MCap: $19.3B
Edge Score: 95.2/100

5D: +0.8% | 20D: +15.3%
Volume: +516% vs avg
Setup: BREAKOUT

Support: $62.55 | Resistance: $101.87
Why: Heavy accumulation + Strong momentum + Outperforming SPY + Breaking out
```

**What each part means:**

| Field | Meaning |
|-------|---------|
| **Edge Score** | How good the setup looks (0-100). Higher = better. |
| **5D / 20D** | Price change over 5 days / 20 days |
| **Volume** | How much more trading than usual |
| **Setup** | Type of opportunity (BREAKOUT, PULLBACK, CONSOLIDATION) |
| **Support** | Price level where buyers tend to step in |
| **Resistance** | Price level where sellers tend to appear |
| **Why** | Plain English explanation of why this stock looks good |

---

## Position Management

Track your trades with the built-in position manager:

```bash
python launcher.py
# Select 7 -> Advanced Tools -> 7 (Position Dashboard)
```

**What you can do:**
- Log positions with entry/stop/target
- See live P&L (fetches current prices)
- Get alerts when near stop or target
- Check sector concentration (warns if >25% in one sector)
- Track closed trade performance

**Example Dashboard:**
```
POSITION DASHBOARD
============================================================

⚠️  ALERTS:
   • CONCENTRATION: Technology is 45% of account (>25%)
   • NEAR STOP: HOOD only 1.5% above stop

ACCOUNT SUMMARY ($100,000 base):
   Positions: 3
   Total Value: $45,000 (45% deployed)
   Total Risk: $2,100 (2.1% of account)
   Unrealized P&L: +$1,250

OPEN POSITIONS:
------------------------------------------------------------
NVDA (50 shares)
   Entry: $450 | Current: $475 | P&L: +5.6%
   Stop: $430 (-9.5%) | Target: $520 (9.5% away)
```

---

## Customizing Thresholds

All scanner parameters are in one file: `configs/scanner_config.yaml`

**Change without touching code:**

```yaml
# Extension Filter
extension:
  hard_reject_5d: 20     # Reject if 5D move > 20%

# Market Regime  
regime:
  min_breadth: 40        # Min % above SMA50 for healthy market

# Earnings
earnings:
  blackout_days: 5       # Reject signals within 5 days of earnings

# Signal Grading
grading:
  grade_a_min_rr: 2.5    # Min R:R for Grade A
```

---

## Risk Management Rules

**These are non-negotiable if you want to survive:**

### Rule 1: Never Risk More Than 1-2% Per Trade

If your account is $10,000:
- Max risk per trade = $100-200
- The alerts assume $500 risk (adjust the share count proportionally)

### Rule 2: Always Use Stop Losses

The stop price in the alert is there for a reason. Set it. Don't move it lower hoping it will recover.

### Rule 3: Don't Chase

If the alert says "Entry $100" but the stock is now at $108:
- You missed it
- Don't buy at $108
- Wait for the next setup or a pullback

### Rule 4: Respect the Regime

- RED regime = No new buys, period
- Even the best stock setup will fail if the whole market is crashing

### Rule 5: Start Small

- Paper trade (fake money) for 2-4 weeks first
- Then start with small positions
- Increase size only after consistent success

---

## Frequently Asked Questions

### "Why did a trade hit my stop and then go back up?"

This happens. Stops are not perfect. They're designed to limit big losses, not avoid all losses. If your stop is hit, accept it and move on.

### "Should I buy all 5 stocks in the alert?"

No. Pick 1-2 that you understand or like. Diversification across 5 random stocks doesn't reduce risk - it spreads it.

### "What if I miss the morning alert?"

You can run the scan locally anytime:
```bash
python launcher.py
# Choose Option 8: Universe Scan
```

### "How do I know if a stock is too expensive?"

Price doesn't matter. A $500 stock isn't "expensive" and a $5 stock isn't "cheap." What matters is:
- Is it going up? (momentum)
- Is the risk/reward good? (R:R)
- Can you afford the position size for your risk tolerance?

### "What's the difference between this and just buying SPY?"

SPY (S&P 500 ETF) is safer and simpler. This system is for people who:
- Want to potentially beat the market
- Are willing to do more work
- Accept higher risk for higher reward

If you're unsure, just buy SPY and chill.

### "Do I need to watch the market all day?"

No. The system is designed for:
1. Check alert in the morning (5 minutes)
2. Place trades if any look good (5 minutes)
3. Go live your life
4. Check positions at end of day (5 minutes)

### "What if the Telegram alert doesn't come?"

Check GitHub Actions for errors, or run locally:
```bash
python launcher.py
# Choose Option 6: Daily Briefing
```

---

## Technical Setup (For Telegram Alerts)

### Creating Your Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Save the **token** (looks like `123456789:ABCdefGHI...`)

### Getting Your Chat ID

1. Start a chat with your new bot
2. Send any message to it
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` - that number is your Chat ID

### Setting Up GitHub Actions

1. Go to your GitHub repo → Settings → Secrets → Actions
2. Add two secrets:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat ID

The workflow runs automatically at 8:30 AM ET on weekdays.

---

## Glossary

| Term | Definition |
|------|------------|
| **ATR** | Average True Range - how much a stock typically moves in a day |
| **Breadth** | Percentage of stocks above their moving average (market health) |
| **Breakout** | Stock moving above its recent high |
| **Entry** | The price at which you buy |
| **Extension** | How much a stock has already run up (high = chasing) |
| **Grade A/B/C** | Signal quality rating based on R:R, volume, extension |
| **MCap** | Market Capitalization - total value of a company |
| **Momentum** | The tendency of a stock to keep moving in its current direction |
| **Pullback** | A temporary dip in an uptrend |
| **R:R** | Risk to Reward ratio |
| **Regime** | Overall market condition (bullish, bearish, neutral) |
| **Resistance** | Price level where a stock tends to stop rising |
| **SMA** | Simple Moving Average - average price over X days |
| **SPY** | ETF that tracks the S&P 500 index |
| **Stop Loss** | An order to sell if price drops to a certain level |
| **Support** | Price level where a stock tends to stop falling |
| **Target** | The price at which you plan to take profit |
| **VIX** | Volatility Index - measures market fear |
| **Volume** | Number of shares traded |
| **Volume Surge** | Trading activity significantly above average (institutional buying) |

---

## Disclaimer

This system is for educational and research purposes. It does not constitute financial advice. Trading stocks involves risk of loss. Past performance does not guarantee future results. Always do your own research and consider consulting a financial advisor.

---

## Support

If something breaks or you have questions:
1. Check the GitHub Issues
2. Run locally to debug
3. The code is yours - modify as needed
