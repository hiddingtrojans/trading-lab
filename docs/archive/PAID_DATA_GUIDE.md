# Paid Data Services - Value Analysis for Retail

## Best Options (Ranked by Value)

### 1. IBKR Market Data Subscriptions (YOU ALREADY HAVE)
**Cost:** $0-4.50/month (waived with $30 commission/month)

**What You Get:**
- Real-time Level 1 (best bid/ask, last trade, volume)
- Historical intraday bars (1-min, 5-min, 15-min, 30-min)
- Market depth (Level 2) for $10/month
- Real-time scanner data

**Verdict:** START HERE. You're already paying for it.

---

### 2. Polygon.io - Starter Plan ($200/month)
**What You Get:**
- All US stocks real-time tick data
- Historical data back to 2004
- Options tick data
- Crypto, forex
- News and fundamentals
- Unlimited API calls
- Websockets for real-time streaming

**Value:** Best bang-for-buck if you need tick data. Clean API, reliable.

**When to buy:** After you've exhausted IBKR's data and proven your strategy works.

---

### 3. Alpha Vantage Premium ($50/month)
**What You Get:**
- Real-time quotes
- Intraday bars (1-min resolution)
- 1200 API calls/minute
- Technical indicators pre-calculated
- Fundamentals, earnings

**Value:** Good for testing/learning, but limited throughput.

**When to buy:** Never. IBKR data is better and cheaper.

---

### 4. Quandl/Nasdaq Data Link (Variable Pricing)
**Cost:** $50-500/month depending on dataset

**What You Get:**
- Alternative data (sentiment, economic indicators)
- Fundamentals from S&P Capital IQ
- Options data from OPRA

**Value:** Only if you need specific alt data.

---

### 5. Bloomberg Terminal ($2,000+/month)
**Verdict:** Don't even think about it unless you're managing $10M+.

---

## Recommendation: 3-Stage Approach

### Stage 1: IBKR Data Only ($0/month)
- Use real-time scanner + historical intraday bars
- Build and test intraday momentum strategies
- **If IC > 0.025, proceed to Stage 2**

### Stage 2: Add Polygon.io ($200/month)
- Get tick-level data for better entries/exits
- Access options flow for conviction signals
- Analyze microstructure patterns

### Stage 3: Add Sentiment Data ($100-300/month)
- Twitter/StockTwits sentiment (via RapidAPI)
- News sentiment (via MarketPsych or RavenPack lite)

---

## Acceptable Performance Thresholds

### For Daily Signals (What We Tried)
- Need IC > 0.05 or it's not worth the holding period risk
- We got IC -0.01 to 0.02 → **Not good enough**

### For Intraday Signals (What We'll Build)
- **IC > 0.025** = Acceptable with high Sharpe
- **Sharpe > 0.5** = Must have to justify intraday noise
- **Win Rate > 55%** = Needed for confidence

### For High-Frequency (If We Go There)
- IC > 0.01 can work if Sharpe > 2.0
- Need sub-second data and execution

---

## Next Steps

1. **Build intraday system with IBKR data** (free, already have it)
2. **Target: 30-min to 4-hour holding periods**
3. **If IC > 0.025, proven profitable → add Polygon.io**
4. **If still failing → pivot to different approach**

---

## Reality Check

Most retail quants who succeed do ONE of these:
1. **Intraday mean reversion** (works in choppy markets)
2. **Overnight gap strategies** (works in trending markets)
3. **Options premium selling** (systematic credit spreads)
4. **Volatility arbitrage** (requires options data)

Daily/weekly momentum (what we tried) is the HARDEST because:
- Holding period is long (more risk)
- Signals decay fastest at this timeframe
- Most arbitraged by institutions

We should try intraday first.
