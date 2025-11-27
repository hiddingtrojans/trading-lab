# Complete Script Audit & Consolidation Plan

## Executive Summary

**Total Scripts Found:** 41 Python scripts (excluding library files)
**Working Scripts:** 12
**Broken/Incomplete:** 18
**Duplicate/Redundant:** 11

**Recommendation:** Consolidate to 5 core scripts + 1 unified scanner

---

## CATEGORY 1: WORKING & USEFUL ✅

### High Value - Keep & Use

1. **run_intraday_scanner.py** ✅
   - Status: Working
   - Purpose: Intraday gap/momentum/VWAP signals using IBKR
   - Value: HIGH - This is your best bet for alpha
   - Dependencies: IBKR Gateway, `src/alpha_lab/intraday_signals.py`
   - Keep: YES

2. **backtest_intraday_signals.py** ✅
   - Status: Working
   - Purpose: Validates intraday signals on historical data
   - Value: HIGH - Proves signals work before trading
   - Dependencies: IBKR Gateway
   - Keep: YES

3. **get_russell1000.py** ✅
   - Status: Working
   - Purpose: Downloads Russell 1000 constituents from iShares
   - Value: MEDIUM - Good for universe building
   - Keep: YES

4. **get_russell2000.py** ✅
   - Status: Working
   - Purpose: Downloads Russell 2000 constituents
   - Value: MEDIUM - Good for universe building
   - Keep: YES

5. **expand_universe.py** ✅
   - Status: Working (but slow - 30+ min)
   - Purpose: Build full US stock universe from multiple sources
   - Value: MEDIUM - Comprehensive but rate-limited
   - Keep: YES (for one-time use)

### Medium Value - Keep for Specific Use Cases

6. **scripts/live_daily.py** ✅
   - Status: Working
   - Purpose: Generate ETF signals (SPY/QQQ/IWM/TLT/GLD/HYG/IBIT)
   - Value: LOW - Signals have no alpha (IC < 0.02)
   - Keep: YES (but don't trade until validated)

7. **scripts/backtest_daily.py** ✅
   - Status: Working
   - Purpose: Backtest ETF strategy
   - Value: LOW - Shows strategy doesn't work
   - Keep: YES (for validation)

8. **scripts/send_orders_ibkr.py** ✅
   - Status: Working
   - Purpose: Submit MOO orders to IBKR
   - Value: MEDIUM - Infrastructure piece
   - Keep: YES

9. **scripts/reconcile_ibkr.py** ✅
   - Status: Working
   - Purpose: Pull fills/positions from IBKR
   - Value: MEDIUM - Essential for tracking
   - Keep: YES

10. **scripts/run_leaps_analysis.py** ✅
    - Status: Working
    - Purpose: LEAPS options analysis
    - Value: MEDIUM - Different strategy
    - Keep: YES (separate from scanners)

11. **scripts/run_paper_trading.py** ✅
    - Status: Working
    - Purpose: Paper trading bot
    - Value: MEDIUM - Good for testing
    - Keep: YES

12. **scripts/run_trading_bot.py** ✅
    - Status: Menu wrapper
    - Purpose: Menu system for trading scripts
    - Value: LOW - main.py does this better
    - Keep: NO (main.py replaces it)

---

## CATEGORY 2: BROKEN / NON-FUNCTIONAL ❌

### Daily Breakout Prediction Scripts (ALL HAVE NEGATIVE IC)

13. **run_breakout_prediction.py** ❌
    - Status: Incomplete/Fails validation
    - Issue: Uses 154-stock universe, no fundamentals, negative IC
    - Value: NONE - Doesn't work
    - Action: DELETE or archive

14. **run_breakout_production.py** ❌
    - Status: Fails validation (IC: -0.0175)
    - Issue: Same as above
    - Value: NONE
    - Action: DELETE

15. **run_breakout_final.py** ❌
    - Status: Fails validation
    - Issue: Same issues
    - Value: NONE
    - Action: DELETE

16. **run_breakout_simple.py** ❌
    - Status: Simplified version, still fails
    - Issue: Same root cause
    - Value: NONE
    - Action: DELETE

17. **run_breakout_curated_7d_WORKING.py** ❌
    - Status: Name says "WORKING" but it doesn't
    - Issue: 7-day prediction window, same problems
    - Value: NONE
    - Action: DELETE

18. **run_breakout_russell2000_7d.py** ❌
    - Status: Russell 2000 variant, fails
    - Issue: Same issues
    - Value: NONE
    - Action: DELETE

19. **run_anomaly_breakout.py** ❌
    - Status: Experimental approach, unfinished
    - Issue: Incomplete implementation
    - Value: NONE - interesting idea but doesn't work
    - Action: ARCHIVE for future research

### Intraday Scanner Variants (DUPLICATES)

20. **run_intraday_laggards.py** ❌
    - Status: Duplicate functionality
    - Issue: Does same thing as run_intraday_scanner.py
    - Value: REDUNDANT
    - Action: DELETE (keep run_intraday_scanner.py)

21. **run_intraday_r1k.py** ❌
    - Status: Russell 1000 variant
    - Issue: Just changes universe, same logic
    - Value: REDUNDANT
    - Action: DELETE (add universe selection to main scanner)

22. **run_intraday_r2k_laggards.py** ❌
    - Status: Russell 2000 variant
    - Issue: Duplicate
    - Value: REDUNDANT
    - Action: DELETE

23. **run_intraday_under5b.py** ❌
    - Status: Market cap filter variant
    - Issue: Duplicate
    - Value: REDUNDANT
    - Action: DELETE

### Simple Scanners (INCOMPLETE/LIMITED)

24. **check_ah_movers.py** ❌
    - Status: Basic after-hours scanner
    - Issue: Limited functionality, no IBKR integration
    - Value: LOW - uses yfinance instead of IBKR
    - Action: DELETE (IBKR scanners better)

25. **scan_gaps.py** ❌
    - Status: Basic gap scanner
    - Issue: Limited, no IBKR
    - Value: LOW
    - Action: DELETE (intraday scanner does this)

26. **ibkr_ah_scanner.py** ❌
    - Status: IBKR after-hours scanner
    - Issue: Hardcoded watchlist, limited
    - Value: MEDIUM - works but limited
    - Action: MERGE into unified scanner

27. **ibkr_1hour_scanner.py** ❌
    - Status: 1-hour momentum scanner
    - Issue: Hardcoded watchlist
    - Value: MEDIUM - works but limited
    - Action: MERGE into unified scanner

28. **ibkr_universe_scanner.py** ❌
    - Status: Full universe scanner using IBKR API
    - Issue: Incomplete implementation
    - Value: LOW - doesn't parse results properly
    - Action: DELETE (broken)

29. **comprehensive_scanner.py** ❌
    - Status: Ambitious full-universe scanner
    - Issue: Too slow, rate-limited
    - Value: LOW - impractical
    - Action: DELETE

30. **small_midcap_scanner.py** ❌
    - Status: Small/mid-cap focused scanner
    - Issue: Hardcoded watchlist, redundant
    - Value: REDUNDANT
    - Action: DELETE

---

## CATEGORY 3: INFRASTRUCTURE / TESTS ⚙️

31. **tests/test_cv.py** ✅
    - Keep: YES

32. **tests/test_leakage.py** ✅
    - Keep: YES

33. **main.py** ✅
    - Keep: YES (primary entry point)

34. **scripts/run_1000trade_validation.py** ✅
    - Keep: YES (validates day trading bot)

35. **scripts/run_validation_simulation.py** ✅
    - Keep: YES

36. **scripts/run_live_trading.py** ⚠️
    - Status: Unknown (need to test)
    - Keep: YES (but verify first)

---

## CONSOLIDATION PLAN

### DELETE (18 scripts)
```bash
# Broken daily prediction scripts
rm run_breakout_prediction.py
rm run_breakout_production.py
rm run_breakout_final.py
rm run_breakout_simple.py
rm run_breakout_curated_7d_WORKING.py
rm run_breakout_russell2000_7d.py

# Duplicate intraday scanners
rm run_intraday_laggards.py
rm run_intraday_r1k.py
rm run_intraday_r2k_laggards.py
rm run_intraday_under5b.py

# Limited/broken scanners
rm check_ah_movers.py
rm scan_gaps.py
rm ibkr_universe_scanner.py
rm comprehensive_scanner.py
rm small_midcap_scanner.py

# Duplicate/redundant
rm ibkr_ah_scanner.py  # Merge into unified
rm ibkr_1hour_scanner.py  # Merge into unified
rm scripts/run_trading_bot.py  # main.py does this
```

### ARCHIVE (1 script - for future research)
```bash
mkdir -p archive
mv run_anomaly_breakout.py archive/
```

### KEEP & IMPROVE (12 scripts)
```
✅ run_intraday_scanner.py (PRIMARY SCANNER)
✅ backtest_intraday_signals.py
✅ get_russell1000.py
✅ get_russell2000.py
✅ expand_universe.py
✅ main.py
✅ scripts/live_daily.py
✅ scripts/backtest_daily.py
✅ scripts/send_orders_ibkr.py
✅ scripts/reconcile_ibkr.py
✅ scripts/run_leaps_analysis.py
✅ scripts/run_paper_trading.py
```

### NEW: CREATE UNIFIED SCANNER (Replaces 7 scripts)

**scanner.py** - Consolidated, feature-rich scanner

Features:
- Intraday signals (gap/momentum/VWAP)
- After-hours movers
- 1-hour momentum
- Multiple universes (R1K, R2K, custom)
- Real-time IBKR data
- Backtesting capability
- Output to CSV
- Alert system

This replaces:
- run_intraday_scanner.py
- ibkr_ah_scanner.py
- ibkr_1hour_scanner.py
- run_intraday_laggards.py
- run_intraday_r1k.py
- run_intraday_r2k_laggards.py
- run_intraday_under5b.py

---

## FINAL STRUCTURE

```
scanner/
├── main.py                          # Menu system
├── scanner.py                       # NEW: Unified scanner
│
├── utils/
│   ├── get_russell1000.py
│   ├── get_russell2000.py
│   └── expand_universe.py
│
├── backtest/
│   ├── backtest_intraday_signals.py
│   └── backtest_daily.py
│
├── scripts/
│   ├── live_daily.py               # ETF signals
│   ├── send_orders_ibkr.py         # Order execution
│   ├── reconcile_ibkr.py           # Position tracking
│   ├── run_leaps_analysis.py       # LEAPS system
│   ├── run_paper_trading.py        # Paper trading
│   └── run_1000trade_validation.py # Bot validation
│
├── tests/
│   ├── test_cv.py
│   └── test_leakage.py
│
└── archive/
    └── run_anomaly_breakout.py     # Future research
```

---

## NEXT STEPS

1. ✅ Create unified `scanner.py`
2. ✅ Update `main.py` to use new scanner
3. ✅ Delete 18 redundant/broken scripts
4. ✅ Archive 1 experimental script
5. ✅ Update all documentation in `docs/`
6. ✅ Create new `docs/SCANNER_GUIDE.md`
7. ✅ Test unified scanner
8. ✅ Update README.md

---

## PERFORMANCE EXPECTATIONS

### What Works
- **Intraday signals**: Unvalidated but promising (need 2 weeks backtesting)
- **Universe builders**: Work reliably
- **IBKR infrastructure**: Solid

### What Doesn't Work
- **Daily breakout predictions**: Negative IC (-0.01 to +0.02)
- **ETF systematic signals**: No alpha at daily timeframe
- **Comprehensive scanners**: Too slow/rate-limited

### What to Trade
1. Start with intraday scanner during market hours
2. Paper trade for 2 weeks
3. If IC > 0.025 and Sharpe > 0.5, go live with small size
4. Do NOT trade daily prediction scripts (negative alpha)

---

## HONEST ASSESSMENT

**Good:**
- Clean code structure
- Proper validation framework
- IBKR integration works
- Intraday approach is correct pivot

**Bad:**
- Too many duplicate scripts
- Daily predictions don't work
- No consolidation
- Confusing for user

**Ugly:**
- 11 scripts doing the same thing
- 6 broken daily prediction variants
- No clear "start here" path

**Fix:**
- Consolidate to 1 unified scanner
- Delete everything that doesn't work
- Clear documentation
- Simple entry point

