# Quick Reference - Cursor Scanner Commands

## Most Useful Queries

### 📈 Growth Stocks
```
"Find stocks with 25%+ revenue growth and expanding margins"
"Show me profitable tech companies growing over 30% YoY"
"What mid-cap stocks have accelerating earnings growth?"
```

### 🎯 LEAPS Opportunities  
```
"Find LEAPS candidates with 6-12 month catalysts under $100"
"Show me biotech stocks with high options volume for LEAPS"
"What tech stocks are good for 1-year call options?"
```

### 🚀 Day Trading Setups
```
"Find stocks gapping up 3%+ on high volume"
"Show me momentum stocks near VWAP with news"
"What stocks are breaking 52-week highs with volume?"
```

### 💰 Value Plays
```
"Find profitable companies with P/E under 15 and growth"
"Show me stocks with insider buying under book value"
"What dividend stocks are oversold with good fundamentals?"
```

## Quick Workflow

1. **Ask Cursor**: Use query from above
2. **Get Tickers**: Copy the ticker symbols
3. **Run Analysis**:
```bash
python cursor_workflow.py --tickers TICK1,TICK2,TICK3 --criteria "your search criteria"
```

## Best Times to Search

- **Pre-Market (7-9:30 AM)**: Gap plays, news reactions
- **Mid-Day (11 AM-2 PM)**: VWAP setups, trend continuations  
- **After Hours (4-6 PM)**: Earnings plays, next day prep
- **Weekends**: LEAPS research, fundamental screening

## Red Flags to Avoid

❌ Chinese ADRs without specific reason
❌ Stocks under $5 (unless penny stock strategy)
❌ Average volume < 500K shares
❌ Companies with going concern warnings
❌ Biotech without cash runway

## Green Flags to Prioritize

✅ Positive free cash flow
✅ Insider buying (not just vesting)
✅ Beat and raise quarters
✅ Expanding margins
✅ Multiple catalysts aligned

## Position Sizing Guide

- **LEAPS**: 1-2% of portfolio per position
- **Day Trades**: 0.5-1% risk per trade
- **Swing Trades**: 2-3% of portfolio
- **Core Holdings**: 5-10% for high conviction

## Example Full Workflow

```bash
# Monday Morning Routine
1. "Find stocks gapping up with earnings beats"
   -> Get: NVDA, AMD, PLTR

2. python cursor_workflow.py --tickers NVDA,AMD,PLTR --criteria "earnings beat gaps"

3. Review scores and recommendations

4. Execute trades:
   - NVDA: LEAPS Jan 2025 $200 calls
   - AMD: Day trade gap fill
   - PLTR: Wait for pullback

5. Set alerts and stops
```

## Emergency Searches

🆘 **Market Crash**: "Find defensive stocks with low beta and dividends"
📉 **Sector Rotation**: "Show me stocks with relative strength vs SPY"
📰 **News Event**: "Find stocks moving on [specific news type]"
💥 **Volatility Spike**: "Show me stocks with IV crush opportunities"

## Save These Aliases

```bash
# Add to .bashrc or .zshrc
alias scan='python /Users/raulacedo/Desktop/scanner/cursor_workflow.py'
alias growth='echo "Find stocks with 25%+ revenue growth"'
alias leaps='echo "Find LEAPS candidates with catalysts"'
alias gaps='echo "Find stocks gapping up 3%+ on volume"'
```

## Remember

1. Always verify with `cursor_workflow.py` analysis
2. Check options chain manually before LEAPS
3. Set stops on all day trades
4. Size positions appropriately
5. Track your hit rate over time

---
*Keep this handy during market hours!*










