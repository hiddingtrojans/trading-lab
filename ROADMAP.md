# Trading Lab Roadmap

## Current Status: v2.0 (Local Development Complete)

All Tier 1 and Tier 2 features implemented. System ready for deployment.

---

## Implemented Features

### Tier 1 (Core)
- [x] Alert System (`src/alpha_lab/alerts.py`) - Email/SMS notifications
- [x] Scheduled Runner (`src/alpha_lab/scheduler.py`) - Cron-compatible tasks
- [x] Trade Journal (`src/alpha_lab/trade_journal.py`) - SQLite trade logging
- [x] Watchlist Persistence (`src/alpha_lab/watchlist.py`) - Save/load ticker lists

### Tier 2 (Advanced)
- [x] Correlation Filter (`src/alpha_lab/correlation_filter.py`) - Portfolio concentration guard
- [x] Multi-Timeframe Confirmation (`src/alpha_lab/multi_timeframe.py`) - Daily/Weekly alignment
- [x] Sector-Weighted Screener (`src/alpha_lab/sector_weighted_screener.py`) - Sector-adjusted scores
- [x] Options Greeks Display (`src/alpha_lab/options_greeks.py`) - Delta, Theta, IV metrics

### Existing Features
- [x] Market Regime Analysis (VIX, SPY trend, breadth)
- [x] Whale Detector (dark pool proxy)
- [x] Sector Rotation Analysis
- [x] LEAPS System (complete with GPT/FinBERT)
- [x] Backtesting Engine (walk-forward validation)
- [x] Daily Briefing Generator
- [x] Unified Analyzer
- [x] Menu-Driven Launcher

---

## Deployment Options

### Option A: GitHub Actions (FREE - Recommended for Start)

**Best for:** Daily briefing, email alerts, no real-time trading

**Setup:**
1. Push repo to GitHub
2. Add secrets: `SENDGRID_API_KEY`, `ALERT_EMAIL`
3. Enable Actions workflow

**Limitations:**
- 6-hour max runtime
- No IBKR real-time data (Yahoo only)
- No persistent state between runs

**Cost:** $0/month

---

### Option B: Railway (SIMPLE - $5/mo)

**Best for:** Always-on alerts, scheduled tasks, simple deployment

**Setup:**
```bash
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python src/alpha_lab/scheduler.py --daemon"
```

**Features:**
- Git push to deploy
- Built-in cron scheduling
- Persistent SQLite storage
- Custom domains

**Cost:** $5/month (Starter plan)

---

### Option C: AWS EC2 (FULL CONTROL - $8-15/mo)

**Best for:** IBKR integration, full system, maximum flexibility

**Setup:**
1. Launch t3.micro instance (Ubuntu)
2. Install IBKR Gateway (headless)
3. Configure systemd for scheduler
4. Use CloudWatch for monitoring

**Components:**
| Service | Purpose | Cost |
|---------|---------|------|
| EC2 t3.micro | Compute | ~$8/mo |
| S3 | Results backup | ~$1/mo |
| SNS | Alerts | Free tier |
| CloudWatch | Logs | Free tier |

**Cost:** ~$10/month after free tier

---

### Option D: Raspberry Pi (CHEAPEST LONG-TERM)

**Best for:** Home lab, IBKR local, zero recurring cost

**Setup:**
1. Install Raspberry Pi OS
2. Clone repo, create venv
3. Configure systemd service
4. Port forward for remote access (optional)

**Cost:** $80 one-time (Pi 5), ~$5/year electricity

---

## Future Improvements (Tier 3+)

### Free/Low-Cost (<$20/mo)

| Feature | Description | Effort | Cost |
|---------|-------------|--------|------|
| **Telegram Bot** | Real-time alerts via Telegram instead of SMS | 3 hrs | Free |
| **Discord Integration** | Alert channel for community use | 2 hrs | Free |
| **Backtest Optimization** | Grid search for strategy parameters | 8 hrs | Free |
| **Options Chain Cache** | Redis cache for faster LEAPS analysis | 4 hrs | Free (local) |
| **Historical Whale Levels** | Track institutional accumulation zones | 4 hrs | Free |
| **Earnings Calendar Filter** | Avoid trades before earnings | 2 hrs | Free |
| **News Sentiment Feed** | RSS feed integration for real-time news | 4 hrs | Free |
| **Portfolio Rebalancer** | Suggest trades to hit target allocation | 6 hrs | Free |

### Medium Cost ($20-50/mo)

| Feature | Description | Effort | Cost |
|---------|-------------|--------|------|
| **Polygon.io Data** | Real-time market data (faster than Yahoo) | 4 hrs | $29/mo |
| **OpenAI Embeddings** | Semantic search through trade notes | 6 hrs | ~$10/mo |
| **Supabase Backend** | Hosted PostgreSQL + Auth | 8 hrs | Free-$25/mo |
| **Vercel Dashboard** | Modern web UI for results | 12 hrs | Free-$20/mo |

### Higher Cost (>$50/mo)

| Feature | Description | Effort | Cost |
|---------|-------------|--------|------|
| **Bloomberg API** | Institutional-grade data | N/A | $2k+/mo |
| **Alpaca Trading** | Paper + Live auto-execution | 10 hrs | Free (paper) |
| **ML Signal Ranker** | Train model on historical signals | 20 hrs | GPU costs |

---

## Next Steps (Recommended Order)

### Phase 1: Deploy Locally (Current)
```bash
# Test all new modules
python src/alpha_lab/alerts.py
python src/alpha_lab/scheduler.py --task briefing
python src/alpha_lab/trade_journal.py
python src/alpha_lab/watchlist.py create-presets
python src/alpha_lab/correlation_filter.py
python src/alpha_lab/multi_timeframe.py NVDA
python src/alpha_lab/options_greeks.py NVDA
```

### Phase 2: Set Up Alerts
```bash
# 1. Get SendGrid API key (free)
# https://sendgrid.com/free/

# 2. Set environment variables
export SENDGRID_API_KEY="your_key"
export ALERT_EMAIL="you@email.com"

# 3. Test
python src/alpha_lab/alerts.py
```

### Phase 3: Deploy to Cloud
```bash
# Option A: GitHub Actions
# Copy .github/workflows/daily_briefing.yml to repo

# Option B: Railway
# railway init && railway up
```

### Phase 4: Build Trading Routine
1. Morning: Run `scheduler.py --task briefing`
2. Pre-trade: Check `multi_timeframe.py` for alignment
3. Entry: Use `options_greeks.py` for strike selection
4. Post-trade: Log in `trade_journal.py`
5. Weekly: Review `correlation_filter.py` portfolio analysis

---

## Configuration Files Needed

### For Email Alerts (SendGrid)
```bash
# .env file (don't commit!)
SENDGRID_API_KEY=SG.xxxxx
ALERT_EMAIL=your@email.com
```

### For SMS Alerts (Twilio)
```bash
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_NUMBER=+1234567890
ALERT_PHONE=+1234567890
```

### For GitHub Actions
```yaml
# .github/workflows/daily_briefing.yml
name: Daily Briefing
on:
  schedule:
    - cron: '30 12 * * 1-5'  # 8:30 AM ET (UTC-4)
  workflow_dispatch:

jobs:
  briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/alpha_lab/scheduler.py --task briefing
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          ALERT_EMAIL: ${{ secrets.ALERT_EMAIL }}
```

---

## Success Metrics

Track these to measure system value:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Win Rate | >55% | Trade Journal |
| Profit Factor | >1.5 | Trade Journal |
| Regime Accuracy | >70% | Compare regime calls vs SPY performance |
| Alert Relevance | >80% | Manual review of alerts acted upon |
| Time Saved | >2 hrs/day | Compare to manual research time |

---

## Questions?

The system is designed to be modular. Each component can be:
- Run standalone via CLI
- Imported into other scripts
- Extended with new functionality

Start with the launcher (`python launcher.py`) and explore from there.

