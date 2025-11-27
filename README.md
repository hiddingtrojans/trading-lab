# 🚀 Institutional-Grade Trading Lab

**A professional quantitative research system designed for retail traders.**

This system bridges the gap between "guessing" and "knowing". It combines rigorous fundamental data, macro regime filtering, dark pool proxies, and robust backtesting into a single, user-friendly toolkit.

**Zero coding required.** Just run the launcher and follow the signals.

---

## 🏁 Getting Started (In 30 Seconds)

1.  **Open your terminal.**
2.  **Run the Control Center:**
    ```bash
    python launcher.py
    ```
3.  **Select a Tool from the Menu:**
    ```
       1. 📊  Open Dashboard (View Analysis & Trades)
       2. 🔎  Analyze a Stock (Deep Dive + Whale/Regime Check)
       3. 📡  Screen the Market (Find Growth/Momentum Ideas)
       4. 🧪  Run Backtest (Validate Strategy)
       5. 🏥  Portfolio Health Check (Risk & Correlation)
       6. ☕  Daily Briefing (One-Click Research)
       0. ❌  Exit
    ```

---

## 🧠 The "Pro" Trader's Workflow

Follow this routine to trade like a hedge fund, not a gambler.

### 🌅 Morning Routine (Pre-Market: 8:30 AM - 9:15 AM)

**Goal:** Understand the battlefield before the war starts.

1.  **Check the Market Regime (The "Traffic Light"):**
    *   **Action:** Run `launcher.py` -> **Option 2** -> Enter `SPY`.
    *   **Why:** Most strategies fail because the market environment is wrong.
    *   **Decision Tree:**
        *   🟢 **GREEN (Bullish):** Aggressive. Look for breakouts and LEAPS.
        *   🟡 **YELLOW (Choppy):** Caution. Reduce position size by 50%. Be picky.
        *   🔴 **RED (Bearish):** Danger. Cash is king. Do not open new long positions.

2.  **Get Your Daily Briefing:**
    *   **Action:** Run **Option 6 (Daily Briefing)**.
    *   **Why:** It scans 11 sectors and thousands of stocks in 60 seconds.
    *   **Output:** It will tell you which Sectors are **LEADING** (e.g., "Technology is Weak, Utilities are Strong") and give you 3 curated trade ideas.

### ☀️ Mid-Day (Execution: 9:45 AM - 11:00 AM)

**Goal:** Execute high-probability setups with precision.

1.  **Deep Dive Your Targets:**
    *   Take the stocks from your Briefing (or your own ideas) and run **Option 2 (Analyze)** on them.
    *   **The Checklist:**
        *   [ ] **Score > 75?** (Fundamentals are strong).
        *   [ ] **Whale Alert?** (Is "Smart Money" buying? Look for `ACCUMULATION` or `BULLISH FLOW`).
        *   [ ] **Sector Aligned?** (Is the stock in a LEADING sector?).
        *   [ ] **Volatility Cheap?** (Implied Move < Historical Move).

2.  **Check the "Tactical Plan":**
    *   At the bottom of the report, look for:
        ```
        📝 TACTICAL PLAN (Gap & Go)
           • Action: BUY_STOP
           • Entry: $150.50
           • Stop:  $148.20
        ```
    *   **Execution:** Enter these orders into your broker *exactly* as shown. Do not chase. If the price doesn't hit the Entry, **do not trade**.

### 🌙 Evening (Review: Post-Close)

**Goal:** Manage risk and prepare for tomorrow.

1.  **Portfolio Health Check:**
    *   **Action:** Run **Option 5**. Enter your current positions (e.g., `NVDA,AMD,TSM`).
    *   **Why:** You might accidentally be 100% exposed to one risk factor.
    *   **Warning Signs:**
        *   "High Correlation" (> 0.7): You basically own the same stock multiple times.
        *   "High Beta" (> 1.5): Your portfolio is very volatile.
    *   **Fix:** Sell one correlated loser and buy something stable (like `GLD` or `XLE`) to balance.

---

## 📚 Tool Guide: Understanding the Output

### 1. Market Regime (The Filter)
*   **What it calculates:** Trends (SMA 20/50/200), Fear (VIX), and Breadth (Sector participation).
*   **Rule:** Never buy when the Regime is RED. It's like sailing into a hurricane.

### 2. Whale Detector (The Invisible Hand)
*   **What it sees:** Institutional "footprints" hidden in the volume data.
*   **Signals:**
    *   **ACCUMULATION:** Price is flat, but volume is massive. Someone is quietly buying. **Bullish.**
    *   **DISTRIBUTION:** Price is flat/up, but volume is massive. Someone is selling into the rally. **Bearish.**
    *   **High Volume Node (HVN):** A price level where huge business was done. Acts as concrete support/resistance.

### 3. Sector Rotation (The Wind)
*   **Concept:** Money rotates. Tech rallies one month, Energy the next.
*   **Status:**
    *   **LEADING:** Strong trend + Strong momentum. Buy these.
    *   **WEAKENING:** Strong trend + Losing momentum. Take profits.
    *   **LAGGING:** Weak trend + Weak momentum. Avoid/Short.
    *   **IMPROVING:** Weak trend + Gaining momentum. Watch for reversals.

### 4. Earnings Volatility (The Edge)
*   **Concept:** Market makers price options based on expected moves.
*   **The Edge:**
    *   **Cheap Volatility:** Market expects a 2% move, but stock historically moves 8%. **Buy Options.**
    *   **Expensive Volatility:** Market expects 10%, stock moves 5%. **Sell Options / Wait.**

---

## ❓ FAQ for Beginners

**Q: The system says "Strategy Not Validated" in the backtest. Is it broken?**
A: **No!** It is working perfectly. It simulated trading that strategy over the last 30 days and found it lost money. **The system just saved you from a loss.** Do not trade strategies that fail the backtest.

**Q: Why do I see "No LEAPS available"?**
A: The stock might be too small, or the options market is illiquid (spreads too wide). The system protects you from buying options you can't sell later. Stick to liquid names.

**Q: Do I need Interactive Brokers (IBKR)?**
A: No. The system works great with **free Yahoo Finance data**. It automatically falls back to Yahoo if IBKR isn't connected.

**Q: What does "Buy Stop" mean in the Tactical Plan?**
A: It means "Buy ONLY if the price goes UP to this level." It confirms momentum. You place a *Stop Limit* or *Stop Market* order at that price.

**Q: I see "Whale Alert: BEARISH" but the Fundamental Score is 90. What do I do?**
A: **Wait.** Fundamentals tell you *what* to buy (Quality). Whales tell you *when* to buy (Timing). If Whales are selling, the price will likely drop cheaper. Let it fall, then buy when the Whale Alert flips to Neutral or Bullish.

---

## ⚠️ The 3 Golden Rules of Risk

1.  **The 2% Rule:** Never risk more than 2% of your account equity on a single trade. (Use the Stop Loss calculated by the Tactical Plan to size your position).
2.  **The Regime Rule:** If the Market Regime is RED, your only job is to protect capital. Sit on your hands.
3.  **The Validation Rule:** Never trade a strategy (like "Gap & Go") on a stock if the Backtest (Option 4) says it has a < 50% win rate.
