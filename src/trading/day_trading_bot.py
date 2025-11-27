#!/usr/bin/env python3
"""
Robust Day Trading Bot - Interactive Brokers IB Gateway Integration
==================================================================

SYSTEM REQUIREMENTS & SETUP:
----------------------------
1. Install dependencies:
   pip install ib_insync pandas numpy yfinance pytz

2. IB Gateway Setup:
   - Download and install IB Gateway from Interactive Brokers
   - Run IB Gateway in headless/server mode
   - Configure API settings:
     * Enable API connections
     * Set port: 4002 (paper trading) or 4001 (live trading)
     * Add trusted IP: 127.0.0.1
     * Set client ID: any unique number

3. No graphical interface required - runs in terminal/console

CONFIGURATION:
--------------
All settings are configurable via the CONFIG section below.
Default connection: 127.0.0.1:4002 (paper trading)

STRATEGY:
---------
VWAP Long Strategy for gap-up stocks:
- Scan for market cap >$1B, gap >3%, pre-market volume >20K
- Enter long when price tests and holds VWAP after gap up
- Stop loss: 5-min close below VWAP
- Take profit: 2% above VWAP or next resistance level
"""

import asyncio
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, time
import pytz
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Dict, List, Optional, Tuple
import time as time_module

try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder
    from ib_insync import util
    IB_AVAILABLE = True
except ImportError:
    print("❌ ib_insync not installed. Run: pip install ib_insync")
    IB_AVAILABLE = False
    exit(1)

# ==================================================================================
# CONFIGURATION - MODIFY THESE SETTINGS
# ==================================================================================

CONFIG = {
    # IB Gateway Connection
    'IB_HOST': '127.0.0.1',
    'IB_PORT': 4002,  # 4002 = Paper Trading, 4001 = Live Trading
    'CLIENT_ID': 100,  # Unique client ID
    'TIMEOUT': 10,
    
    # Trading Mode
    'SCAN_ONLY_MODE': False,   # Set to True to analyze without executing trades
    
    # Trading Parameters
    'MAX_POSITION_PCT': 10.0,  # Max 10% of buying power per position
    'MAX_POSITIONS': 3,        # Maximum concurrent positions
    
    # Risk Management (Humble Trader Style)
    'USE_DOLLAR_STOPS': True,  # Use dollar stops instead of percentage
    'STOP_LOSS_DOLLARS': 0.25, # $0.25 stop loss (day trading)
    'STOP_LOSS_PCT': 2.0,      # 2% stop loss (fallback for high-priced stocks)
    'TAKE_PROFIT_DOLLARS': 0.50, # $0.50 take profit (2:1 reward/risk)
    'TAKE_PROFIT_PCT': 2.0,    # 2% take profit (fallback)
    'MAX_RISK_PER_TRADE': 100, # Maximum $100 risk per trade
    
    # Scaling Out (Humble Trader Style)
    'SCALE_OUT_ENABLED': True, # Sell in increments
    'FIRST_TARGET_PCT': 50,    # Sell 50% of position at first target
    'SECOND_TARGET_PCT': 50,   # Sell remaining 50% at second target
    'FIRST_TARGET_MULTIPLIER': 0.5,  # First target at 0.5x of full target
    'MOVE_STOP_TO_BREAKEVEN': True,  # Move stop to breakeven after first target
    
    # Scanning Criteria (LOWERED FOR TESTING)
    'MIN_MARKET_CAP': 100e6,   # $100M minimum market cap (was $1B)
    'MIN_GAP_PCT': 1.0,        # 1% minimum overnight gap (was 3%)
    'MIN_PREMARKET_VOLUME': 5000,   # 5K minimum pre-market volume (was 20K)
    'MAX_PRICE': 1000.0,       # Maximum stock price for scanning (was $500)
    'REQUIRE_NEWS_CATALYST': True,  # Only trade stocks with recent news (Humble Trader style)
    'NEWS_MAX_AGE_HOURS': 24,  # News must be within 24 hours
    'REQUIRE_SPY_BULLISH': True,  # Only trade if SPY is green (don't fight market)
    'SPY_MIN_CHANGE_PCT': -0.3,  # Allow if SPY down less than 0.3%
    
    # Technical Analysis (LOWERED FOR TESTING)
    'VWAP_PERIODS': [2, 5],    # 2min and 5min bars for VWAP
    'VOLUME_CONFIRM_THRESHOLD': 100000,   # 100K shares in first 30min (was 1M)
    'RESISTANCE_LOOKBACK': 3,  # Days to look back for resistance (was 5)
    
    # Options Scanning (Optimized for smaller, volatile stocks)
    'SCAN_OPTIONS': True,           # Enable options scanning
    'MIN_OPTIONS_VOLUME': 100,     # Lower threshold for smaller stocks
    'MIN_OPTIONS_OI': 50,          # Lower OI threshold for smaller stocks
    'MAX_OPTIONS_DAYS': 45,        # Extended expiration window
    'MIN_OPTIONS_DELTA': 0.2,      # Lower delta threshold (20% chance ITM)
    'UNUSUAL_VOLUME_MULTIPLIER': 1.5,  # Lower multiplier for more sensitive detection
    
    # Risk Management
    'MAX_DAILY_LOSS': 1000.0,  # Maximum daily loss limit
    'MAX_DAILY_TRADES': 10,    # Maximum trades per day
    
    # Logging & Alerts
    'LOG_LEVEL': 'INFO',
    'ENABLE_EMAIL_ALERTS': False,
    'EMAIL_HOST': 'smtp.gmail.com',
    'EMAIL_PORT': 587,
    'EMAIL_USER': '',  # Your email
    'EMAIL_PASS': '',  # Your app password
    'EMAIL_TO': '',    # Alert recipient
}

# ==================================================================================
# LOGGING SETUP
# ==================================================================================

def setup_logging():
    """Setup comprehensive logging system."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Setup file logging
    today = datetime.now().strftime('%Y%m%d')
    log_filename = f'logs/trading_bot_{today}.log'
    
    logging.basicConfig(
        level=getattr(logging, CONFIG['LOG_LEVEL']),
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger(__name__)

# ==================================================================================
# MAIN TRADING BOT CLASS
# ==================================================================================

class DayTradingBot:
    """Robust day trading bot with VWAP strategy and IB Gateway integration."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logging()
        self.ib = IB()
        self.connected = False
        
        # Initialize trade tracker for performance validation
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from utils.trade_tracker import TradeTracker
            self.trade_tracker = TradeTracker()
            self.logger.info("📊 Trade tracker initialized for performance validation")
        except Exception as e:
            self.trade_tracker = None
            self.logger.warning(f"⚠️ Trade tracker not available: {e}")
        
        # Trading state
        self.positions = {}
        self.daily_pnl = 0.0
        self.trade_count = 0
        self.candidates = []
        self.market_data = {}
        
        # Technical indicators
        self.vwap_data = {}
        self.support_resistance = {}
        
        self.logger.info("🤖 Day Trading Bot initialized")
        self.logger.info(f"📊 Config: {config['IB_HOST']}:{config['IB_PORT']} (Client ID: {config['CLIENT_ID']})")
    
    async def connect_to_ib(self) -> bool:
        """Establish persistent connection to IB Gateway."""
        # Skip connection in scan-only mode
        if self.config.get('SCAN_ONLY_MODE', False):
            self.logger.info("🔍 SCAN-ONLY MODE: Skipping IB Gateway connection")
            self.connected = False
            return True  # Return True to continue without connection
        
        try:
            self.logger.info("🔌 Connecting to IB Gateway...")
            
            await self.ib.connectAsync(
                host=self.config['IB_HOST'],
                port=self.config['IB_PORT'], 
                clientId=self.config['CLIENT_ID'],
                timeout=self.config['TIMEOUT']
            )
            
            self.connected = True
            self.logger.info("✅ Connected to IB Gateway successfully")
            
            # Get account info
            account = self.ib.managedAccounts()[0]
            self.logger.info(f"📊 Trading Account: {account}")
            
            # Sync existing positions
            await self.sync_existing_positions()
            
            # Set up portfolio updates for real-time P&L tracking
            self.ib.updatePortfolioEvent += self.on_portfolio_update
            
            # Request current market data for all positions
            await self.request_market_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ IB Gateway connection failed: {e}")
            self.logger.error("💡 Make sure IB Gateway is running with API enabled")
            return False
    
    async def sync_existing_positions(self):
        """Sync existing positions from IBKR on startup."""
        if not self.connected:
            return
            
        try:
            self.logger.info("🔄 Syncing existing positions...")
            
            # Get all positions from IBKR
            positions = self.ib.positions()
            
            if not positions:
                self.logger.info("📊 No existing positions found")
                return
            
            # Clear existing positions dict
            self.positions = {}
            
            for position in positions:
                symbol = position.contract.symbol
                shares = position.position
                avg_cost = position.avgCost
                
                if shares == 0:
                    continue
                    
                # Add to positions dict with realistic targets
                self.positions[symbol] = {
                    'shares': abs(shares),
                    'shares_remaining': abs(shares),
                    'entry_price': avg_cost,
                    'entry_time': datetime.now(),
                    'side': 'LONG' if shares > 0 else 'SHORT',
                    'stop_price': avg_cost * 0.96,  # 4% stop loss
                    'take_profit_price': avg_cost * 1.025,  # 2.5% take profit
                    'scaled_out': False,
                    'breakeven_moved': False
                }
                
                self.logger.info(f"📊 Synced existing position: {symbol} - {abs(shares)} shares @ ${avg_cost:.2f}")
            
            self.logger.info(f"✅ Synced {len(self.positions)} existing positions")
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing positions: {e}")

    async def request_market_data(self):
        """Request current market data for all positions."""
        if not self.connected:
            return
            
        try:
            for symbol in self.positions.keys():
                contract = Stock(symbol, 'SMART', 'USD')
                self.ib.reqMktData(contract, '', False, False)
                self.logger.debug(f"📊 Requested market data for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ Error requesting market data: {e}")

    def on_portfolio_update(self, portfolio_item):
        """Handle real-time portfolio updates from IBKR."""
        try:
            symbol = portfolio_item.contract.symbol
            position = portfolio_item.position
            market_price = portfolio_item.marketPrice
            unrealized_pnl = portfolio_item.unrealizedPNL
            
            if symbol in self.positions:
                # Update existing position with real-time data
                self.positions[symbol]['current_price'] = market_price
                self.positions[symbol]['unrealized_pnl'] = unrealized_pnl
                
                # Log significant P&L changes
                if abs(unrealized_pnl) > 10:  # Log if P&L > $10
                    self.logger.info(f"💰 {symbol}: ${unrealized_pnl:.2f} P&L @ ${market_price:.2f}")
                    
        except Exception as e:
            self.logger.debug(f"Portfolio update error: {e}")

    def disconnect_from_ib(self):
        """Safely disconnect from IB Gateway."""
        if self.connected:
            try:
                self.ib.disconnect()
                self.connected = False
                self.logger.info("🔌 Disconnected from IB Gateway")
            except Exception as e:
                self.logger.error(f"⚠️ Disconnect error: {e}")
    
    def is_market_hours(self) -> bool:
        """Check if US market is open for trading."""
        try:
            et_tz = pytz.timezone('US/Eastern')
            now = datetime.now(et_tz)
            
            # Market hours: Monday-Friday, 9:30 AM - 4:00 PM ET
            if now.weekday() >= 5:  # Weekend
                return False
            
            # Get today's market hours with proper timezone
            today = now.date()
            from datetime import time
            market_open = et_tz.localize(datetime.combine(today, time(9, 30)))
            market_close = et_tz.localize(datetime.combine(today, time(16, 0)))
            
            return market_open <= now <= market_close
        except Exception:
            return False
    
    def is_premarket_hours(self) -> bool:
        """Check if we're in pre-market hours (4:00 AM - 9:30 AM ET)."""
        try:
            et_tz = pytz.timezone('US/Eastern')
            now = datetime.now(et_tz)
            
            if now.weekday() >= 5:  # Weekend
                return False
            
            premarket_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            
            return premarket_start <= now < market_open
        except Exception:
            return False
    
    async def scan_gap_up_candidates(self) -> List[Dict]:
        """Scan for gap-up candidates meeting our criteria."""
        self.logger.info("🔍 Scanning for gap-up candidates...")
        
        candidates = []
        
        # Sample list of liquid stocks to scan (REDUCED FOR SPEED)
        scan_universe = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'AMD', 'INTC', 'SPY', 'QQQ', 'IWM'
        ]
        
        for symbol in scan_universe:
            try:
                # Get basic data via yfinance (free source)
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period='5d', interval='1d')
                
                if len(hist) < 2:
                    continue
                
                current_price = info.get('currentPrice', hist['Close'].iloc[-1])
                prev_close = hist['Close'].iloc[-2]
                market_cap = info.get('marketCap', 0)
                
                # Calculate overnight gap
                gap_pct = ((current_price - prev_close) / prev_close * 100)
                
                # Check criteria
                if (market_cap >= self.config['MIN_MARKET_CAP'] and
                    gap_pct >= self.config['MIN_GAP_PCT'] and
                    current_price <= self.config['MAX_PRICE']):
                    
                    # Get pre-market volume (placeholder - would need real-time data)
                    premarket_volume = info.get('averageVolume', 0) * 0.1  # Estimate
                    
                    if premarket_volume >= self.config['MIN_PREMARKET_VOLUME']:
                        candidate = {
                            'symbol': symbol,
                            'current_price': current_price,
                            'prev_close': prev_close,
                            'gap_pct': gap_pct,
                            'market_cap': market_cap,
                            'premarket_volume': premarket_volume,
                            'avg_volume': info.get('averageVolume', 0)
                        }
                        candidates.append(candidate)
                        
                        self.logger.info(f"✅ Candidate: {symbol} - Gap: {gap_pct:.1f}%, Volume: {premarket_volume:,.0f}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Scan error for {symbol}: {str(e)[:50]}")
                continue
        
        self.logger.info(f"🎯 Found {len(candidates)} gap-up candidates")
        return candidates

    async def get_high_options_activity_stocks(self) -> List[str]:
        """Dynamically find stocks with high options activity based on real market data."""
        try:
            import yfinance as yf
            import pandas as pd
            
            # Get stocks with high volume and volatility today
            high_activity_stocks = []
            
            # Start with a broad universe of potentially active stocks
            candidate_tickers = [
                # Major tech
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
                # High growth tech
                'PLTR', 'SOFI', 'RBLX', 'HOOD', 'COIN', 'UPST', 'AFRM', 'SQ', 'PYPL', 'ADBE',
                # Meme stocks
                'GME', 'AMC', 'BB', 'NOK', 'WISH', 'CLOV', 'SPCE', 'RKT', 'WKHS', 'NKLA',
                # Crypto-related
                'MSTR', 'RIOT', 'MARA', 'HUT', 'BITF', 'CAN', 'EBON', 'COIN', 'HOOD',
                # Biotech/pharma
                'MRNA', 'BNTX', 'NVAX', 'OCGN', 'INO', 'VXRT', 'SRPT', 'BIIB', 'GILD', 'JNJ',
                # ETFs with high options volume
                'SPY', 'QQQ', 'IWM', 'DIA', 'TQQQ', 'SQQQ', 'SPXL', 'SPXS', 'UVXY', 'VXX',
                # Small caps with options
                'LCID', 'RIVN', 'F', 'GM', 'FORD', 'NIO', 'XPEV', 'LI', 'BABA', 'JD'
            ]
            
            # Filter stocks based on real-time criteria
            filtered_stocks = []
            
            for ticker in candidate_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # Get current market data
                    market_cap = info.get('marketCap', 0)
                    avg_volume = info.get('averageVolume', 0)
                    current_volume = info.get('volume', 0)
                    price = info.get('currentPrice', 0)
                    beta = info.get('beta', 1.0)
                    
                    # Filter criteria for options scanning:
                    # 1. Market cap between $100M and $100B (liquid but not too big)
                    # 2. High volume today (at least 1.5x average)
                    # 3. Reasonable price ($5-$500)
                    # 4. High beta (volatile stocks)
                    if (100_000_000 <= market_cap <= 100_000_000_000 and
                        current_volume > avg_volume * 1.5 and
                        avg_volume > 50_000 and
                        5 <= price <= 500 and
                        beta > 1.2):
                        
                        filtered_stocks.append(ticker)
                        
                except Exception as e:
                    # Skip stocks with data issues
                    continue
            
            # Sort by volume and return top candidates
            if filtered_stocks:
                # Get volume data for sorting
                volume_data = []
                for ticker in filtered_stocks:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        volume = info.get('volume', 0)
                        volume_data.append((ticker, volume))
                    except:
                        continue
                
                # Sort by volume and return top 15
                volume_data.sort(key=lambda x: x[1], reverse=True)
                return [ticker for ticker, _ in volume_data[:15]]
            else:
                # Fallback to a curated list if filtering fails
                return [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
                    'PLTR', 'SOFI', 'RBLX', 'HOOD', 'COIN', 'UPST', 'AFRM', 'SQ',
                    'GME', 'AMC', 'BB', 'NOK', 'WISH', 'CLOV', 'SPCE', 'RKT',
                    'MSTR', 'RIOT', 'MARA', 'HUT', 'BITF', 'CAN', 'EBON',
                    'MRNA', 'BNTX', 'NVAX', 'OCGN', 'INO', 'VXRT', 'SRPT', 'BIIB',
                    'SPY', 'QQQ', 'IWM', 'TQQQ', 'SQQQ', 'SPXL', 'SPXS', 'UVXY', 'VXX'
                ]
                
        except Exception as e:
            self.logger.error(f"Error getting high options activity stocks: {e}")
            # Ultimate fallback
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'SPY', 'QQQ']

    async def is_market_favorable(self) -> Tuple[bool, float]:
        """Check if overall market (SPY) is favorable for long trades."""
        if not self.config.get('REQUIRE_SPY_BULLISH', False):
            return True, 0.0
        
        try:
            import yfinance as yf
            
            spy = yf.Ticker('SPY')
            hist = spy.history(period='1d', interval='1m')
            
            if hist.empty:
                self.logger.warning("⚠️ Could not get SPY data - allowing trade")
                return True, 0.0
            
            # Calculate SPY change today
            current_price = hist['Close'].iloc[-1]
            open_price = hist['Open'].iloc[0]
            spy_change_pct = (current_price - open_price) / open_price * 100
            
            min_change = self.config.get('SPY_MIN_CHANGE_PCT', -0.3)
            is_favorable = spy_change_pct >= min_change
            
            if not is_favorable:
                self.logger.info(f"⚠️ SPY filter: Market down {spy_change_pct:.2f}% (threshold: {min_change}%) - Skipping longs")
            
            return is_favorable, spy_change_pct
            
        except Exception as e:
            self.logger.warning(f"⚠️ SPY check failed: {e} - Allowing trade")
            return True, 0.0
    
    async def has_recent_news(self, symbol: str) -> Tuple[bool, str]:
        """Check if stock has recent news/catalyst (Humble Trader requirement)."""
        if not self.config.get('REQUIRE_NEWS_CATALYST', False):
            return True, "News filter disabled"
        
        try:
            import yfinance as yf
            from datetime import datetime, timedelta
            
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news or len(news) == 0:
                return False, "No recent news found"
            
            # Check for news within configured time window
            max_age_hours = self.config.get('NEWS_MAX_AGE_HOURS', 24)
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for article in news[:5]:  # Check latest 5 articles
                try:
                    # Get publish time
                    if 'providerPublishTime' in article:
                        pub_time = datetime.fromtimestamp(article['providerPublishTime'])
                    elif 'published' in article:
                        pub_time = datetime.fromtimestamp(article['published'])
                    else:
                        continue
                    
                    if pub_time >= cutoff_time:
                        # Extract title
                        title = ''
                        if isinstance(article, dict):
                            if 'title' in article:
                                title = article['title']
                            elif 'content' in article and isinstance(article['content'], dict):
                                title = article['content'].get('title', '')
                        
                        if title:
                            return True, f"Catalyst: {title[:60]}..."
                        else:
                            return True, "Recent news found"
                
                except:
                    continue
            
            return False, f"No news within {max_age_hours} hours"
            
        except Exception as e:
            # If news check fails, allow trade (don't break the bot)
            self.logger.warning(f"⚠️ News check failed for {symbol}: {e}")
            return True, "News check failed - allowing trade"
    
    async def scan_unusual_options_activity(self) -> List[Dict]:
        """Scan for unusual call options activity."""
        unusual_options = []
        
        if not self.config['SCAN_OPTIONS']:
            return unusual_options
        
        # Skip scanning during after-hours (yfinance data is stale)
        if not self.is_market_hours():
            return unusual_options
            
        try:
            # Dynamic market scanning - find stocks with high options activity
            options_stocks = await self.get_high_options_activity_stocks()
            
            for symbol in options_stocks:
                try:
                    # Get options chain
                    ticker = yf.Ticker(symbol)
                    options_chain = ticker.option_chain()
                    
                    if not options_chain or not hasattr(options_chain, 'calls'):
                        continue
                    
                    calls = options_chain.calls
                    if calls.empty:
                        continue
                    
                    # Filter for unusual activity
                    for _, option in calls.iterrows():
                        try:
                            # Check if required fields exist
                            if not all(field in option for field in ['volume', 'openInterest', 'strike']):
                                continue
                                
                            # Get days to expiration safely
                            days_to_exp = option.get('daysToExpiration', 999)  # Default to far future if missing
                            
                            # Basic filters
                            if (option['volume'] >= self.config['MIN_OPTIONS_VOLUME'] and
                                option['openInterest'] >= self.config['MIN_OPTIONS_OI'] and
                                days_to_exp <= self.config['MAX_OPTIONS_DAYS']):
                                
                                # Calculate unusual volume using volume/OI ratio (more reliable)
                                # "Unusual" = today's volume is high relative to open interest
                                # Normal ratio: 0.1-0.3, Unusual ratio: > 0.5
                                oi = option['openInterest']
                                volume = option['volume']
                                
                                # Volume/OI ratio method (works without historical data)
                                volume_oi_ratio = volume / max(oi, 1)
                                
                                # Flag as unusual if:
                                # 1. Volume > 50% of open interest (unusual activity)
                                # 2. Absolute volume > 500 (meaningful)
                                if volume_oi_ratio >= 0.5 and volume >= 500:
                                    # Calculate delta (simplified approximation)
                                    current_price = option.get('underlyingPrice', 0)
                                    strike = option['strike']
                                    
                                    # Simple delta approximation
                                    if current_price > 0 and strike > 0:
                                        delta = max(0, min(1, (current_price - strike) / current_price + 0.5))
                                        
                                        if delta >= self.config['MIN_OPTIONS_DELTA']:
                                            unusual_option = {
                                                'symbol': symbol,
                                                'option_type': 'CALL',  # Fixed: Add missing field
                                                'contract': option.get('contractSymbol', f'{symbol}_{strike}'),
                                                'strike': strike,
                                                'expiration': option.get('lastTradeDate', 'Unknown'),
                                                'volume': volume,
                                                'open_interest': oi,
                                                'volume_oi_ratio': volume_oi_ratio,
                                                'delta': delta,
                                                'current_price': current_price,
                                                'option_price': option.get('lastPrice', 0),
                                                'days_to_exp': days_to_exp
                                            }
                                            
                                            unusual_options.append(unusual_option)
                                            
                        except Exception as e:
                            # Only log if it's not a common missing field error
                            if 'daysToExpiration' not in str(e) and 'contractSymbol' not in str(e):
                                self.logger.warning(f"Error processing option for {symbol}: {e}")
                            continue
                            
                except Exception as e:
                    self.logger.warning(f"Error scanning options for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in options scan: {e}")
            
        # Sort by volume/OI ratio (most unusual first)
        unusual_options.sort(key=lambda x: x['volume_oi_ratio'], reverse=True)
        
        # Log results appropriately
        if unusual_options:
            self.logger.info(f"🎯 Found {len(unusual_options)} unusual options")
        elif self.is_market_hours():
            self.logger.info("📊 No unusual options activity found (market hours)")
        # Don't log anything after hours (reduces noise)
        
        return unusual_options[:10]  # Return top 10
    
    async def get_support_resistance(self, symbol: str) -> Dict:
        """Calculate support/resistance levels using IB historical data."""
        try:
            if not self.connected:
                return {}
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            
            if not qualified:
                return {}
            
            stock = qualified[0]
            
            # Get 5 days of historical data
            bars = self.ib.reqHistoricalData(
                stock,
                endDateTime='',
                durationStr='5 D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if not bars:
                return {}
            
            # Calculate support/resistance from recent highs/lows
            highs = [bar.high for bar in bars[-self.config['RESISTANCE_LOOKBACK']:]]
            lows = [bar.low for bar in bars[-self.config['RESISTANCE_LOOKBACK']:]]
            
            resistance = max(highs) if highs else 0
            support = min(lows) if lows else 0
            
            return {
                'resistance': resistance,
                'support': support,
                'recent_high': highs[-1] if highs else 0,
                'recent_low': lows[-1] if lows else 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ Support/resistance error for {symbol}: {e}")
            return {}
    
    async def calculate_vwap(self, symbol: str, period_minutes: int = 5) -> float:
        """Calculate real-time VWAP using IB Gateway data."""
        try:
            if not self.connected:
                return 0.0
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            
            if not qualified:
                return 0.0
            
            stock = qualified[0]
            
            # Get intraday bars from market open
            et_tz = pytz.timezone('US/Eastern')
            now = datetime.now(et_tz)
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            
            # Calculate duration from market open to now
            if now < market_open:
                return 0.0  # Before market open
            
            duration_minutes = int((now - market_open).total_seconds() / 60)
            duration_str = f"{max(1, duration_minutes)} S"  # Seconds format for intraday
            
            bars = self.ib.reqHistoricalData(
                stock,
                endDateTime='',
                durationStr=duration_str,
                barSizeSetting=f'{period_minutes} mins',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if not bars:
                return 0.0
            
            # Calculate VWAP
            total_volume = 0
            total_pv = 0  # Price * Volume
            
            for bar in bars:
                typical_price = (bar.high + bar.low + bar.close) / 3
                volume = bar.volume
                
                total_pv += typical_price * volume
                total_volume += volume
            
            vwap = total_pv / total_volume if total_volume > 0 else 0.0
            
            self.logger.debug(f"📊 {symbol} VWAP ({period_minutes}min): ${vwap:.2f}")
            return vwap
            
        except Exception as e:
            self.logger.error(f"❌ VWAP calculation error for {symbol}: {e}")
            return 0.0
    
    async def check_entry_signal(self, candidate: Dict) -> bool:
        """Check if candidate meets VWAP long entry criteria."""
        symbol = candidate['symbol']
        current_price = candidate['current_price']
        
        try:
            # Get support/resistance levels
            levels = await self.get_support_resistance(symbol)
            if not levels:
                return False
            
            # Calculate VWAP
            vwap_5min = await self.calculate_vwap(symbol, 5)
            if vwap_5min <= 0:
                return False
            
            # Get current market data
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            if not qualified:
                return False
            
            stock = qualified[0]
            ticker = self.ib.reqMktData(stock, '', False, False)
            await asyncio.sleep(2)  # Wait for data
            
            current_price = ticker.last if ticker.last > 0 else ticker.close
            
            # Entry criteria:
            # 1. Gap opened above resistance
            gap_above_resistance = candidate['current_price'] > levels['resistance']
            
            # 2. Current price is testing/holding VWAP (within 3% - LOWERED FOR TESTING)
            vwap_test = abs(current_price - vwap_5min) / vwap_5min <= 0.03
            
            # 3. Price is above VWAP (for long strategy)
            above_vwap = current_price >= vwap_5min
            
            # 4. Volume confirmation (simplified - would need real-time volume)
            volume_confirmed = True  # Placeholder for real volume check
            
            entry_signal = (gap_above_resistance and vwap_test and 
                          above_vwap and volume_confirmed)
            
            if entry_signal:
                self.logger.info(f"🎯 ENTRY SIGNAL: {symbol} at ${current_price:.2f}")
                self.logger.info(f"   Gap above resistance: {gap_above_resistance}")
                self.logger.info(f"   VWAP: ${vwap_5min:.2f}")
                self.logger.info(f"   Above VWAP: {above_vwap}")
            
            # Store technical data
            self.support_resistance[symbol] = levels
            self.vwap_data[symbol] = vwap_5min
            
            self.ib.cancelMktData(stock)
            return entry_signal
            
        except Exception as e:
            self.logger.error(f"❌ Entry signal error for {symbol}: {e}")
            return False
    
    async def test_order_placement(self, symbol: str = "AAPL") -> bool:
        """Test order placement with a small paper trade."""
        try:
            self.logger.info(f"🧪 TESTING ORDER PLACEMENT: {symbol}")
            
            # Get current price
            contract = Stock(symbol, 'SMART', 'USD')
            ticker = self.ib.reqMktData(contract)
            await asyncio.sleep(2)  # Wait for data
            
            if not ticker.last:
                self.logger.error(f"❌ No price data for {symbol}")
                return False
                
            current_price = ticker.last
            self.logger.info(f"📊 Current {symbol} price: ${current_price:.2f}")
            
            # Create a small test order (1 share)
            order = MarketOrder('BUY', 1)
            order.transmit = True
            
            # Place the order
            trade = self.ib.placeOrder(contract, order)
            self.logger.info(f"✅ TEST ORDER PLACED: {symbol} @ ${current_price:.2f}")
            
            # Wait a moment then cancel (paper trading)
            await asyncio.sleep(3)
            self.ib.cancelOrder(order)
            self.logger.info(f"🔄 TEST ORDER CANCELLED: {symbol}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Test order failed: {e}")
            return False

    async def execute_long_entry(self, symbol: str, current_price: float) -> bool:
        """Execute long entry order via IB Gateway."""
        try:
            # SCAN ONLY MODE - Just log the opportunity, don't trade
            if self.config.get('SCAN_ONLY_MODE', False):
                self.logger.info(f"📊 SCAN ONLY: Would enter {symbol} @ ${current_price:.2f}")
                self.logger.info(f"   This is an analysis-only mode. No trades executed.")
                return False  # Don't actually execute
            
            if not self.connected:
                return False
            
            # Check position limits
            if len(self.positions) >= self.config['MAX_POSITIONS']:
                self.logger.warning(f"⚠️ Max positions reached ({self.config['MAX_POSITIONS']})")
                return False
            
            # Calculate position size based on buying power
            account_values = self.ib.accountValues()
            buying_power = 0
            
            for value in account_values:
                if value.tag == 'BuyingPower':
                    buying_power = float(value.value)
                    break
            
            if buying_power <= 0:
                self.logger.error("❌ No buying power available")
                return False
            
            # Calculate shares based on dollar risk (Humble Trader style)
            if self.config.get('USE_DOLLAR_STOPS', False):
                # Risk-based position sizing
                stop_loss_dollars = self.config.get('STOP_LOSS_DOLLARS', 0.25)
                max_risk = self.config.get('MAX_RISK_PER_TRADE', 100)
                
                # Calculate max shares based on risk
                shares_from_risk = int(max_risk / stop_loss_dollars)
                
                # Also respect max position percentage
                max_investment = buying_power * (self.config['MAX_POSITION_PCT'] / 100)
                shares_from_capital = int(max_investment / current_price)
                
                # Use smaller of the two (more conservative)
                shares = min(shares_from_risk, shares_from_capital)
            else:
                # Original method: max % of buying power
                max_investment = buying_power * (self.config['MAX_POSITION_PCT'] / 100)
                shares = int(max_investment / current_price)
            
            if shares <= 0:
                self.logger.warning(f"⚠️ Position size too small for {symbol}")
                return False
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            
            if not qualified:
                self.logger.error(f"❌ Could not qualify contract for {symbol}")
                return False
            
            stock = qualified[0]
            
            # Place limit order slightly above current price
            limit_price = current_price * 1.001  # 0.1% above current
            
            order = LimitOrder('BUY', shares, limit_price)
            trade = self.ib.placeOrder(stock, order)
            
            self.logger.info(f"📈 LONG ENTRY: {symbol} - {shares} shares @ ${limit_price:.2f}")
            
            # Store position info with dollar-based stops
            vwap = self.vwap_data.get(symbol, current_price)
            
            # Calculate stop and target prices (Humble Trader style)
            if self.config.get('USE_DOLLAR_STOPS', False):
                stop_price = limit_price - self.config.get('STOP_LOSS_DOLLARS', 0.25)
                target_dollars = self.config.get('TAKE_PROFIT_DOLLARS', 0.50)
                take_profit_price = limit_price + target_dollars
                first_target_price = limit_price + (target_dollars * self.config.get('FIRST_TARGET_MULTIPLIER', 0.5))
            else:
                # Percentage-based (original)
                stop_price = vwap * (1 - self.config['STOP_LOSS_PCT'] / 100)
                take_profit_price = vwap * (1 + self.config['TAKE_PROFIT_PCT'] / 100)
                first_target_price = (vwap + take_profit_price) / 2  # Midpoint
            
            self.positions[symbol] = {
                'shares': shares,
                'shares_remaining': shares,  # Track for scaling out
                'entry_price': limit_price,
                'entry_time': datetime.now(),
                'vwap_entry': vwap,
                'stop_price': stop_price,
                'take_profit_price': take_profit_price,
                'first_target_price': first_target_price,
                'first_target_hit': False,  # Track scaling progress
                'stop_moved_to_breakeven': False,
                'trade_id': trade.order.orderId
            }
            
            # Record entry in trade tracker
            if self.trade_tracker:
                try:
                    tracker_id = self.trade_tracker.record_entry(
                        symbol=symbol,
                        entry_price=limit_price,
                        shares=shares,
                        stop_price=stop_price,
                        target_price=take_profit_price,
                        entry_reason=f"Gap up + VWAP @ ${vwap:.2f}"
                    )
                    self.positions[symbol]['tracker_id'] = tracker_id
                    self.logger.info(f"📊 Trade recorded in tracker (ID: {tracker_id})")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to record trade in tracker: {e}")
            
            self.trade_count += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Entry execution error for {symbol}: {e}")
            return False
    
    async def monitor_positions(self):
        """Monitor open positions for exit signals."""
        if not self.positions:
            return
        
        self.logger.debug("👁️ Monitoring positions...")
        
        for symbol, position in list(self.positions.items()):
            try:
                # Get current price
                stock = Stock(symbol, 'SMART', 'USD')
                qualified = self.ib.qualifyContracts(stock)
                
                if not qualified:
                    continue
                
                stock = qualified[0]
                ticker = self.ib.reqMktData(stock, '', False, False)
                await asyncio.sleep(1)
                
                current_price = ticker.last if ticker.last > 0 else ticker.close
                shares_remaining = position.get('shares_remaining', position['shares'])
                
                # Skip if position already closed
                if shares_remaining <= 0:
                    del self.positions[symbol]
                    continue
                
                # SCALING OUT LOGIC:
                if self.config.get('SCALE_OUT_ENABLED', False):
                    # Check first target (sell 50%)
                    if (not position.get('first_target_hit', False) and 
                        current_price >= position['first_target_price']):
                        
                        shares_to_sell = int(position['shares'] * 0.5)
                        await self.execute_partial_exit(symbol, shares_to_sell, current_price, "First target hit")
                        
                        position['first_target_hit'] = True
                        position['shares_remaining'] = shares_remaining - shares_to_sell
                        
                        # Move stop to breakeven
                        if self.config.get('MOVE_STOP_TO_BREAKEVEN', False):
                            position['stop_price'] = position['entry_price']
                            position['stop_moved_to_breakeven'] = True
                            self.logger.info(f"📍 {symbol} - Stop moved to breakeven ${position['entry_price']:.2f}")
                    
                    # Check second target (sell remaining)
                    elif (position.get('first_target_hit', False) and 
                          current_price >= position['take_profit_price']):
                        await self.execute_exit(symbol, current_price, "Final target hit")
                    
                    # Check stop loss
                    elif current_price <= position['stop_price']:
                        await self.execute_exit(symbol, current_price, "Stop loss hit")
                    
                    # Time-based exit (near market close)
                    elif self.is_near_market_close():
                        await self.execute_exit(symbol, current_price, "End of day exit")
                
                else:
                    # Original all-or-nothing logic
                    if current_price >= position['take_profit_price']:
                        await self.execute_exit(symbol, current_price, "Take profit hit")
                    elif current_price <= position['stop_price']:
                        await self.execute_exit(symbol, current_price, "Stop loss hit")
                    elif self.is_near_market_close():
                        await self.execute_exit(symbol, current_price, "End of day exit")
                
                self.ib.cancelMktData(stock)
                
            except Exception as e:
                self.logger.error(f"❌ Position monitoring error for {symbol}: {e}")
    
    def is_near_market_close(self) -> bool:
        """Check if we're within 30 minutes of market close."""
        try:
            et_tz = pytz.timezone('US/Eastern')
            now = datetime.now(et_tz)
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            return (market_close - now).total_seconds() <= 1800  # 30 minutes
        except:
            return False
    
    async def execute_partial_exit(self, symbol: str, shares: int, current_price: float, reason: str):
        """Execute partial exit (scaling out)."""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            entry_price = position['entry_price']
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            
            if not qualified:
                return
            
            stock = qualified[0]
            
            # Place market order to sell partial position
            order = MarketOrder('SELL', shares)
            trade = self.ib.placeOrder(stock, order)
            
            # Calculate partial P&L
            pnl = (current_price - entry_price) * shares
            pnl_pct = (current_price - entry_price) / entry_price * 100
            
            self.daily_pnl += pnl
            
            self.logger.info(f"📊 PARTIAL EXIT: {symbol} - {shares} shares @ ${current_price:.2f}")
            self.logger.info(f"   Reason: {reason}")
            self.logger.info(f"   Partial P&L: ${pnl:.2f} ({pnl_pct:+.1f}%)")
            self.logger.info(f"   Remaining: {position['shares_remaining'] - shares} shares")
            
        except Exception as e:
            self.logger.error(f"❌ Partial exit error for {symbol}: {e}")
    
    async def execute_exit(self, symbol: str, current_price: float, reason: str):
        """Execute exit order for a position."""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            shares = position.get('shares_remaining', position['shares'])
            entry_price = position['entry_price']
            
            # Create stock contract
            stock = Stock(symbol, 'SMART', 'USD')
            qualified = self.ib.qualifyContracts(stock)
            
            if not qualified:
                return
            
            stock = qualified[0]
            
            # Place market order to exit quickly
            order = MarketOrder('SELL', shares)
            trade = self.ib.placeOrder(stock, order)
            
            # Calculate P&L
            pnl = (current_price - entry_price) * shares
            pnl_pct = (current_price - entry_price) / entry_price * 100
            
            self.daily_pnl += pnl
            
            self.logger.info(f"📉 EXIT: {symbol} - {shares} shares @ ${current_price:.2f}")
            self.logger.info(f"   Reason: {reason}")
            self.logger.info(f"   P&L: ${pnl:.2f} ({pnl_pct:+.1f}%)")
            self.logger.info(f"   Daily P&L: ${self.daily_pnl:.2f}")
            
            # Record exit in trade tracker
            if self.trade_tracker and 'tracker_id' in position:
                try:
                    result = self.trade_tracker.record_exit(
                        trade_id=position['tracker_id'],
                        exit_price=current_price,
                        exit_reason=reason
                    )
                    self.logger.info(f"📊 Trade closed in tracker: {result['pnl_pct']:.1f}% return")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to record exit in tracker: {e}")
            
            # Remove from positions
            del self.positions[symbol]
            
            # Send alert if configured
            if self.config['ENABLE_EMAIL_ALERTS']:
                await self.send_trade_alert(symbol, 'EXIT', current_price, pnl, reason)
            
        except Exception as e:
            self.logger.error(f"❌ Exit execution error for {symbol}: {e}")
    
    async def send_trade_alert(self, symbol: str, action: str, price: float, 
                             pnl: float = 0, reason: str = ''):
        """Send email alert for trade actions."""
        try:
            if not all([self.config['EMAIL_USER'], self.config['EMAIL_PASS'], 
                       self.config['EMAIL_TO']]):
                return
            
            subject = f"Trading Bot Alert: {action} {symbol}"
            
            body = f"""
Trading Bot Alert
================

Action: {action}
Symbol: {symbol}
Price: ${price:.2f}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
            if pnl != 0:
                body += f"P&L: ${pnl:.2f}\n"
            if reason:
                body += f"Reason: {reason}\n"
            
            body += f"\nDaily P&L: ${self.daily_pnl:.2f}"
            body += f"\nActive Positions: {len(self.positions)}"
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = self.config['EMAIL_USER']
            msg['To'] = self.config['EMAIL_TO']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['EMAIL_HOST'], self.config['EMAIL_PORT'])
            server.starttls()
            server.login(self.config['EMAIL_USER'], self.config['EMAIL_PASS'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"📧 Alert sent: {action} {symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Email alert error: {e}")
    
    async def risk_check(self) -> bool:
        """Check if we should continue trading based on risk limits."""
        # Check daily loss limit
        if self.daily_pnl <= -self.config['MAX_DAILY_LOSS']:
            self.logger.warning(f"🛑 Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False
        
        # Check daily trade limit
        if self.trade_count >= self.config['MAX_DAILY_TRADES']:
            self.logger.warning(f"🛑 Daily trade limit reached: {self.trade_count}")
            return False
        
        return True
    
    async def run_trading_session(self):
        """Main trading session loop."""
        self.logger.info("🚀 Starting trading session...")
        
        # Connect to IB Gateway
        if not await self.connect_to_ib():
            return
        
        try:
            # Pre-market scanning
            if self.is_premarket_hours():
                self.logger.info("🌅 Pre-market: Scanning for candidates...")
                self.candidates = await self.scan_gap_up_candidates()
                
                # Scan for unusual options activity
                if self.config['SCAN_OPTIONS']:
                    self.logger.info("📊 Pre-market: Scanning for unusual options activity...")
                    unusual_options = await self.scan_unusual_options_activity()
                    if unusual_options:
                        self.logger.info(f"🎯 Found {len(unusual_options)} unusual options:")
                        for option in unusual_options[:5]:  # Show top 5
                            self.logger.info(f"   {option['symbol']} {option['strike']}C - Volume: {option['volume']:,} (Ratio: {option['volume_ratio']:.1f}x)")
            
            # Wait for market open
            while not self.is_market_hours():
                if not self.is_premarket_hours():
                    self.logger.info("⏰ Waiting for market hours...")
                await asyncio.sleep(5)  # Check every 5 seconds (was 60)
            
            self.logger.info("🔔 Market is open - Starting trading...")
            
            # Check SPY market direction first (Humble Trader rule)
            spy_ok, spy_change = await self.is_market_favorable()
            if not spy_ok:
                self.logger.info(f"🔴 Market Filter: SPY {spy_change:+.2f}% - Not trading today")
                # Still monitor positions but don't open new ones
                while self.is_market_hours():
                    await self.monitor_positions()
                    await asyncio.sleep(30)
                return
            else:
                self.logger.info(f"✅ Market Filter: SPY {spy_change:+.2f}% - Good to trade")
            
            # Main trading loop
            while self.is_market_hours():
                # Risk check
                if not await self.risk_check():
                    break
                
                # Look for entry signals in candidates
                for candidate in self.candidates:
                    symbol = candidate['symbol']
                    
                    # Skip if already have position
                    if symbol in self.positions:
                        continue
                    
                    # Check news catalyst first (Humble Trader requirement)
                    has_news, news_info = await self.has_recent_news(symbol)
                    if not has_news:
                        self.logger.info(f"⚠️ {symbol} - Skipped: {news_info}")
                        continue
                    
                    self.logger.info(f"✅ {symbol} - {news_info}")
                    
                    # Check entry signal
                    if await self.check_entry_signal(candidate):
                        current_price = candidate['current_price']
                        success = await self.execute_long_entry(symbol, current_price)
                        
                        if success:
                            await self.send_trade_alert(symbol, 'ENTRY', current_price)
                
                # Scan for unusual options activity during market hours (every 5 minutes)
                if self.config['SCAN_OPTIONS'] and hasattr(self, '_last_options_scan'):
                    if time_module.time() - self._last_options_scan > 300:  # 5 minutes
                        unusual_options = await self.scan_unusual_options_activity()
                        if unusual_options:
                            self.logger.info(f"📊 Market hours: Found {len(unusual_options)} unusual options")
                            for option in unusual_options[:3]:  # Show top 3
                                self.logger.info(f"   {option['symbol']} {option['strike']}C - Volume: {option['volume']:,} (Ratio: {option['volume_ratio']:.1f}x)")
                        self._last_options_scan = time_module.time()
                elif self.config['SCAN_OPTIONS']:
                    self._last_options_scan = time_module.time()
                
                # Monitor existing positions
                await self.monitor_positions()
                
                # Wait before next iteration
                await asyncio.sleep(5)  # Check every 5 seconds (was 30)
            
            # End of day - close all positions
            self.logger.info("🌅 Market closing - Exiting all positions...")
            for symbol in list(self.positions.keys()):
                # Get current price and exit
                stock = Stock(symbol, 'SMART', 'USD')
                qualified = self.ib.qualifyContracts(stock)
                if qualified:
                    ticker = self.ib.reqMktData(qualified[0], '', False, False)
                    await asyncio.sleep(1)
                    current_price = ticker.last if ticker.last > 0 else ticker.close
                    await self.execute_exit(symbol, current_price, "End of day")
            
            # Daily summary
            self.logger.info(f"📊 Daily Summary:")
            self.logger.info(f"   Total Trades: {self.trade_count}")
            self.logger.info(f"   Daily P&L: ${self.daily_pnl:.2f}")
            self.logger.info(f"   Candidates Scanned: {len(self.candidates)}")
            
        except Exception as e:
            self.logger.error(f"❌ Trading session error: {e}")
        
        finally:
            # Cleanup
            self.disconnect_from_ib()
            self.logger.info("🏁 Trading session ended")

# ==================================================================================
# UTILITY FUNCTIONS
# ==================================================================================

def validate_config(config: Dict) -> bool:
    """Validate configuration settings."""
    required_keys = ['IB_HOST', 'IB_PORT', 'CLIENT_ID']
    
    for key in required_keys:
        if key not in config:
            print(f"❌ Missing required config: {key}")
            return False
    
    if config['IB_PORT'] not in [4001, 4002]:
        print("⚠️ Warning: IB_PORT should be 4001 (live) or 4002 (paper)")
    
    return True

def print_startup_info():
    """Print startup information and instructions."""
    print("🤖 ROBUST DAY TRADING BOT")
    print("=" * 50)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔌 Target: IB Gateway {CONFIG['IB_HOST']}:{CONFIG['IB_PORT']}")
    print(f"📊 Strategy: VWAP Long on Gap-Up Stocks")
    print(f"💰 Max Position: {CONFIG['MAX_POSITION_PCT']}% of buying power")
    print(f"🛑 Stop Loss: {CONFIG['STOP_LOSS_PCT']}% below VWAP")
    print(f"🎯 Take Profit: {CONFIG['TAKE_PROFIT_PCT']}% above VWAP")
    print("=" * 50)
    print()

# ==================================================================================
# MAIN EXECUTION
# ==================================================================================

async def main():
    """Main execution function."""
    print_startup_info()
    
    # Validate configuration
    if not validate_config(CONFIG):
        return
    
    # Check if IB Gateway is available
    if not IB_AVAILABLE:
        print("❌ ib_insync not available")
        return
    
    # Create and run trading bot
    bot = DayTradingBot(CONFIG)
    
    try:
        await bot.run_trading_session()
    except KeyboardInterrupt:
        print("\n⏹️ Trading bot stopped by user")
        bot.disconnect_from_ib()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        bot.disconnect_from_ib()

if __name__ == "__main__":
    # Run the async trading bot
    asyncio.run(main())

