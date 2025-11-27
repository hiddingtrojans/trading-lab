# Unified Scanner Guide

## Overview

The unified scanner consolidates 7 separate scanner scripts into one powerful tool for finding intraday trading opportunities.

### What It Replaces

The new `scanner.py` replaces these 7 scripts:
- `run_intraday_scanner.py`
- `ibkr_ah_scanner.py`
- `ibkr_1hour_scanner.py`
- `run_intraday_laggards.py`
- `run_intraday_r1k.py`
- `run_intraday_r2k_laggards.py`
- `run_intraday_under5b.py`

---

## Quick Start

### Basic Usage

```bash
# Scan liquid stocks for intraday signals (default)
python scanner.py

# Scan for after-hours movers
python scanner.py --mode after_hours

# Scan for 1-hour momentum
python scanner.py --mode 1hour

# Run all scan types
python scanner.py --mode all
```

### Universe Selection

```bash
# Liquid stocks (60 high-volume names)
python scanner.py --universe liquid

# Russell 1000 (large/mid caps)
python scanner.py --universe russell1000

# Russell 2000 (small caps)
python scanner.py --universe russell2000

# Custom universe (create data/custom_universe.csv)
python scanner.py --universe custom
```

### Advanced Options

```bash
# Show top 20 results
python scanner.py --top 20

# Save results to CSV
python scanner.py --save

# Use paper trading port
python scanner.py --port 7497

# Complete example
python scanner.py --mode all --universe russell1000 --top 20 --save
```

---

## Scan Modes

### 1. Intraday Signals (Default)

Detects three types of intraday opportunities:

#### Gap Continuation/Fade
- Identifies stocks that gapped at open
- Predicts if gap will continue or fade
- Factors: gap size, volume, VWAP, yesterday's trend

#### Momentum Breakout
- Finds stocks breaking previous day high/low
- Requires volume surge (>1.5x normal)
- Sustained move (>1% in 30 minutes)

#### VWAP Reversion
- Mean reversion around VWAP
- Signals when price deviates >2 std devs
- Looks for momentum reversal

**When to use:** During market hours (9:30 AM - 4:00 PM ET)

**Example:**
```bash
python scanner.py --mode intraday --universe liquid --top 10
```

**Output:**
```
Rank  Symbol   Signal                    Confidence  Price     
1     NVDA     GAP_CONTINUATION          85.2        $450.75   
2     TSLA     MOMENTUM_BREAKOUT_LONG    72.8        $245.30   
3     AMD      VWAP_REVERSION_SHORT      68.4        $115.20   
```

---

### 2. After-Hours Scanner

Finds stocks moving in after-hours/pre-market.

**Criteria:**
- Minimum 0.5% gap from previous close
- Uses real-time IBKR data
- Sorted by gap magnitude

**When to use:** After market close (4:00 PM - 9:30 AM ET)

**Example:**
```bash
python scanner.py --mode after_hours --universe liquid
```

**Output:**
```
Rank  Symbol   Gap %     Direction  Prev Close   Current   
1     COIN     +3.45%    UP         $145.20      $150.21   
2     PLTR     -2.15%    DOWN       $23.45       $22.95    
```

---

### 3. 1-Hour Momentum Scanner

Captures intraday momentum moves.

**Criteria:**
- Minimum 1% move in last hour
- Uses real-time IBKR data
- Good for day trading entries

**When to use:** During market hours, run every hour

**Example:**
```bash
python scanner.py --mode 1hour --universe liquid
```

**Output:**
```
Rank  Symbol   Change %  Direction  1h Ago     Current   
1     NVDA     +2.35%    UP         $445.20    $455.67   
2     TSLA     -1.85%    DOWN       $248.50    $243.90   
```

---

## Universe Options

### Liquid (60 stocks) - DEFAULT

Best for intraday trading. Hand-picked liquid names:
- High volume tech (AAPL, NVDA, TSLA)
- Volatile growth (COIN, PLTR, SNOW)
- Meme/retail (GME, AMC, SOFI)
- High beta (UPST, AFRM, CVNA)
- Major ETFs (SPY, QQQ, IWM)

**Pros:** Fast scanning (1-2 minutes), reliable signals
**Cons:** Limited coverage

### Russell 1000 (~1000 stocks)

Large and mid-cap stocks.

**Setup:**
```bash
python get_russell1000.py
python scanner.py --universe russell1000
```

**Pros:** Broader coverage, still liquid
**Cons:** Slower (5-10 minutes)

### Russell 2000 (~2000 stocks)

Small-cap stocks.

**Setup:**
```bash
python get_russell2000.py
python scanner.py --universe russell2000
```

**Pros:** More volatility, less efficient
**Cons:** Slower (10-20 minutes), wider spreads

### Custom Universe

Create your own watchlist:

1. Create `data/custom_universe.csv`:
```csv
ticker
AAPL
NVDA
TSLA
PLTR
```

2. Run scanner:
```bash
python scanner.py --universe custom
```

---

## Typical Daily Workflow

### Morning Routine (Before Market Open)

```bash
# Check after-hours movers
python scanner.py --mode after_hours --universe liquid --save

# Review gaps, prepare watchlist
# Copy top 5 symbols to notebook
```

### Market Open (9:30 AM)

```bash
# First scan at 9:30 AM
python scanner.py --mode intraday --universe liquid --top 10 --save

# Note gap continuation/fade signals
# Place trades on highest confidence signals
```

### Mid-Morning (11:00 AM)

```bash
# Check 1-hour momentum
python scanner.py --mode 1hour --universe liquid --save

# Look for new momentum breakouts
```

### Lunch (1:00 PM)

```bash
# Full scan again
python scanner.py --mode all --universe liquid --save

# Review morning trades
# Look for afternoon setups
```

### Late Day (3:00 PM)

```bash
# Final scan
python scanner.py --mode intraday --universe liquid --save

# Close positions or hold overnight
```

### After Close (4:30 PM)

```bash
# Check after-hours action
python scanner.py --mode after_hours --universe liquid --save

# Prepare for next day
```

---

## Configuration

### IBKR Connection Settings

Edit `configs/ibkr.yaml`:
```yaml
host: '127.0.0.1'
port: 4001          # 4001 for live, 7497 for paper
client_id: 1
account: 'YOUR_ACCOUNT'
```

### Custom Filters

Edit `scanner.py` to adjust thresholds:

```python
# Gap detection
min_gap = 0.01  # 1% minimum gap

# Momentum breakout
min_volume_surge = 1.5  # 1.5x normal volume
min_price_move = 0.01   # 1% minimum move

# VWAP reversion
min_std_devs = 2.0  # 2 standard deviations
```

---

## Output Files

When using `--save`, results are saved to:

```
data/output/
├── intraday_signals_20251009_093015.csv
├── after_hours_signals_20251009_083045.csv
└── 1hour_signals_20251009_113020.csv
```

CSV columns:
- `symbol`: Ticker
- `signal`: Signal type
- `confidence`: 0-100 score
- `price`: Current price
- Additional metrics per signal type

---

## Troubleshooting

### "Failed to connect to IBKR Gateway"

1. Check IBKR Gateway is running
2. Verify port (4001 for live, 7497 for paper)
3. Check API settings are enabled

### "No signals found"

- Market may be quiet
- Try different universe
- Lower confidence threshold
- Check market hours

### "Universe file not found"

Run universe builder first:
```bash
python get_russell1000.py
# or
python get_russell2000.py
```

### Slow scanning

- Use smaller universe
- Close other IBKR connections
- Run during off-hours for data download

---

## Performance Tips

1. **Use liquid universe during market hours** - fastest, most reliable
2. **Run Russell scans overnight** - download data when markets closed
3. **Save results** - review later without re-scanning
4. **Focus on top 10** - highest confidence signals only
5. **Paper trade first** - validate signals for 2 weeks before going live

---

## Signal Validation

Before trading ANY signals:

1. **Backtest first:**
```bash
python backtest_intraday_signals.py
```

2. **Target metrics:**
   - IC > 0.025
   - Sharpe > 0.5
   - Win Rate > 55%

3. **Paper trade 2 weeks** minimum

4. **Start small** - risk 0.5% per trade

---

## Integration with Main System

The scanner is integrated into `main.py`:

```bash
python main.py
# Select option for scanning
```

Or run standalone:

```bash
python scanner.py --mode intraday
```

---

## API Rate Limits

IBKR has rate limits:
- 60 requests per second
- Scanner includes delays to stay under limits
- Large universes may take 10-20 minutes

Tips:
- Scan during pre-market for faster data
- Use smaller universes during market hours
- Cache results and review later

---

## Next Steps

1. **Run first scan:**
```bash
python scanner.py --mode intraday --universe liquid
```

2. **Backtest signals:**
```bash
python backtest_intraday_signals.py
```

3. **Paper trade 2 weeks**

4. **Go live with small size**

5. **Scale up gradually**

---

## Support

For issues or questions:
1. Check `SCRIPT_AUDIT.md` for script status
2. Review `SHORTCUTS_AND_FIXES.md` for known issues
3. See `FINAL_SUMMARY.md` for system overview

---

## Disclaimer

Intraday trading is risky. These signals are experimental. Paper trade extensively before risking real capital. No guarantee of profitability.

