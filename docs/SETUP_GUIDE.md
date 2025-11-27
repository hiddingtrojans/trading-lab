# Complete LEAPS System - Setup Guide

## Quick Start

### 1. Install Required Dependencies

```bash
pip install pandas numpy yfinance tabulate pytz
```

### 2. Optional Dependencies

For GPT analysis (recommended):
```bash
pip install openai
export OPENAI_API_KEY="your-openai-api-key"
```

For IBKR integration (optional):
```bash
pip install ib_insync
# Requires Interactive Brokers TWS/Gateway running
```

### 3. Basic Usage

```bash
# Analyze a single stock
python3 complete_leaps_system.py AAPL

# Analyze multiple stocks with triage summary
python3 complete_leaps_system.py --batch AAPL MSFT GOOGL TSLA

# Get JSON output for programmatic use
python3 complete_leaps_system.py --json AAPL

# Use systematic model only (no GPT required)
python3 complete_leaps_system.py --no-gpt AAPL
```

## Features Overview

### ✅ What's Included
- **Real option chain analysis** with liquidity validation
- **Dynamic LEAPS expiry calculation** (always future dates)
- **Enhanced fundamental scoring** with risk penalties
- **Batch analysis with triage ranking**
- **Transparent scoring breakdown**
- **Error handling with retry mechanisms**
- **JSON output for integration**

### 📊 New Analysis Components
1. **Short interest analysis** - Identifies heavily shorted stocks
2. **Institutional ownership** - Finds under-discovered opportunities
3. **Real contract costs** - Targets ~$500 per LEAPS contract
4. **Liquidity validation** - Ensures tradeable recommendations
5. **Risk/reward transparency** - Shows all scoring factors

### 🎯 Output Sections
- **Executive Verdict** - Overall recommendation with confidence
- **Price Predictions** - 12 and 24-month targets with methodology
- **Enhanced LEAPS Strategy** - Specific contract recommendations
- **Real Option Chain Analysis** - Actual tradeable contracts
- **Enhanced Scoring Breakdown** - Transparent point allocation
- **Key Catalysts & Risks** - Timeline and probability assessments

## Configuration Options

### Environment Variables
```bash
# Required for GPT analysis
export OPENAI_API_KEY="sk-..."

# Optional for enhanced options data
export POLYGON_API_KEY="your-polygon-key"  # Future feature
```

### Command Line Arguments
- `ticker` - Single ticker to analyze
- `--batch T1 T2 T3` - Multiple tickers with summary
- `--no-gpt` - Use systematic model only
- `--json` - Output results as JSON

## Understanding the Output

### Systematic Scores
- **75-100**: 🚀 STRONG BUY LEAPS
- **60-74**: 🟢 BUY LEAPS  
- **45-59**: 🟡 CONSIDER LEAPS
- **Below 45**: 🔴 AVOID LEAPS

### LEAPS Strategy Components
- **Optimal Strike**: Based on recommendation level and real data
- **Expiry Date**: Dynamically calculated third Friday
- **Contract Cost**: Real market pricing when available
- **Liquidity Info**: Open interest and volume metrics

### Batch Triage Table
Shows ranked comparison of multiple stocks with:
- Ticker, Score, Verdict
- Current Price, Expected 24M Return
- Recommended Strike, Expiry, Cost
- Liquidity Status

## Troubleshooting

### Common Issues

**"No fundamental data available"**
- Check ticker symbol spelling
- Verify stock trades on major US exchanges
- Some foreign stocks may not have complete data

**"No LEAPS available"**
- Stock may not have long-term options
- Check if underlying has sufficient liquidity
- Some small-cap stocks lack LEAPS

**"GPT analysis unavailable"**
- Set OPENAI_API_KEY environment variable
- Check API key validity and credits
- System will use systematic model as fallback

### Data Quality Notes
- Uses Yahoo Finance as primary data source
- Real-time option data requires market hours for IBKR
- Some metrics may be unavailable for certain stocks
- System provides fallback values when data is missing

## Best Practices

### For Screening
1. Use batch mode to compare multiple opportunities
2. Focus on stocks with "liquid contracts" status
3. Pay attention to risk penalties in scoring breakdown
4. Consider institutional ownership for hidden gems

### For Analysis
1. Review the enhanced scoring breakdown for transparency
2. Check real option chain data before trading
3. Verify contract costs fit your budget
4. Consider the risk factors and their probabilities

### For Integration
1. Use JSON output for automated workflows
2. Set up regular screening runs with batch mode
3. Monitor scoring components for risk management
4. Export results for portfolio tracking systems

---

The enhanced LEAPS system provides professional-grade analysis while remaining accessible to individual investors. The comprehensive error handling and transparent scoring make it suitable for both research and systematic investment processes.
