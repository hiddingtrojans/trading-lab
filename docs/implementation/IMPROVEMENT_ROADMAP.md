# System Improvement Roadmap

## Overview

Comprehensive plan to improve the trading system from working prototype to production-grade platform.

---

## PHASE 1: Critical Fixes (Week 1) 🔴

### 1.1 Fix Integration Bugs ⚠️ HIGH PRIORITY
**Status:** In Progress
**Issue:** analyze.py has bugs, doesn't show full GPT output
**Impact:** Can't use intelligent analysis properly

**Tasks:**
- [x] Fix score extraction (final_score vs overall_score)
- [ ] Show full GPT insights (catalysts, risks, detailed analysis)
- [ ] Fix JSON serialization errors
- [ ] Add proper error handling for missing data
- [ ] Test on 20+ different tickers

**Estimated Time:** 2-3 hours

---

### 1.2 Delete Broken Scripts ⚠️ HIGH PRIORITY
**Status:** Not Started
**Issue:** 18 broken/duplicate scripts cluttering repo
**Impact:** Confusion, maintenance burden

**Tasks:**
- [ ] Delete 6 broken daily prediction scripts (negative IC)
- [ ] Delete 5 duplicate intraday scanners
- [ ] Delete 7 limited/broken scanners
- [ ] Archive run_anomaly_breakout.py
- [ ] Update .gitignore if needed

**Commands:**
```bash
# Run deletion commands from CONSOLIDATION_SUMMARY.md
rm run_breakout_prediction.py run_breakout_production.py run_breakout_final.py
rm run_breakout_simple.py run_breakout_curated_7d_WORKING.py run_breakout_russell2000_7d.py
rm run_intraday_laggards.py run_intraday_r1k.py run_intraday_r2k_laggards.py
rm run_intraday_under5b.py run_intraday_scanner.py
rm check_ah_movers.py scan_gaps.py ibkr_ah_scanner.py ibkr_1hour_scanner.py
rm ibkr_universe_scanner.py comprehensive_scanner.py small_midcap_scanner.py
rm scripts/run_trading_bot.py
mkdir -p archive && mv run_anomaly_breakout.py archive/
```

**Estimated Time:** 15 minutes

---

### 1.3 Add Caching System
**Status:** Not Started
**Issue:** Re-downloads same data, FinBERT reloads every time
**Impact:** Slow repeated queries, unnecessary API calls

**Tasks:**
- [ ] Cache FinBERT model (load once, reuse)
- [ ] Cache yfinance data (5-minute TTL)
- [ ] Cache LEAPS results (1-hour TTL)
- [ ] Cache scanner signals (15-minute TTL)

**Implementation:**
```python
import pickle
import time

class Cache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
```

**Estimated Time:** 2 hours

---

## PHASE 2: Validation (Week 2) 🟡

### 2.1 Historical Backtest for Day Bot ⭐ HIGHEST ROI
**Status:** Not Started
**Issue:** Need to wait 2-4 weeks for 1000 trades
**Impact:** Can't validate quickly

**Tasks:**
- [ ] Download 1 year of 5-minute bars from IBKR
- [ ] Simulate gap trades on historical data
- [ ] Calculate win rate, profit factor, Sharpe
- [ ] Compare to forward validation
- [ ] Generate backtest report

**Implementation:**
```python
class HistoricalBacktester:
    def backtest_gap_strategy(self, start_date, end_date):
        # For each trading day:
        # 1. Identify gaps at open
        # 2. Calculate VWAP
        # 3. Simulate entry/exit using bot logic
        # 4. Track P&L
        
        # Return:
        # - Win rate
        # - Average win/loss
        # - Sharpe ratio
        # - Max drawdown
```

**Benefit:** Validate in 1 hour instead of 4 weeks

**Estimated Time:** 6-8 hours

---

### 2.2 Scanner Signal Validation
**Status:** Partial (backtest_intraday_signals.py exists)
**Issue:** Need to prove IC > 0.025

**Tasks:**
- [ ] Run 30-day backtest on scanner signals
- [ ] Calculate actual IC (Information Coefficient)
- [ ] Measure Sharpe ratio
- [ ] Test on different market regimes
- [ ] Document validation results

**Estimated Time:** 3-4 hours

---

### 2.3 LEAPS Performance Tracking
**Status:** Not Started
**Issue:** No way to track if LEAPS recommendations are profitable

**Tasks:**
- [ ] Create LEAPS portfolio tracker
- [ ] Track entries vs actual performance
- [ ] Calculate hit rate on price targets
- [ ] Measure average holding period return
- [ ] Compare to buy-and-hold

**Estimated Time:** 4 hours

---

## PHASE 3: Feature Additions (Weeks 3-4) 🟢

### 3.1 Unified Position Tracking ⭐ HIGH VALUE
**Status:** Not Started
**Issue:** Positions scattered across systems

**Tasks:**
- [ ] Create positions.db (SQLite)
- [ ] Track day trades automatically (from bot)
- [ ] Manual entry for LEAPS positions
- [ ] Manual entry for scanner trades
- [ ] Calculate combined metrics

**Schema:**
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    ticker TEXT,
    strategy TEXT,  -- 'day_bot', 'leaps', 'scanner'
    entry_price REAL,
    current_price REAL,
    quantity INTEGER,
    pnl REAL,
    status TEXT  -- 'open', 'closed'
);
```

**Dashboard:**
```python
def show_portfolio():
    """
    Combined Portfolio View:
    
    Day Trades: 3 positions, +$450 today
    LEAPS: 7 positions, +$3,200 total
    Scanner: 2 positions, +$180 today
    
    Total: 12 positions, +$3,830
    Exposure: 45% of capital
    Beta: 1.2
    Sharpe: 1.8
    """
```

**Estimated Time:** 8 hours

---

### 3.2 Real-Time Alert System
**Status:** Not Started
**Issue:** Must manually check scanner

**Tasks:**
- [ ] Background scanner process
- [ ] Email alerts (SMTP)
- [ ] SMS alerts (Twilio)
- [ ] Telegram bot (optional)
- [ ] Alert on high-confidence signals (>70)

**Implementation:**
```python
def background_scanner():
    while market_open():
        signals = scan_universe(watchlist)
        high_conf = [s for s in signals if s['confidence'] > 70]
        
        for signal in high_conf:
            send_alert(f"{signal['ticker']}: {signal['signal']}, "
                      f"confidence {signal['confidence']}")
        
        sleep(300)  # Every 5 minutes
```

**Estimated Time:** 4 hours

---

### 3.3 Portfolio Optimizer
**Status:** Not Started
**Issue:** No systematic position sizing

**Tasks:**
- [ ] Implement Kelly criterion
- [ ] Add correlation matrix
- [ ] Sector exposure limits
- [ ] Risk parity allocation
- [ ] Maximum position sizes

**Implementation:**
```python
class PortfolioOptimizer:
    def optimize(self, signals, capital):
        """
        Input: 
        - Day bot: 3 gap signals
        - Scanner: 5 VWAP signals
        - LEAPS: 3 opportunities
        
        Output:
        - Optimal position sizes
        - Risk-adjusted allocation
        - Diversification score
        """
```

**Estimated Time:** 10 hours

---

## PHASE 4: Model Improvements (Month 2) 🔵

### 4.1 Fix Daily Breakout Models
**Status:** Not Started (Models have negative IC)
**Issue:** Missing features, small universe

**Tasks:**
- [ ] Expand universe to 2000+ stocks
- [ ] Add fundamental features (20+ ratios)
- [ ] Add event-driven features (earnings calendar)
- [ ] Add sentiment features (news, social)
- [ ] Run hyperparameter optimization (Optuna)
- [ ] Re-validate with walk-forward

**Features to Add:**
```python
# Fundamental (yfinance):
- P/E, P/B, P/S ratios
- ROE, ROA, ROIC
- Debt/Equity
- Revenue growth trend
- Earnings surprise history

# Event-driven (yfinance):
- Days to earnings
- Days since earnings
- Earnings beat/miss
- Analyst upgrades/downgrades

# Sentiment (free sources):
- News headline count
- Reddit mentions (pushshift)
- Twitter sentiment
- Google Trends
```

**Estimated Time:** 20-30 hours

---

### 4.2 Improve Scanner Signals
**Status:** Partial (works but low confidence on many)
**Issue:** Too many signals, quality varies

**Tasks:**
- [ ] Add volume confirmation filter
- [ ] Require news catalyst for gaps
- [ ] Add market regime filter (only trade in trends)
- [ ] Sector momentum overlay
- [ ] Multi-timeframe confirmation

**Filters:**
```python
# Only output signal if:
signal_quality = (
    has_gap and gap > 2%              # Significant move
    and volume > 2x_average           # Volume confirmation
    and has_news_catalyst             # Reason for move
    and spy_direction == signal_direction  # Market alignment
    and sector_momentum > 0           # Sector supporting
)
```

**Estimated Time:** 8 hours

---

### 4.3 Add Options Flow Analysis
**Status:** Not Started
**Issue:** Missing informed money signals

**Tasks:**
- [ ] Track unusual options volume
- [ ] Calculate put/call ratios
- [ ] Detect large block trades
- [ ] Identify smart money moves
- [ ] Integrate into day bot signals

**Benefit:** Options flow often predicts stock moves

**Estimated Time:** 12 hours

---

## PHASE 5: Infrastructure (Month 3) 🟣

### 5.1 Database Migration
**Status:** Not Started
**Tasks:**
- [ ] SQLite for all data storage
- [ ] Migrate CSV files to tables
- [ ] Add proper indexes
- [ ] Create query interface
- [ ] Backup system

**Estimated Time:** 10 hours

---

### 5.2 Web Dashboard
**Status:** Partial (validation dashboard exists)
**Tasks:**
- [ ] Unified dashboard for all strategies
- [ ] Real-time scanner results
- [ ] Portfolio overview
- [ ] Performance charts
- [ ] Trade history

**Estimated Time:** 15-20 hours

---

### 5.3 Proper Testing Suite
**Status:** Minimal
**Tasks:**
- [ ] Unit tests for all modules
- [ ] Integration tests
- [ ] Performance tests
- [ ] CI/CD pipeline
- [ ] Documentation tests

**Estimated Time:** 12 hours

---

## PHASE 6: Advanced Features (Month 4+) ⚪

### 6.1 Machine Learning Improvements
- [ ] AutoML for hyperparameter tuning
- [ ] Online learning (update models daily)
- [ ] Ensemble stacking
- [ ] Feature importance tracking

### 6.2 Alternative Data
- [ ] Satellite imagery (retail traffic)
- [ ] Credit card data
- [ ] Social media sentiment
- [ ] Insider trading tracking

### 6.3 Risk Management
- [ ] VaR (Value at Risk) calculations
- [ ] Stress testing
- [ ] Correlation monitoring
- [ ] Dynamic position sizing

---

## Total Effort Estimate

**Phase 1 (Critical):** 10-15 hours
**Phase 2 (Validation):** 20-25 hours
**Phase 3 (Features):** 30-40 hours
**Phase 4 (Models):** 40-50 hours
**Phase 5 (Infrastructure):** 35-45 hours
**Phase 6 (Advanced):** 60+ hours

**Total: 195-225 hours** (roughly 5-6 weeks full-time)

---

## Recommended Start

**This week (5-10 hours):**
1. Fix analyze.py bugs completely (2 hours)
2. Delete broken scripts (15 minutes)
3. Add caching (2 hours)
4. Historical backtest for day bot (6 hours)

**Next week (10-15 hours):**
5. Unified position tracking (8 hours)
6. Real-time alerts (4 hours)
7. Scanner validation (3 hours)

**Month 1:**
Focus on validation and position tracking - prove the systems work.

**Month 2:**
Improve models and add features.

**Month 3+:**
Infrastructure upgrades and advanced features.

---

## Success Metrics

**After Phase 1:**
- [ ] All bugs fixed
- [ ] Clean codebase
- [ ] Fast repeated queries

**After Phase 2:**
- [ ] Day bot validated (55%+ win rate)
- [ ] Scanner validated (IC > 0.025)
- [ ] LEAPS tracking operational

**After Phase 3:**
- [ ] Unified portfolio view
- [ ] Real-time alerts working
- [ ] Position optimizer functional

**After Phase 4:**
- [ ] Daily models have positive IC
- [ ] Scanner produces fewer, higher-quality signals
- [ ] Options flow integrated

---

## Priority Matrix

**Critical (Do First):**
1. Fix analyze.py bugs
2. Historical backtest
3. Delete broken scripts

**High Value:**
4. Unified position tracking
5. Real-time alerts
6. Fix daily models

**Nice to Have:**
7. Web dashboard
8. Portfolio optimizer
9. Alternative data

**Future:**
10. Advanced ML
11. Full testing suite
12. CI/CD

---

## Current Status: Phase 1 Started

Working on critical fixes now...

