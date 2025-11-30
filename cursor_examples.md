# Cursor Scanner Examples

## Example Queries and Expected Outputs

### 1. High Growth Query
**Query**: "Find stocks with 20%+ revenue growth and positive free cash flow"

**Expected Response**:
```
Based on your criteria, here are 5 high-growth stocks with positive FCF:

1. NVDA - NVIDIA Corporation
   Sector: Technology/Semiconductors  
   Market Cap: $1,100B
   Why Selected: AI boom driving massive growth
   
   Key Metrics:
   - Revenue Growth: 122% YoY
   - FCF Margin: 35%
   - Gross Margin: 75%
   - P/E: 65
   - RSI: 58
   
   LEAPS Potential: Yes - High liquidity, clear growth trajectory
   Day Trade Setup: Yes - High volatility, $5+ ATR
   Risk Factors: Valuation, China exposure, competition

2. CELH - Celsius Holdings
   Sector: Consumer/Beverages
   Market Cap: $9B
   Why Selected: Energy drink market share gains
   
   Key Metrics:
   - Revenue Growth: 37% YoY
   - FCF Margin: 12%
   - Gross Margin: 49%
   - P/E: 48
   - RSI: 45
   
   LEAPS Potential: Yes - Growing options volume
   Day Trade Setup: Yes - High volatility on news
   Risk Factors: Competition from MNST/KO, valuation

[3-5 more examples...]

To analyze all: 
python cursor_workflow.py --tickers NVDA,CELH,... --criteria "20%+ revenue growth with positive FCF"
```

### 2. LEAPS Opportunity Query
**Query**: "Find the best LEAPS candidates in technology with upcoming catalysts"

**Expected Response**:
```
Top 5 Technology LEAPS Candidates:

1. AMD - Advanced Micro Devices
   Market Cap: $230B
   Catalyst: MI300 AI chip ramp, Data center growth
   Timeline: Q1-Q2 2024 earnings
   
   Options Analysis:
   - Jan 2025 calls most liquid
   - IV: 42% (below 1-year avg)
   - Suggested strikes: 140-150 (20-30% OTM)
   - Risk/Reward: 5:1 potential
   
2. PLTR - Palantir Technologies  
   Market Cap: $40B
   Catalyst: AIP platform adoption, Gov contracts
   Timeline: Throughout 2024
   
   Options Analysis:
   - Jan 2025 calls building volume
   - IV: 55% (reasonable for growth)
   - Suggested strikes: 25-30
   - Risk/Reward: 4:1 potential

[3-5 more examples...]

Analyze with: 
python cursor_workflow.py --tickers AMD,PLTR,... --criteria "Tech LEAPS with catalysts"
```

### 3. Day Trading Setup Query
**Query**: "Find stocks gapping up over 3% with news"

**Expected Response**:
```
Today's Gap-Up Day Trading Candidates:

1. SMCI - Super Micro Computer
   Gap: +5.2% 
   News: New AI server contract announced
   Pre-market Volume: 2.5M shares
   
   Setup:
   - Entry: VWAP test (if gaps holds)
   - Stop: Below pre-market low
   - Target 1: +2% from entry
   - Target 2: High of day
   
2. RIVN - Rivian
   Gap: +4.8%
   News: Partnership with major fleet operator
   Pre-market Volume: 8M shares
   
   Setup:
   - Entry: First 5-min high break
   - Stop: -$0.50 from entry
   - Target: Previous resistance at $16.50

[3 more examples...]

Monitor with:
python cursor_workflow.py --tickers SMCI,RIVN,... --criteria "Gap up day trades"
```

### 4. Value + Growth Query
**Query**: "Find profitable companies trading below 20 P/E with 15%+ growth"

**Expected Response**:
```
Value + Growth Opportunities (GARP):

1. FLEX - Flex Ltd
   Sector: Technology/Manufacturing
   Market Cap: $15B
   
   Value Metrics:
   - P/E: 16.5
   - EV/EBITDA: 8.2
   - Price/Book: 2.8
   
   Growth Metrics:
   - Revenue Growth: 18% YoY
   - EPS Growth: 22% YoY
   - FCF Growth: 25% YoY
   
   Why Attractive:
   - EV/AI manufacturing exposure
   - Margin expansion story
   - Share buyback program

[4 more examples...]

Deep dive analysis:
python cursor_workflow.py --tickers FLEX,... --criteria "GARP stocks P/E<20 growth>15%"
```

### 5. Sector Rotation Query
**Query**: "Find financial stocks benefiting from high interest rates"

**Expected Response**:
```
Rate-Sensitive Financial Winners:

1. BAC - Bank of America
   Net Interest Margin: 2.83% (expanding)
   Loan Growth: 8% YoY
   Efficiency Ratio: 58%
   
   Why Selected:
   - NIM expansion from rate environment
   - Strong consumer deposit base
   - Trading below book value
   
2. SCHW - Charles Schwab
   Cash Sweep Revenue: +45% YoY
   New Accounts: +12% YoY
   
   Why Selected:
   - Direct beneficiary of high rates
   - Growing active trader base
   - Options on cash positions

[3 more examples...]

Analyze sector rotation:
python cursor_workflow.py --tickers BAC,SCHW,... --criteria "Rate beneficiary financials"
```

## Query Templates

### Growth Screening:
- "Find stocks with [X]% revenue growth and [Y]% earnings growth"
- "Show me companies growing faster than [X]% with positive margins"
- "What stocks have accelerating growth rates quarter-over-quarter?"

### LEAPS Hunting:
- "Find LEAPS opportunities with [catalyst] in [timeframe]"
- "Show stocks with high options volume suitable for LEAPS"
- "What are the best risk/reward LEAPS in [sector]?"

### Day Trading:
- "Find stocks moving on news with volume surge"
- "Show me gap plays with clear technical setups"
- "What stocks have momentum for day trading?"

### Value Investing:
- "Find undervalued stocks with improving fundamentals"
- "Show me companies trading below book value with catalysts"
- "What stocks have insider buying and low P/E ratios?"

### Thematic Investing:
- "Find AI beneficiaries with reasonable valuations"
- "Show me EV/clean energy stocks with profitability"
- "What biotech stocks have Phase 3 catalysts?"

## Integration Workflow

1. Ask Cursor for specific criteria stocks
2. Copy the ticker list from response  
3. Run: `python cursor_workflow.py --tickers [LIST] --criteria "[YOUR CRITERIA]"`
4. Review comprehensive analysis output
5. Check detailed JSON for deep metrics
6. Execute trades based on recommendations

## Pro Tips

1. **Combine Criteria**: Mix fundamental + technical filters for better results
2. **Time Your Searches**: Run gap searches pre-market, catalyst searches on weekends
3. **Track History**: Save outputs to track recommendation performance
4. **Refine Criteria**: Adjust based on market conditions
5. **Risk Management**: Never trade all recommendations, diversify approaches






