# 🔬 Stock Research Platform

**Find growth stocks before the crowd. Track your research. Stay disciplined.**

A simple tool for serious investors who want to:
- Discover undercovered growth stocks (scans 11,000+ US stocks)
- Filter out garbage with AI moat analysis
- Track insider buying/selling (real-time SEC Form 4 data)
- Track your investment thesis over time
- Get alerts when stocks hit your price targets

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/stock-research.git
cd stock-research
pip install -r requirements.txt
```

### 2. Set Up API Keys

**OpenAI** (for AI moat analysis, ~$0.50/scan):
```bash
export OPENAI_API_KEY="your-key-here"
```

**Telegram** (optional, for alerts):
```bash
# Create configs/telegram.env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 3. Run

```bash
# Discover stocks with GPT moat filter
python3 src/research/smart_discovery.py --scan 300

# Analyze a specific stock (includes insider activity)
python deep_research.py AAPL

# Check insider buying/selling for any stock
python deep_research.py --insiders AAPL

# Scan your watchlist for insider buying
python deep_research.py --insiders

# Add to your watchlist
python deep_research.py --add AAPL

# Set your thesis & price targets
python deep_research.py --thesis AAPL

# Check if any watchlist stocks hit your targets
python deep_research.py --alerts
```

---

## 📖 How It Works

### Discovery Flow

```
11,552 US Stocks (from NASDAQ)
         ↓
    Numerical Filters
    - Market cap $300M - $10B
    - Revenue growth > 10%
    - FCF positive or path to profitability
         ↓
    ~20 candidates
         ↓
    GPT Moat Analysis
    - Auto-reject: banks, commodities, China ADRs
    - Rate competitive moat 1-10
    - Identify: recurring revenue, switching costs, network effects
         ↓
    ~5 vetted opportunities
         ↓
    📬 Telegram Alert
```

### Example Output

```
🧠 SMART DISCOVERY

Scanned → 19 numerical candidates
Rejected → 14 (banks, commodities, weak moat)
Passed → 5 real opportunities

═══ VETTED STOCKS ═══

✅ DSGX - Moat 7/10 🔄🔒🕸️💰
   Logistics SaaS for global supply chain
   $7.0B | +15% growth
   💡 Strong recurring revenue, high switching costs

😐 AVPT - Moat 5/10 🔄🔒
   Cloud data management for enterprises
   $2.7B | +24% growth
   💡 Growing but competitive market
```

---

## 🎯 Commands

| Command | Description |
|---------|-------------|
| `python3 src/research/smart_discovery.py` | Find stocks with GPT filter |
| `python deep_research.py TICKER` | Full analysis of a stock |
| `python deep_research.py --insiders TICKER` | Check insider buying/selling (SEC Form 4) |
| `python deep_research.py --insiders` | Scan watchlist for insider buying |
| `python deep_research.py --institutions TICKER` | Check 13F institutional holdings |
| `python deep_research.py --shorts TICKER` | Check short interest & squeeze risk |
| `python deep_research.py --add TICKER` | Add to watchlist |
| `python deep_research.py --thesis TICKER` | Set your thesis & targets |
| `python deep_research.py --alerts` | Check price alerts |
| `python deep_research.py` | View your watchlist |

---

## 💡 Philosophy

This tool is built on a simple belief:

> **The edge isn't finding stocks. It's doing the research and staying disciplined.**

### What This Tool Does
- ✅ Scans the entire US market (not just popular stocks)
- ✅ Filters out garbage (banks, commodities, weak moats)
- ✅ **Tracks insider buying** (real-time SEC data GPT doesn't have)
- ✅ Helps you track your thesis and targets
- ✅ Removes emotion with price alerts

### 🔥 Why Insider Tracking Matters

Insiders sell for many reasons (taxes, diversification, buying a house).
**But they BUY for only ONE reason: they think the stock will go up.**

This tool fetches real-time SEC Form 4 filings - data that ChatGPT doesn't have access to.

### What This Tool Doesn't Do
- ❌ Tell you what to buy
- ❌ Predict stock prices
- ❌ Replace your own research
- ❌ Work for day trading

---

## 💰 Cost

| Component | Cost |
|-----------|------|
| Stock data (yfinance) | Free |
| Ticker universe (NASDAQ) | Free |
| GPT moat analysis | ~$0.30-0.50 per scan |
| Telegram alerts | Free |
| **Total** | **~$5-10/month if used daily** |

---

## 📁 Project Structure

```
stock-research/
├── deep_research.py          # Main entry point
├── src/
│   ├── research/
│   │   ├── smart_discovery.py    # Discovery + GPT filter
│   │   ├── discovery.py          # Universe scanning
│   │   ├── moat_analyzer.py      # GPT moat analysis
│   │   ├── insider_tracker.py    # SEC Form 4 insider data (GPT can't do this!)
│   │   ├── fundamentals.py       # Financial analysis
│   │   ├── business.py           # Business analysis
│   │   └── database.py           # Research storage
│   └── alpha_lab/
│       └── telegram_alerts.py    # Telegram integration
├── configs/
│   └── telegram.env.example      # Telegram config template
├── data/                         # Your research data (gitignored)
└── requirements.txt
```

---

## 🤝 Contributing

This is a personal research tool shared with friends. Feel free to:
- Fork and customize for your needs
- Open issues for bugs
- Submit PRs for improvements

---

## ⚠️ Disclaimer

This tool is for **research purposes only**. It does not provide investment advice.

- Do your own due diligence
- Past performance doesn't guarantee future results
- Never invest money you can't afford to lose

---

## 📜 License

MIT License - Use it however you want.
