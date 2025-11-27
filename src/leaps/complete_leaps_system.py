#!/usr/bin/env python3
"""
Complete LEAPS System - Seamless integration of all analysis components
Fundamentals → News → Sector → GPT → Price Prediction → LEAPS Strategy
Enhanced with IV Analysis, Multi-Expiry Spreads, and Portfolio Analytics
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import argparse
import warnings
from tabulate import tabulate
import os
import json
import time
import pytz
from scipy.stats import norm
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

warnings.filterwarnings('ignore')

# Try to import IBKR components (graceful fallback if not available)
try:
    from ib_insync import IB, Stock, Option
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False


class CompleteLEAPSSystem:
    """Complete systematic LEAPS analysis - everything integrated."""
    
    def __init__(self, use_gpt: bool = True, try_ibkr: bool = True, use_finbert: bool = True):
        # Print current date for context
        today = datetime.now()
        print(f"📅 Analysis Date: {today.strftime('%B %d, %Y')} ({today.strftime('%A')})")
        print("🎯 All LEAPS expiry recommendations will be for 2026-2027 (future dates only)")
        
        # Check market hours
        self.market_open = self.is_market_open()
        print(f"🕐 Market Status: {'🟢 OPEN' if self.market_open else '🔴 CLOSED'}")
        
        if try_ibkr and IBKR_AVAILABLE:
            print("🔌 IBKR integration: ENABLED (will verify LEAPS)")
        else:
            print("⏳ IBKR integration: DISABLED (not available)")
        
        # Initialize FinBERT for professional sentiment analysis
        self.use_finbert = use_finbert
        self.finbert_available = False
        self.finbert_model = None
        self.finbert_tokenizer = None
        
        if use_finbert:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                
                print("🧠 Loading FinBERT for professional sentiment analysis...", end=' ')
                self.finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                self.finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
                self.finbert_available = True
                print("✅ FinBERT loaded successfully")
            except Exception as e:
                print(f"⚠️ FinBERT unavailable: {str(e)[:50]}")
        
        print()
        
        self.use_gpt = use_gpt
        self.gpt_available = False
        self.try_ibkr = try_ibkr and IBKR_AVAILABLE
        self.ib = None
        
        if use_gpt:
            try:
                import openai
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.openai_client = openai.OpenAI()
                    self.gpt_available = True
                    print("🤖 Complete GPT integration: ENABLED")
                else:
                    print("⚠️  GPT integration: DISABLED (no API key)")
            except ImportError:
                print("⚠️  GPT integration: DISABLED (openai package not installed)")
    
    def is_market_open(self) -> bool:
        """Check if US options market is currently open."""
        try:
            et_tz = pytz.timezone('US/Eastern')
            now = datetime.now(et_tz)
            
            # Market hours: Monday-Friday, 9:30 AM - 4:00 PM ET
            if now.weekday() >= 5:  # Weekend
                return False
            
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            return market_open <= now <= market_close
        except:
            return False
    
    def try_ibkr_connection(self) -> bool:
        """Try to connect to IBKR Gateway."""
        if not self.try_ibkr:
            return False
        
        try:
            self.ib = IB()
            self.ib.connect('127.0.0.1', 4001, clientId=7, timeout=3)
            return True
        except Exception:
            return False
    
    def get_yfinance_option_chains(self, symbol: str, current_price: float) -> dict:
        """Get actual option chain data from yfinance for LEAPS validation."""
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            
            if not expirations:
                return {'available': False, 'reason': 'No options available'}
            
            # Filter for LEAPS (12+ months out)
            min_expiry_date = datetime.now() + timedelta(days=365)
            leaps_expirations = []
            
            for exp_str in expirations:
                try:
                    exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                    if exp_date >= min_expiry_date:
                        leaps_expirations.append((exp_str, exp_date))
                except:
                    continue
            
            if not leaps_expirations:
                return {'available': True, 'leaps_exists': False, 'reason': 'No LEAPS expiries (need 12+ months)'}
            
            # Sort by expiration date and get the best LEAPS contracts
            leaps_expirations.sort(key=lambda x: x[1])
            best_contracts = []
            
            for exp_str, exp_date in leaps_expirations[:3]:  # Check top 3 LEAPS expiries
                try:
                    chain = ticker.option_chain(exp_str)
                    calls_df = chain.calls
                    
                    if calls_df.empty:
                        continue
                    
                    # Filter for reasonable strikes (0.7x to 1.3x current price)
                    min_strike = current_price * 0.7
                    max_strike = current_price * 1.3
                    
                    filtered_calls = calls_df[
                        (calls_df['strike'] >= min_strike) & 
                        (calls_df['strike'] <= max_strike) &
                        (calls_df['openInterest'] > 0)  # Must have open interest
                    ].copy()
                    
                    if filtered_calls.empty:
                        continue
                    
                    # Calculate contract costs and find best options
                    filtered_calls['midPrice'] = (filtered_calls['bid'] + filtered_calls['ask']) / 2
                    filtered_calls['contractCost'] = filtered_calls['midPrice'] * 100  # Contract multiplier
                    filtered_calls['spread'] = filtered_calls['ask'] - filtered_calls['bid']
                    filtered_calls['spreadPct'] = (filtered_calls['spread'] / filtered_calls['midPrice'] * 100).round(1)
                    
                    # Sort by liquidity (open interest) and reasonable cost
                    best_calls = filtered_calls.sort_values(['openInterest', 'volume'], ascending=False).head(5)
                    
                    for _, call in best_calls.iterrows():
                        best_contracts.append({
                            'expiry': exp_str,
                            'strike': call['strike'],
                            'lastPrice': call['lastPrice'],
                            'bid': call['bid'],
                            'ask': call['ask'],
                            'midPrice': call['midPrice'],
                            'contractCost': call['contractCost'],
                            'volume': call['volume'],
                            'openInterest': call['openInterest'],
                            'spreadPct': call['spreadPct'],
                            'daysToExpiry': (exp_date - datetime.now()).days
                        })
                
                except Exception as e:
                    continue
            
            if not best_contracts:
                return {'available': True, 'leaps_exists': False, 'reason': 'No liquid LEAPS contracts found'}
            
            # Sort by liquidity score (open interest + volume weight)
            for contract in best_contracts:
                contract['liquidityScore'] = contract['openInterest'] + (contract['volume'] * 0.1)
            
            best_contracts.sort(key=lambda x: x['liquidityScore'], reverse=True)
            
            return {
                'available': True,
                'leaps_exists': True,
                'total_expiries': len(leaps_expirations),
                'liquid_contracts': len(best_contracts),
                'best_contracts': best_contracts[:10],  # Top 10 most liquid
                'reason': f'Found {len(best_contracts)} liquid LEAPS contracts'
            }
            
        except Exception as e:
            return {'available': False, 'reason': f'Option chain error: {str(e)[:50]}'}

    def get_ibkr_leaps_data(self, symbol: str) -> dict:
        """Get actual LEAPS data from IBKR if available."""
        if not self.try_ibkr or not self.ib:
            return {'available': False, 'reason': 'IBKR not connected'}
        
        try:
            # Quick LEAPS check
            stock = Stock(symbol, 'SMART', 'USD')
            qualified_stocks = self.ib.qualifyContracts(stock)
            
            if not qualified_stocks:
                return {'available': False, 'reason': 'Stock not found in IBKR'}
            
            stock = qualified_stocks[0]
            
            # Get current stock price
            self.ib.reqMktData(stock, '', True, False)
            self.ib.sleep(1)
            ticker = self.ib.ticker(stock)
            self.ib.cancelMktData(stock)
            
            ibkr_price = ticker.last if ticker.last > 0 else ticker.close if ticker.close > 0 else 0
            
            # Check for option chains
            try:
                chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
                
                if not chains:
                    return {'available': True, 'leaps_exists': False, 'reason': 'No option chains'}
                
                # Check for LEAPS expiries (270+ days)
                min_expiry_date = datetime.now() + timedelta(days=270)
                leaps_count = 0
                
                for chain in chains[:3]:  # Check first 3 exchanges
                    for expiry in chain.expirations:
                        expiry_date = datetime.strptime(expiry, '%Y%m%d')
                        if expiry_date >= min_expiry_date:
                            leaps_count += 1
                            break
                
                if leaps_count > 0:
                    return {
                        'available': True,
                        'leaps_exists': True,
                        'ibkr_price': ibkr_price,
                        'leaps_expiries': leaps_count,
                        'reason': f'Found {leaps_count} LEAPS expiries'
                    }
                else:
                    return {
                        'available': True,
                        'leaps_exists': False,
                        'reason': 'No LEAPS expiries (need 270+ days)'
                    }
                    
            except Exception as e:
                return {'available': True, 'leaps_exists': False, 'reason': f'Option chain error: {str(e)[:50]}'}
                
        except Exception as e:
            return {'available': False, 'reason': f'IBKR error: {str(e)[:50]}'}
    
    def disconnect_ibkr(self):
        """Safely disconnect from IBKR."""
        if self.ib and self.ib.isConnected():
            try:
                self.ib.disconnect()
            except:
                pass
    
    def calculate_options_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> dict:
        """
        Calculate Black-Scholes options Greeks.
        
        Parameters:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Implied volatility (annualized)
        option_type: 'call' or 'put'
        """
        try:
            if T <= 0 or sigma <= 0:
                return {}
            
            # Black-Scholes calculations
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            # Standard normal distribution
            N_d1 = norm.cdf(d1)
            N_d2 = norm.cdf(d2)
            n_d1 = norm.pdf(d1)  # Standard normal density
            
            if option_type.lower() == 'call':
                # Call option pricing and Greeks
                price = S * N_d1 - K * math.exp(-r * T) * N_d2
                delta = N_d1
                theta = (-S * n_d1 * sigma / (2 * math.sqrt(T)) 
                        - r * K * math.exp(-r * T) * N_d2) / 365  # Per day
            else:
                # Put option pricing and Greeks
                price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
                delta = N_d1 - 1
                theta = (-S * n_d1 * sigma / (2 * math.sqrt(T)) 
                        + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365  # Per day
            
            # Greeks that are the same for calls and puts
            gamma = n_d1 / (S * sigma * math.sqrt(T))
            vega = S * n_d1 * math.sqrt(T) / 100  # Per 1% volatility change
            rho = K * T * math.exp(-r * T) * (N_d2 if option_type.lower() == 'call' else norm.cdf(-d2)) / 100
            
            return {
                'theoretical_price': price,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'rho': rho,
                'implied_volatility': sigma,
                'time_to_expiry': T,
                'moneyness': S / K
            }
            
        except Exception as e:
            return {}
    
    def analyze_leaps_greeks(self, symbol: str, current_price: float, strike: float, expiry_date: str, 
                            market_volatility: float = None) -> dict:
        """Analyze LEAPS contract Greeks for risk assessment."""
        try:
            # Calculate time to expiry
            expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
            current_dt = datetime.now()
            time_to_expiry = (expiry_dt - current_dt).days / 365.25
            
            if time_to_expiry <= 0:
                return {'error': 'Expiry date is in the past'}
            
            # Use market volatility or estimate from historical data
            if market_volatility is None:
                # Use the volatility we calculated in fundamentals, or default
                market_volatility = 0.30  # 30% default
            else:
                market_volatility = market_volatility / 100  # Convert percentage to decimal
            
            # Risk-free rate approximation (could be enhanced with real treasury data)
            risk_free_rate = 0.05  # 5% approximation
            
            # Calculate Greeks
            greeks = self.calculate_options_greeks(
                S=current_price,
                K=strike,
                T=time_to_expiry,
                r=risk_free_rate,
                sigma=market_volatility,
                option_type='call'
            )
            
            if not greeks:
                return {'error': 'Greeks calculation failed'}
            
            # Add interpretations for LEAPS investing
            interpretations = {}
            
            # Delta interpretation
            if greeks['delta'] > 0.7:
                interpretations['delta'] = 'High sensitivity to stock moves (deep ITM)'
            elif greeks['delta'] > 0.5:
                interpretations['delta'] = 'Good leverage with moderate risk (ATM)'
            elif greeks['delta'] > 0.3:
                interpretations['delta'] = 'Moderate leverage, higher risk (OTM)'
            else:
                interpretations['delta'] = 'Low probability of profit (far OTM)'
            
            # Theta interpretation for LEAPS
            daily_decay = abs(greeks['theta'])
            if daily_decay > 0.10:
                interpretations['theta'] = 'High time decay - expensive to hold'
            elif daily_decay > 0.05:
                interpretations['theta'] = 'Moderate time decay'
            else:
                interpretations['theta'] = 'Low time decay - good for LEAPS'
            
            # Vega interpretation
            if greeks['vega'] > 0.20:
                interpretations['vega'] = 'High volatility sensitivity'
            elif greeks['vega'] > 0.10:
                interpretations['vega'] = 'Moderate volatility sensitivity'
            else:
                interpretations['vega'] = 'Low volatility sensitivity'
            
            # Overall LEAPS suitability
            leaps_score = 0
            if 0.4 <= greeks['delta'] <= 0.8:  # Good delta range for LEAPS
                leaps_score += 3
            elif 0.2 <= greeks['delta'] <= 0.9:
                leaps_score += 2
            else:
                leaps_score += 1
                
            if daily_decay < 0.05:  # Low time decay is good for LEAPS
                leaps_score += 2
            elif daily_decay < 0.10:
                leaps_score += 1
                
            if time_to_expiry > 1.5:  # Longer time is better for LEAPS
                leaps_score += 2
            elif time_to_expiry > 1.0:
                leaps_score += 1
            
            if leaps_score >= 6:
                suitability = 'Excellent for LEAPS strategy'
            elif leaps_score >= 4:
                suitability = 'Good for LEAPS strategy'
            elif leaps_score >= 2:
                suitability = 'Fair for LEAPS strategy'
            else:
                suitability = 'Poor for LEAPS strategy'
            
            greeks['interpretations'] = interpretations
            greeks['leaps_suitability'] = suitability
            greeks['leaps_score'] = leaps_score
            
            return greeks
            
        except Exception as e:
            return {'error': f'Greeks analysis failed: {str(e)[:50]}'}
    
    def get_all_fundamental_data(self, symbol: str) -> dict:
        """Get comprehensive fundamental data with retry mechanism."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if not info or 'symbol' not in info:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️ Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"   ❌ Invalid ticker symbol: {symbol}")
                        return {}
                
                # Get historical data for technical analysis
                hist = ticker.history(period='1y')
            
                current_price = info.get('currentPrice', 0)
                target_price = info.get('targetMeanPrice', 0)
                
                # Calculate additional metrics with enhanced trend analysis
                price_52w_change = 0
                price_6m_change = 0
                price_3m_change = 0
                price_1m_change = 0
                volatility = 0
                volatility_trend = 0
                momentum_score = 0
                
                if len(hist) > 50:
                    closes = hist['Close']
                    
                    # Price performance over different periods
                    price_52w_change = ((current_price - closes.iloc[0]) / closes.iloc[0] * 100)
                    
                    if len(hist) >= 126:  # 6 months
                        price_6m_change = ((current_price - closes.iloc[-126]) / closes.iloc[-126] * 100)
                    
                    if len(hist) >= 63:  # 3 months
                        price_3m_change = ((current_price - closes.iloc[-63]) / closes.iloc[-63] * 100)
                    
                    if len(hist) >= 21:  # 1 month
                        price_1m_change = ((current_price - closes.iloc[-21]) / closes.iloc[-21] * 100)
                    
                    # Enhanced volatility analysis
                    returns = closes.pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility
                    
                    # Volatility trend (recent vs historical)
                    if len(returns) >= 126:
                        recent_vol = returns.tail(63).std() * np.sqrt(252) * 100  # Last 3 months
                        historical_vol = returns.head(63).std() * np.sqrt(252) * 100  # First 3 months
                        volatility_trend = ((recent_vol - historical_vol) / historical_vol * 100) if historical_vol > 0 else 0
                    
                    # Momentum score (weighted recent performance)
                    # Higher weight for more recent performance
                    momentum_components = []
                    if price_1m_change != 0:
                        momentum_components.append(price_1m_change * 0.4)
                    if price_3m_change != 0:
                        momentum_components.append(price_3m_change * 0.3)
                    if price_6m_change != 0:
                        momentum_components.append(price_6m_change * 0.2)
                    if price_52w_change != 0:
                        momentum_components.append(price_52w_change * 0.1)
                    
                    momentum_score = sum(momentum_components) if momentum_components else 0
                
                # Validate critical data
                if current_price <= 0:
                    print(f"   ⚠️ Warning: No current price for {symbol}, using close price")
                    current_price = info.get('previousClose', hist['Close'].iloc[-1] if len(hist) > 0 else 0)
                
                return {
                    'symbol': symbol,
                    'company_name': info.get('longName', 'N/A'),
                    'sector': info.get('sector', 'N/A'),
                    'industry': info.get('industry', 'N/A'),
                    'current_price': current_price,
                    'market_cap': info.get('marketCap', 0),
                    
                    # Growth metrics
                    'revenue_growth': (info.get('revenueGrowth', 0) or 0) * 100,
                    'quarterly_revenue_growth': (info.get('quarterlyRevenueGrowth', 0) or 0) * 100,
                    'earnings_growth': (info.get('earningsGrowth', 0) or 0) * 100,
                    
                    # Profitability
                    'profit_margin': (info.get('profitMargins', 0) or 0) * 100,
                    'operating_margin': (info.get('operatingMargins', 0) or 0) * 100,
                    'gross_margin': (info.get('grossMargins', 0) or 0) * 100,
                    'return_on_equity': (info.get('returnOnEquity', 0) or 0) * 100,
                    
                    # Valuation
                    'pe_ratio': info.get('trailingPE', np.nan),
                    'forward_pe': info.get('forwardPE', np.nan),
                    'peg_ratio': info.get('pegRatio', np.nan),
                    'price_to_sales': info.get('priceToSalesTrailing12Months', np.nan),
                    'price_to_book': info.get('priceToBook', np.nan),
                    
                    # Analyst data
                    'analyst_target': target_price,
                    'analyst_upside': ((target_price - current_price) / current_price * 100) if target_price > 0 and current_price > 0 else 0,
                    'num_analysts': info.get('numberOfAnalystOpinions', 0),
                    'recommendation_mean': info.get('recommendationMean', 3),
                    
                    # Financial health
                    'debt_to_equity': info.get('debtToEquity', np.nan),
                    'current_ratio': info.get('currentRatio', np.nan),
                    'total_cash': info.get('totalCash', 0),
                    'total_debt': info.get('totalDebt', 0),
                    
                    # Performance and trend analysis
                    'price_52w_change': price_52w_change,
                    'price_6m_change': price_6m_change,
                    'price_3m_change': price_3m_change,
                    'price_1m_change': price_1m_change,
                    'volatility_annual': volatility,
                    'volatility_trend': volatility_trend,
                    'momentum_score': momentum_score,
                    '52w_high': info.get('fiftyTwoWeekHigh', 0),
                    '52w_low': info.get('fiftyTwoWeekLow', 0),
                    
                    # Additional risk/opportunity signals
                    'short_percent_float': info.get('shortPercentOfFloat', 0) or 0,
                    'short_ratio': info.get('shortRatio', 0) or 0,
                    'institutional_percent': info.get('heldPercentInstitutions', 0) or 0,
                    'insider_percent': info.get('heldPercentInsiders', 0) or 0,
                    'shares_outstanding': info.get('sharesOutstanding', 0),
                    'float_shares': info.get('floatShares', 0),
                    
                    # Dividend and yield info
                    'dividend_yield': (info.get('dividendYield', 0) or 0) * 100,
                    'payout_ratio': (info.get('payoutRatio', 0) or 0) * 100,
                    
                    # Meta
                    'business_summary': info.get('longBusinessSummary', 'N/A')
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Network error (attempt {attempt + 1}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"   ❌ Failed to fetch data for {symbol}: {str(e)[:50]}")
                    return {}
    
    def analyze_finbert_sentiment(self, text: str) -> dict:
        """Analyze sentiment using FinBERT professional model."""
        if not self.finbert_available:
            return None
            
        try:
            import torch
            
            # Tokenize and predict
            inputs = self.finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # FinBERT outputs: [negative, neutral, positive]
            negative_score = predictions[0][0].item()
            neutral_score = predictions[0][1].item()
            positive_score = predictions[0][2].item()
            
            # Convert to our scoring system (0-100)
            finbert_score = (positive_score - negative_score) * 50 + 50  # Scale to 0-100
            finbert_score = max(0, min(100, finbert_score))  # Clamp to bounds
            
            # Determine sentiment category
            if positive_score > 0.6:
                sentiment = 'positive'
            elif negative_score > 0.6:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
                
            return {
                'sentiment': sentiment,
                'score': int(finbert_score),
                'confidence': max(positive_score, negative_score, neutral_score),
                'raw_scores': {
                    'positive': positive_score,
                    'neutral': neutral_score,
                    'negative': negative_score
                }
            }
            
        except Exception as e:
            return None

    def get_news_sentiment(self, symbol: str) -> dict:
        """Get news sentiment with FinBERT professional analysis and keyword fallback."""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            # Default neutral if no news
            if not news or len(news) == 0:
                return {
                    'sentiment': 'neutral',
                    'news_score': 50,
                    'recent_developments': [],
                    'valid_articles': 0,
                    'analysis_method': 'no_news'
                }
            
            # Collect article texts and titles
            valid_articles = 0
            developments = []
            article_texts = []
            
            for article in news[:10]:
                # Handle new yfinance structure where title is nested in content
                title = ''
                if isinstance(article, dict):
                    if 'content' in article and isinstance(article['content'], dict):
                        # New structure: title is in article['content']['title']
                        title = article['content'].get('title', '').strip()
                    else:
                        # Fallback to old structure
                        title = article.get('title', '').strip()
                
                if not title or len(title) < 10:
                    continue
                
                valid_articles += 1
                article_texts.append(title)
                
                # Track important developments
                if any(word in title.lower() for word in ['earnings', 'revenue', 'guidance', 'approval', 'quarter', 'results']):
                    developments.append(title[:60] + "..." if len(title) > 60 else title)
            
            if valid_articles == 0:
                return {
                    'sentiment': 'neutral',
                    'news_score': 50,
                    'recent_developments': [],
                    'valid_articles': 0,
                    'analysis_method': 'no_valid_articles'
                }
            
            # Try FinBERT analysis first
            if self.finbert_available and article_texts:
                try:
                    # Analyze top 5 most relevant articles with FinBERT
                    finbert_scores = []
                    for text in article_texts[:5]:
                        finbert_result = self.analyze_finbert_sentiment(text)
                        if finbert_result:
                            finbert_scores.append(finbert_result['score'])
                    
                    if finbert_scores:
                        # Calculate weighted average (more recent articles get higher weight)
                        weights = [0.4, 0.3, 0.2, 0.1, 0.05][:len(finbert_scores)]
                        weighted_score = sum(score * weight for score, weight in zip(finbert_scores, weights))
                        avg_sentiment = weighted_score / sum(weights[:len(finbert_scores)])
                        
                        # Classify sentiment
                        if avg_sentiment > 60:
                            sentiment = 'positive'
                        elif avg_sentiment < 40:
                            sentiment = 'negative'
                        else:
                            sentiment = 'neutral'
                        
                        return {
                            'sentiment': sentiment,
                            'news_score': int(avg_sentiment),
                            'recent_developments': developments[:3],
                            'valid_articles': valid_articles,
                            'analysis_method': 'finbert',
                            'finbert_scores': finbert_scores
                        }
                        
                except Exception as e:
                    print(f"   ⚠️ FinBERT analysis failed: {str(e)[:30]}, using keyword fallback")
            
            # Fallback to keyword analysis
            sentiment_total = 0
            positive_words = ['growth', 'strong', 'beat', 'exceeded', 'positive', 'upgrade', 'bullish', 'gains', 'surge', 'rally']
            negative_words = ['decline', 'miss', 'negative', 'downgrade', 'bearish', 'concern', 'risk', 'falls', 'drops', 'plunges']
            
            for title in article_texts:
                title_lower = title.lower()
                
                # Count sentiment words
                positive_count = sum(1 for word in positive_words if word in title_lower)
                negative_count = sum(1 for word in negative_words if word in title_lower)
                
                # Score this article
                if positive_count > negative_count:
                    article_score = 70
                elif negative_count > positive_count:
                    article_score = 30
                else:
                    article_score = 50
                
                sentiment_total += article_score
            
            # Calculate average sentiment
            avg_sentiment = sentiment_total / valid_articles if valid_articles > 0 else 50
            
            # Classify sentiment
            if avg_sentiment > 60:
                sentiment = 'positive'
            elif avg_sentiment < 40:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'sentiment': sentiment,
                'news_score': int(avg_sentiment),
                'recent_developments': developments[:3],
                'valid_articles': valid_articles,
                'analysis_method': 'keyword_fallback'
            }
            
        except Exception as e:
            return {
                'sentiment': 'neutral', 
                'news_score': 50, 
                'recent_developments': [], 
                'valid_articles': 0,
                'analysis_method': 'error_fallback'
            }
    
    def get_sector_analysis(self, sector: str, industry: str) -> dict:
        """Get sector-specific analysis and scoring."""
        sector_data = {
            'sector_score': 50,
            'growth_outlook': 'moderate',
            'policy_support': 'neutral',
            'competitive_intensity': 'medium'
        }
        
        sector_lower = sector.lower()
        industry_lower = industry.lower()
        
        # Healthcare/Biotech - High growth potential
        if 'healthcare' in sector_lower or 'biotech' in industry_lower or 'pharma' in industry_lower:
            sector_data.update({
                'sector_score': 75,
                'growth_outlook': 'high',
                'policy_support': 'supportive',
                'competitive_intensity': 'high',
                'key_drivers': ['Aging population', 'Innovation pipeline', 'Regulatory approvals']
            })
        
        # Technology - AI boom
        elif 'technology' in sector_lower or 'software' in industry_lower:
            sector_data.update({
                'sector_score': 80,
                'growth_outlook': 'very_high',
                'policy_support': 'mixed',
                'competitive_intensity': 'very_high',
                'key_drivers': ['AI adoption', 'Digital transformation', 'Cloud migration']
            })
        
        # Clean Energy - Policy tailwinds
        elif 'energy' in sector_lower and any(word in industry_lower for word in ['renewable', 'solar', 'battery']):
            sector_data.update({
                'sector_score': 85,
                'growth_outlook': 'very_high',
                'policy_support': 'very_supportive',
                'competitive_intensity': 'high',
                'key_drivers': ['Climate policies', 'Cost reductions', 'Grid modernization']
            })
        
        # Aerospace/Defense
        elif 'aerospace' in industry_lower or 'defense' in industry_lower:
            sector_data.update({
                'sector_score': 75,
                'growth_outlook': 'high',
                'policy_support': 'supportive',
                'competitive_intensity': 'medium',
                'key_drivers': ['Space commercialization', 'Defense spending', 'Innovation cycles']
            })
        
        return sector_data
    
    def get_gpt_analysis(self, symbol: str, fundamentals: dict, news: dict, sector: dict) -> dict:
        """Get real GPT analysis with all context."""
        if not self.gpt_available:
            print("   ⚠️ GPT analysis unavailable, using enhanced systematic model")
            return self.get_systematic_fallback(fundamentals, news, sector)
        
        try:
            # Build comprehensive context with business summary
            business_summary = fundamentals.get('business_summary', 'N/A')
            business_context = ""
            if business_summary != 'N/A' and len(business_summary) > 50:
                # Use first 500 characters of business summary for context
                business_context = f"\nBUSINESS OVERVIEW: {business_summary[:500]}{'...' if len(business_summary) > 500 else ''}"
            
            # Additional risk signals
            short_interest = fundamentals.get('short_percent_float', 0)
            institutional_own = fundamentals.get('institutional_percent', 0) * 100
            volatility = fundamentals.get('volatility_annual', 0)
            
            context = f"""
SYSTEMATIC INVESTMENT ANALYSIS: {symbol}

COMPANY: {fundamentals['company_name']}
SECTOR: {fundamentals['sector']} | INDUSTRY: {fundamentals['industry']}
PRICE: ${fundamentals['current_price']:.2f} | MARKET CAP: ${fundamentals['market_cap']/1e9:.1f}B{business_context}

FUNDAMENTAL METRICS:
• Revenue Growth: {fundamentals['revenue_growth']:.0f}% (TTM)
• Profit Margin: {fundamentals['profit_margin']:.1f}%
• Operating Margin: {fundamentals['operating_margin']:.1f}%
• Analyst Target: ${fundamentals['analyst_target']:.2f} ({fundamentals['analyst_upside']:+.0f}% upside)
• Analyst Coverage: {fundamentals['num_analysts']} analysts
• Debt/Equity: {fundamentals.get('debt_to_equity', 'N/A')}

RISK/OPPORTUNITY SIGNALS:
• Short Interest: {short_interest:.1f}% of float
• Institutional Ownership: {institutional_own:.0f}%
• Annual Volatility: {volatility:.0f}%
• 52-Week Performance: {fundamentals['price_52w_change']:+.0f}%

NEWS INTELLIGENCE:
• Sentiment: {news['sentiment'].upper()}
• Valid Articles Analyzed: {news['valid_articles']}
• Recent Developments: {len(news['recent_developments'])} tracked

SECTOR DYNAMICS:
• Sector Outlook: {sector['growth_outlook'].upper()}
• Policy Environment: {sector['policy_support'].upper()}
• Competitive Intensity: {sector['competitive_intensity'].upper()}

ANALYSIS REQUEST:
Provide a systematic 2-year LEAPS investment analysis for the period 2025-2027. 

IMPORTANT: We are currently in September 2025. All catalysts and timelines must be FUTURE events (Q4 2025, 2026, 2027). Do not suggest past events like "Q3 2024" - those have already occurred.

Base predictions on the fundamental data above, not speculation. Consider the business context, risk signals, and sector dynamics. Focus on:
1. Realistic price targets with clear methodology based on current fundamentals
2. Future catalysts with specific timelines (Q4 2025 onwards)
3. Risk assessment with probabilities for 2025-2027 period
4. Optimal LEAPS strategy (find best contract regardless of cost)

Return analysis ONLY as valid JSON in this exact format:
{{
    "price_prediction": {{
        "12_month_target": 25.50,
        "24_month_target": 35.75,
        "confidence_level": 78,
        "methodology": "DCF + sector multiples",
        "key_assumptions": ["revenue growth continues", "margin expansion"]
    }},
    "catalyst_timeline": [
        {{"event": "Product launch", "timeline": "Q2 2025", "price_impact": "+15%"}},
        {{"event": "Earnings beat", "timeline": "Q4 2024", "price_impact": "+8%"}}
    ],
    "risk_factors": [
        {{"risk": "Competition", "probability": 40, "impact": "-20%"}},
        {{"risk": "Execution", "probability": 25, "impact": "-15%"}}
    ],
    "leaps_strategy": {{
        "recommendation": "STRONG_BUY",
        "optimal_strike": 18.50,
        "expiry_date": "2026-06-19",
        "position_size": 4.0,
        "expected_return": 85
    }},
    "overall_score": 82
}}
"""
            
            # Define the structured output schema
            leaps_analysis_function = {
                "name": "analyze_leaps_investment",
                "description": "Analyze a stock for LEAPS investment potential",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "price_prediction": {
                            "type": "object",
                            "properties": {
                                "12_month_target": {"type": "number", "description": "12-month price target in USD"},
                                "24_month_target": {"type": "number", "description": "24-month price target in USD"},
                                "confidence_level": {"type": "integer", "minimum": 20, "maximum": 95, "description": "Confidence level as integer 20-95"},
                                "methodology": {"type": "string", "maxLength": 100, "description": "Brief methodology description"},
                                "key_assumptions": {
                                    "type": "array",
                                    "items": {"type": "string", "maxLength": 100},
                                    "maxItems": 3,
                                    "description": "Key assumptions for price targets"
                                }
                            },
                            "required": ["12_month_target", "24_month_target", "confidence_level", "methodology", "key_assumptions"]
                        },
                        "catalyst_timeline": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event": {"type": "string", "maxLength": 80, "description": "Catalyst event description"},
                                    "timeline": {"type": "string", "maxLength": 30, "description": "Expected timeline"},
                                    "price_impact": {"type": "string", "maxLength": 20, "description": "Expected price impact"}
                                },
                                "required": ["event", "timeline", "price_impact"]
                            },
                            "maxItems": 5,
                            "description": "Key catalysts with timeline and impact"
                        },
                        "risk_factors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "risk": {"type": "string", "maxLength": 80, "description": "Risk factor description"},
                                    "probability": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Probability percentage"},
                                    "impact": {"type": "string", "maxLength": 20, "description": "Expected impact"}
                                },
                                "required": ["risk", "probability", "impact"]
                            },
                            "maxItems": 5,
                            "description": "Key risk factors with probability and impact"
                        },
                        "leaps_strategy": {
                            "type": "object",
                            "properties": {
                                "recommendation": {
                                    "type": "string",
                                    "enum": ["STRONG_BUY", "BUY", "CONSIDER", "AVOID"],
                                    "description": "LEAPS recommendation level"
                                },
                                "optimal_strike": {"type": "number", "description": "Optimal strike price in USD"},
                                "expiry_date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "description": "Expiry date in YYYY-MM-DD format"},
                                "position_size": {"type": "number", "minimum": 0.5, "maximum": 10.0, "description": "Position size as percentage of portfolio"},
                                "expected_return": {"type": "number", "minimum": -50, "maximum": 300, "description": "Expected return percentage"}
                            },
                            "required": ["recommendation", "optimal_strike", "expiry_date", "position_size", "expected_return"]
                        },
                        "overall_score": {"type": "integer", "minimum": 10, "maximum": 100, "description": "Overall investment score 10-100"}
                    },
                    "required": ["price_prediction", "catalyst_timeline", "risk_factors", "leaps_strategy", "overall_score"]
                }
            }

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a systematic investment analyst. Provide precise, quantified analysis based on fundamental analysis, not speculation. Use the provided function to structure your response."
                    },
                    {"role": "user", "content": context}
                ],
                functions=[leaps_analysis_function],
                function_call={"name": "analyze_leaps_investment"},
                temperature=0.1  # Very low for consistent analysis
            )
            
            # Handle function calling response
            message = response.choices[0].message
            
            if message.function_call:
                # Function calling succeeded - parse the structured response
                try:
                    function_args = json.loads(message.function_call.arguments)
                    print("   ✅ Function calling successful - guaranteed structured output")
                    
                    # The function call already provides validated structure, but we still sanitize for safety
                    analysis = self.validate_and_sanitize_gpt_json(function_args, fundamentals)
                    return analysis
                    
                except Exception as parse_error:
                    print(f"   ⚠️ Function call parsing failed: {str(parse_error)[:50]}")
                    return self.get_systematic_fallback(fundamentals, news, sector)
            
            elif message.content:
                # Fallback to content parsing (shouldn't happen with function calling, but just in case)
                print("   ⚠️ Function calling failed, parsing content as fallback")
                gpt_response = message.content
                
                # Extract and parse JSON with validation
                try:
                    json_start = gpt_response.find('{')
                    json_end = gpt_response.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = gpt_response[json_start:json_end]
                        raw_analysis = json.loads(json_str)
                        
                        # Validate and sanitize the JSON structure
                        analysis = self.validate_and_sanitize_gpt_json(raw_analysis, fundamentals)
                        return analysis
                    else:
                        raise ValueError("No valid JSON found")
                        
                except Exception as parse_error:
                    # If JSON parsing fails, extract key numbers from text
                    print(f"   ⚠️ GPT JSON parsing failed, using text extraction fallback")
                    return self.parse_gpt_text_fallback(gpt_response, fundamentals)
            
            else:
                print("   ❌ No function call or content in GPT response")
                return self.get_systematic_fallback(fundamentals, news, sector)
                
        except Exception as e:
            print(f"   ❌ GPT API error: {str(e)[:50]}, using systematic fallback")
            return self.get_systematic_fallback(fundamentals, news, sector)
    
    def validate_and_sanitize_gpt_json(self, raw_json: dict, fundamentals: dict) -> dict:
        """Validate and sanitize GPT JSON output to ensure data consistency."""
        current_price = fundamentals.get('current_price', 0)
        current_date = datetime.now()
        
        # Initialize validated structure
        validated = {
            "price_prediction": {},
            "catalyst_timeline": [],
            "risk_factors": [],
            "leaps_strategy": {},
            "overall_score": 50
        }
        
        try:
            # Validate price predictions
            price_pred = raw_json.get('price_prediction', {})
            
            # Sanitize 12-month target
            target_12m = self._sanitize_float(price_pred.get('12_month_target'), current_price * 0.5, current_price * 2.5, current_price * 1.1)
            
            # Sanitize 24-month target
            target_24m = self._sanitize_float(price_pred.get('24_month_target'), current_price * 0.5, current_price * 3.0, current_price * 1.25)
            
            # Ensure 24m target >= 12m target
            if target_24m < target_12m:
                target_24m = target_12m * 1.1
            
            # Sanitize confidence level
            confidence = self._sanitize_int(price_pred.get('confidence_level'), 20, 95, 65)
            
            validated["price_prediction"] = {
                "12_month_target": target_12m,
                "24_month_target": target_24m,
                "confidence_level": confidence,
                "methodology": str(price_pred.get('methodology', 'GPT analysis'))[:100],
                "key_assumptions": self._sanitize_list(price_pred.get('key_assumptions', []), str, 3)
            }
            
            # Validate catalysts
            catalysts = raw_json.get('catalyst_timeline', [])
            if isinstance(catalysts, list):
                for catalyst in catalysts[:5]:  # Max 5 catalysts
                    if isinstance(catalyst, dict):
                        event = str(catalyst.get('event', 'Unknown'))[:80]
                        timeline = str(catalyst.get('timeline', 'TBD'))[:30]
                        impact = str(catalyst.get('price_impact', 'N/A'))[:20]
                        
                        validated["catalyst_timeline"].append({
                            "event": event,
                            "timeline": timeline,
                            "price_impact": impact
                        })
            
            # Validate risk factors
            risks = raw_json.get('risk_factors', [])
            if isinstance(risks, list):
                for risk in risks[:5]:  # Max 5 risks
                    if isinstance(risk, dict):
                        risk_name = str(risk.get('risk', 'Unknown'))[:80]
                        probability = self._sanitize_int(risk.get('probability'), 0, 100, 30)
                        impact = str(risk.get('impact', 'N/A'))[:20]
                        
                        validated["risk_factors"].append({
                            "risk": risk_name,
                            "probability": probability,
                            "impact": impact
                        })
            
            # Validate LEAPS strategy
            leaps = raw_json.get('leaps_strategy', {})
            
            # Sanitize recommendation
            rec = str(leaps.get('recommendation', 'CONSIDER')).upper()
            if rec not in ['STRONG_BUY', 'BUY', 'CONSIDER', 'AVOID']:
                rec = 'CONSIDER'
            
            # Sanitize strike price
            optimal_strike = self._sanitize_float(
                leaps.get('optimal_strike'), 
                current_price * 0.5, 
                current_price * 1.5, 
                current_price * 0.9
            )
            
            # Sanitize expiry date
            expiry_date = str(leaps.get('expiry_date', ''))
            if not self._is_valid_future_date(expiry_date):
                expected_return = ((target_24m - current_price) / current_price * 100) if current_price > 0 else 25
                expiry_date = self.calculate_dynamic_expiry_dates(expected_return)
            
            # Sanitize position size and expected return
            position_size = self._sanitize_float(leaps.get('position_size'), 0.5, 10.0, 3.0)
            expected_return = self._sanitize_float(leaps.get('expected_return'), -50, 300, 25)
            
            validated["leaps_strategy"] = {
                "recommendation": rec,
                "optimal_strike": optimal_strike,
                "expiry_date": expiry_date,
                "position_size": position_size,
                "expected_return": expected_return
            }
            
            # Sanitize overall score
            overall_score = self._sanitize_int(raw_json.get('overall_score'), 10, 100, 50)
            validated["overall_score"] = overall_score
            
            return validated
            
        except Exception as e:
            print(f"   ⚠️ JSON validation error: {str(e)[:30]}, using defaults")
            # Return minimal valid structure
            return {
                "price_prediction": {
                    "12_month_target": current_price * 1.1,
                    "24_month_target": current_price * 1.25,
                    "confidence_level": 50,
                    "methodology": "GPT analysis (sanitized)",
                    "key_assumptions": ["Market conditions stable"]
                },
                "catalyst_timeline": [{"event": "General market conditions", "timeline": "12-24 months", "price_impact": "Variable"}],
                "risk_factors": [{"risk": "Market volatility", "probability": 50, "impact": "-15%"}],
                "leaps_strategy": {
                    "recommendation": "CONSIDER",
                    "optimal_strike": current_price * 0.9,
                    "expiry_date": self.calculate_dynamic_expiry_dates(25),
                    "position_size": 3.0,
                    "expected_return": 25
                },
                "overall_score": 50
            }
    
    def _sanitize_float(self, value, min_val: float, max_val: float, default: float) -> float:
        """Sanitize a float value within bounds."""
        try:
            if isinstance(value, str):
                # Remove percentage signs and other characters
                value = value.replace('%', '').replace('$', '').replace(',', '').strip()
            
            num_val = float(value)
            return max(min_val, min(max_val, num_val))
        except (ValueError, TypeError):
            return default
    
    def _sanitize_int(self, value, min_val: int, max_val: int, default: int) -> int:
        """Sanitize an integer value within bounds."""
        try:
            if isinstance(value, str):
                value = value.replace('%', '').replace(',', '').strip()
            
            int_val = int(float(value))
            return max(min_val, min(max_val, int_val))
        except (ValueError, TypeError):
            return default
    
    def _sanitize_list(self, value, item_type, max_items: int) -> list:
        """Sanitize a list to ensure proper type and length."""
        if not isinstance(value, list):
            return []
        
        sanitized = []
        for item in value[:max_items]:
            try:
                if item_type == str:
                    sanitized.append(str(item)[:100])  # Limit string length
                else:
                    sanitized.append(item_type(item))
            except:
                continue
        
        return sanitized
    
    def _is_valid_future_date(self, date_str: str) -> bool:
        """Check if date string represents a valid future date."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj > datetime.now() and (date_obj - datetime.now()).days >= 365
        except:
            return False

    def calculate_dynamic_expiry_dates(self, expected_return: float) -> str:
        """Calculate dynamic LEAPS expiry dates based on current date and available options."""
        current_date = datetime.now()
        
        def get_third_friday(year: int, month: int) -> datetime:
            """Get the third Friday of a given month and year."""
            first_day = datetime(year, month, 1)
            first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
            third_friday = first_friday + timedelta(days=14)
            return third_friday
        
        # Determine target expiry based on expected return and current date
        if expected_return > 60:
            # High conviction - 24+ month LEAPS
            target_year = current_date.year + 2
            target_month = 1  # January LEAPS
        elif expected_return > 35:
            # Medium conviction - 18+ month LEAPS
            months_ahead = 18
            target_date = current_date + timedelta(days=months_ahead * 30)
            target_year = target_date.year
            target_month = 1 if target_date.month <= 6 else 6  # Jan or Jun LEAPS
        else:
            # Lower conviction - 12+ month LEAPS
            target_year = current_date.year + 1
            target_month = 1  # January LEAPS next year
        
        # Get the actual third Friday
        try:
            expiry_date = get_third_friday(target_year, target_month)
            
            # Ensure it's at least 12 months out
            min_expiry = current_date + timedelta(days=365)
            if expiry_date < min_expiry:
                # Move to next year's January LEAPS
                expiry_date = get_third_friday(target_year + 1, 1)
            
            return expiry_date.strftime('%Y-%m-%d')
            
        except:
            # Fallback to safe future date
            return get_third_friday(current_date.year + 2, 1).strftime('%Y-%m-%d')
    
    def find_optimal_expiry_from_options(self, symbol: str, current_price: float) -> str:
        """Find the optimal expiry date from available options data."""
        try:
            ticker = yf.Ticker(symbol)
            options_chain = ticker.option_chain()
            
            if not options_chain or not hasattr(options_chain, 'calls'):
                return self.calculate_dynamic_expiry_dates(50)  # Default fallback
            
            calls = options_chain.calls
            if calls.empty:
                return self.calculate_dynamic_expiry_dates(50)
            
            # Get unique expiry dates and filter for LEAPS (12+ months)
            current_date = datetime.now()
            min_leaps_date = current_date + timedelta(days=365)
            
            available_expiries = []
            for expiry_str in calls['expiration'].unique():
                try:
                    expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                    if expiry_date >= min_leaps_date:
                        # Calculate liquidity score for this expiry
                        expiry_calls = calls[calls['expiration'] == expiry_str]
                        liquidity_score = (
                            expiry_calls['volume'].sum() * 0.4 +  # Volume weight
                            expiry_calls['openInterest'].sum() * 0.3 +  # OI weight
                            (1 / (expiry_calls['ask'] - expiry_calls['bid']).mean()) * 0.3  # Spread weight
                        )
                        
                        available_expiries.append({
                            'expiry': expiry_str,
                            'date': expiry_date,
                            'liquidity_score': liquidity_score,
                            'days_to_expiry': (expiry_date - current_date).days
                        })
                except:
                    continue
            
            if not available_expiries:
                return self.calculate_dynamic_expiry_dates(50)
            
            # Sort by liquidity score and select the best
            available_expiries.sort(key=lambda x: x['liquidity_score'], reverse=True)
            return available_expiries[0]['expiry']
            
        except Exception as e:
            print(f"⚠️ Error finding optimal expiry: {e}")
            return self.calculate_dynamic_expiry_dates(50)

    def select_optimal_leaps_contract(self, symbol: str, current_price: float, recommendation: str, expected_return: float) -> dict:
        """Select optimal LEAPS contract based on real option chain data."""
        # Get real option chain data
        option_data = self.get_yfinance_option_chains(symbol, current_price)
        
        if not option_data.get('leaps_exists'):
            # Use optimal expiry selection even when no LEAPS data
            optimal_expiry = self.find_optimal_expiry_from_options(symbol, current_price)
            return {
                'has_real_data': False,
                'optimal_strike': current_price * 0.90,
                'expiry_date': optimal_expiry,
                'estimated_cost': 500,  # Default assumption
                'reason': option_data.get('reason', 'No LEAPS data')
            }
        
        best_contracts = option_data.get('best_contracts', [])
        
        # Filter contracts by recommendation type (but no cost limits)
        strike_multipliers = {
            'STRONG_BUY': (0.70, 1.00),  # Deep ITM to ATM
            'BUY': (0.80, 1.10),         # ITM to slightly OTM
            'CONSIDER': (0.85, 1.20),    # Near ATM to OTM
            'AVOID': (0.90, 1.30)        # OTM range
        }
        
        min_mult, max_mult = strike_multipliers.get(recommendation, (0.80, 1.20))
        min_strike = current_price * min_mult
        max_strike = current_price * max_mult
        
        # Find all suitable contracts and analyze for arbitrage opportunities
        suitable_contracts = []
        for contract in best_contracts:
            strike = contract['strike']
            
            # Check if strike is in our target range and has decent liquidity
            if min_strike <= strike <= max_strike and contract['openInterest'] >= 50:
                suitable_contracts.append(contract)
        
        if not suitable_contracts:
            # Expand search if no contracts found
            suitable_contracts = [c for c in best_contracts if c['openInterest'] >= 50]
        
        if suitable_contracts:
            # Analyze for arbitrage opportunities and optimal value
            for contract in suitable_contracts:
                # Calculate value metrics
                intrinsic_value = max(0, current_price - contract['strike'])
                time_value = contract['midPrice'] - intrinsic_value
                
                # Calculate efficiency ratio (delta per dollar spent)
                days_to_expiry = contract['daysToExpiry']
                time_to_expiry_years = days_to_expiry / 365.25
                
                # Estimate delta using simple approximation
                moneyness = current_price / contract['strike']
                estimated_delta = min(0.95, max(0.05, 0.5 + (moneyness - 1) * 2))
                
                # Value efficiency: delta per dollar of premium
                efficiency = estimated_delta / max(0.01, contract['midPrice']) if contract['midPrice'] > 0 else 0
                
                # Time decay resistance (good for LEAPS)
                time_decay_resistance = time_to_expiry_years * 10  # Longer time = better
                
                # Overall value score
                contract['value_score'] = (
                    efficiency * 40 +  # 40% weight on efficiency
                    time_decay_resistance * 30 +  # 30% weight on time
                    (contract['liquidityScore'] / 100) * 20 +  # 20% weight on liquidity
                    (10 if contract['spreadPct'] <= 5 else 5 if contract['spreadPct'] <= 10 else 0)  # 10% weight on spread
                )
                
                contract['estimated_delta'] = estimated_delta
                contract['efficiency_ratio'] = efficiency
                contract['intrinsic_value'] = intrinsic_value
                contract['time_value'] = time_value
            
            # Sort by value score to find the best contract
            suitable_contracts.sort(key=lambda x: x['value_score'], reverse=True)
            best_contract = suitable_contracts[0]
            
            # Enhanced arbitrage detection - find opportunities like ZETA example
            arbitrage_opportunities = []
            
            # Sort contracts by strike for easier comparison
            strike_sorted = sorted(suitable_contracts, key=lambda x: x['strike'])
            
            for i, contract in enumerate(strike_sorted):
                for j, other_contract in enumerate(strike_sorted):
                    if i != j:
                        # Check if higher strike is cheaper (classic arbitrage)
                        if (contract['strike'] > other_contract['strike'] and 
                            contract['midPrice'] < other_contract['midPrice'] and
                            contract['midPrice'] > 0 and other_contract['midPrice'] > 0):
                            
                            savings = other_contract['midPrice'] - contract['midPrice']
                            efficiency_gain = contract.get('efficiency_ratio', 0) - other_contract.get('efficiency_ratio', 0)
                            
                            # Calculate total cost including premium (like ZETA example)
                            total_cost_higher = contract['strike'] + contract['midPrice']
                            total_cost_lower = other_contract['strike'] + other_contract['midPrice']
                            total_savings = total_cost_lower - total_cost_higher
                            
                            arbitrage_opportunities.append({
                                'higher_strike': contract['strike'],
                                'lower_strike': other_contract['strike'],
                                'higher_cost': contract['contractCost'],
                                'lower_cost': other_contract['contractCost'],
                                'savings_per_share': savings,
                                'savings_per_contract': savings * 100,
                                'total_cost_savings': total_savings * 100,  # Total cost including premium
                                'efficiency_gain': efficiency_gain,
                                'type': 'higher_strike_cheaper',
                                'description': f"${contract['strike']} strike + ${contract['midPrice']:.2f} premium = ${total_cost_higher:.2f} vs ${other_contract['strike']} strike + ${other_contract['midPrice']:.2f} premium = ${total_cost_lower:.2f}"
                            })
            
            # Additional arbitrage detection: Calendar spreads and time decay opportunities
            for i, contract in enumerate(suitable_contracts):
                for j, other_contract in enumerate(suitable_contracts):
                    if i != j and contract['strike'] == other_contract['strike']:
                        # Same strike, different expiries - calendar spread opportunity
                        if (contract['daysToExpiry'] > other_contract['daysToExpiry'] and
                            contract['midPrice'] < other_contract['midPrice']):
                            
                            time_decay_arbitrage = other_contract['midPrice'] - contract['midPrice']
                            
                            arbitrage_opportunities.append({
                                'strike': contract['strike'],
                                'longer_expiry': contract['expiry'],
                                'shorter_expiry': other_contract['expiry'],
                                'longer_cost': contract['contractCost'],
                                'shorter_cost': other_contract['contractCost'],
                                'time_decay_savings': time_decay_arbitrage * 100,
                                'type': 'calendar_spread',
                                'description': f"Same ${contract['strike']} strike: {contract['expiry']} (${contract['midPrice']:.2f}) vs {other_contract['expiry']} (${other_contract['midPrice']:.2f})"
                            })
            
            # Volume-based arbitrage: High volume contracts that might be mispriced
            for contract in suitable_contracts:
                if contract['volume'] > 1000 and contract['spreadPct'] < 5:  # High volume, tight spread
                    # Look for similar strikes with worse pricing
                    for other_contract in suitable_contracts:
                        if (abs(contract['strike'] - other_contract['strike']) <= 2.5 and  # Similar strikes
                            contract['strike'] != other_contract['strike'] and
                            other_contract['volume'] < contract['volume'] and  # Lower volume
                            other_contract['spreadPct'] > contract['spreadPct']):  # Worse spread
                            
                            volume_arbitrage = other_contract['midPrice'] - contract['midPrice']
                            
                            arbitrage_opportunities.append({
                                'recommended_strike': contract['strike'],
                                'avoid_strike': other_contract['strike'],
                                'recommended_cost': contract['contractCost'],
                                'avoid_cost': other_contract['contractCost'],
                                'volume_advantage': contract['volume'] - other_contract['volume'],
                                'spread_advantage': other_contract['spreadPct'] - contract['spreadPct'],
                                'savings': volume_arbitrage * 100,
                                'type': 'volume_liquidity',
                                'description': f"Better liquidity: ${contract['strike']} strike (Vol: {contract['volume']}, Spread: {contract['spreadPct']:.1f}%) vs ${other_contract['strike']} (Vol: {other_contract['volume']}, Spread: {other_contract['spreadPct']:.1f}%)"
                            })
            
            # Remove duplicates and sort by savings
            seen = set()
            unique_arbitrage = []
            for arb in arbitrage_opportunities:
                key = (arb['higher_strike'], arb['lower_strike'])
                if key not in seen:
                    seen.add(key)
                    unique_arbitrage.append(arb)
            
            arbitrage_opportunities = sorted(unique_arbitrage, key=lambda x: x['savings_per_contract'], reverse=True)
            
            return {
                'has_real_data': True,
                'optimal_strike': best_contract['strike'],
                'expiry_date': best_contract['expiry'],
                'estimated_cost': best_contract['contractCost'],
                'bid_ask_spread': best_contract['spreadPct'],
                'open_interest': best_contract['openInterest'],
                'volume': best_contract['volume'],
                'estimated_delta': best_contract['estimated_delta'],
                'efficiency_ratio': best_contract['efficiency_ratio'],
                'value_score': best_contract['value_score'],
                'intrinsic_value': best_contract['intrinsic_value'],
                'time_value': best_contract['time_value'],
                'arbitrage_opportunities': arbitrage_opportunities[:3],  # Top 3 arbitrage opportunities
                'reason': f"Best value: ${best_contract['contractCost']:.0f} cost, {best_contract['estimated_delta']:.2f} delta, {best_contract['openInterest']} OI"
            }
        
        # Fallback: find any reasonable contract
        if best_contracts:
            # Just pick the most liquid contract
            best_liquid = max(best_contracts, key=lambda x: x['liquidityScore'])
            return {
                'has_real_data': True,
                'optimal_strike': best_liquid['strike'],
                'expiry_date': best_liquid['expiry'],
                'estimated_cost': best_liquid['contractCost'],
                'bid_ask_spread': best_liquid['spreadPct'],
                'open_interest': best_liquid['openInterest'],
                'volume': best_liquid['volume'],
                'reason': f"Most liquid: ${best_liquid['contractCost']:.0f} cost, {best_liquid['openInterest']} OI"
            }
        
        # Ultimate fallback
        return {
            'has_real_data': False,
            'optimal_strike': current_price * ((min_mult + max_mult) / 2),
            'expiry_date': self.calculate_dynamic_expiry_dates(expected_return),
            'estimated_cost': target_cost,
            'reason': 'No suitable liquid contracts found'
        }

    def get_systematic_fallback(self, fundamentals: dict, news: dict, sector: dict) -> dict:
        """Systematic fallback analysis when GPT unavailable."""
        current_price = fundamentals['current_price']
        revenue_growth = fundamentals['revenue_growth']
        analyst_upside = fundamentals['analyst_upside']
        analyst_target = fundamentals['analyst_target']
        symbol = fundamentals['symbol']
        
        # Systematic price prediction model with penalty system
        base_multiplier = 1.0
        
        # Growth factor with penalties for negative growth
        if revenue_growth > 50:
            base_multiplier += 0.30
        elif revenue_growth > 25:
            base_multiplier += 0.20
        elif revenue_growth > 15:
            base_multiplier += 0.10
        elif revenue_growth > 0:
            base_multiplier += 0.05
        elif revenue_growth < -10:
            base_multiplier -= 0.15  # Penalty for declining revenue
        elif revenue_growth < 0:
            base_multiplier -= 0.10
        
        # Profitability factor with penalties for losses
        profit_margin = fundamentals['profit_margin']
        operating_margin = fundamentals['operating_margin']
        
        if profit_margin > 15:
            base_multiplier += 0.20
        elif profit_margin > 10:
            base_multiplier += 0.15
        elif profit_margin > 5:
            base_multiplier += 0.10
        elif profit_margin > 0:
            base_multiplier += 0.05
        elif profit_margin < -10:
            base_multiplier -= 0.15  # Heavy penalty for big losses
        elif profit_margin < 0:
            base_multiplier -= 0.10
        elif operating_margin > 0:
            base_multiplier += 0.03  # Small bonus for operational profitability
        
        # Financial health penalties
        debt_to_equity = fundamentals.get('debt_to_equity', 0)
        current_ratio = fundamentals.get('current_ratio', 1)
        
        if not np.isnan(debt_to_equity) and debt_to_equity > 100:
            base_multiplier -= 0.05  # High debt penalty
        if not np.isnan(current_ratio) and current_ratio < 1:
            base_multiplier -= 0.05  # Liquidity concern penalty
        
        # Enhanced volatility and trend analysis
        volatility = fundamentals.get('volatility_annual', 0)
        volatility_trend = fundamentals.get('volatility_trend', 0)
        momentum_score = fundamentals.get('momentum_score', 0)
        
        # Volatility penalties and adjustments
        if volatility > 100:
            base_multiplier -= 0.08  # Extreme volatility penalty
        elif volatility > 80:
            base_multiplier -= 0.05  # High volatility penalty
        elif volatility > 60:
            base_multiplier -= 0.02  # Moderate volatility penalty
        elif volatility < 20:
            base_multiplier += 0.02  # Low volatility bonus (stable stock)
        
        # Volatility trend adjustments
        if volatility_trend > 50:
            base_multiplier -= 0.03  # Increasing volatility penalty
        elif volatility_trend < -30:
            base_multiplier += 0.02  # Decreasing volatility bonus
        
        # Momentum scoring
        if momentum_score > 20:
            base_multiplier += 0.06  # Strong positive momentum
        elif momentum_score > 10:
            base_multiplier += 0.03  # Moderate positive momentum
        elif momentum_score < -20:
            base_multiplier -= 0.06  # Strong negative momentum
        elif momentum_score < -10:
            base_multiplier -= 0.03  # Moderate negative momentum
        
        # Short interest analysis
        short_percent = fundamentals.get('short_percent_float', 0)
        if short_percent > 20:
            base_multiplier -= 0.08  # Heavy short interest penalty
        elif short_percent > 10:
            base_multiplier -= 0.05  # Moderate short interest penalty
        elif short_percent < 2:
            base_multiplier += 0.02  # Low short interest bonus
        
        # Institutional ownership analysis
        institutional_percent = fundamentals.get('institutional_percent', 0) * 100
        if institutional_percent > 80:
            base_multiplier -= 0.03  # Over-owned by institutions
        elif institutional_percent < 20:
            base_multiplier += 0.05  # Under-discovered bonus
        elif institutional_percent < 40:
            base_multiplier += 0.02  # Moderately under-owned bonus
        
        # Analyst factor
        if analyst_upside > 50:
            base_multiplier += 0.15
        elif analyst_upside > 25:
            base_multiplier += 0.10
        elif analyst_upside < -20:
            base_multiplier -= 0.10  # Analyst pessimism penalty
        
        # News factor
        news_score = news.get('news_score', 50)
        if news_score > 70:
            base_multiplier += 0.08
        elif news_score > 60:
            base_multiplier += 0.05
        elif news_score < 30:
            base_multiplier -= 0.08  # Negative news penalty
        elif news_score < 40:
            base_multiplier -= 0.05
        
        # Sector factor
        sector_score = sector.get('sector_score', 50)
        if sector_score > 80:
            base_multiplier += 0.12
        elif sector_score > 70:
            base_multiplier += 0.10
        elif sector_score < 30:
            base_multiplier -= 0.08
        elif sector_score < 40:
            base_multiplier -= 0.05
        
        # Calculate targets
        twelve_month_target = current_price * (1 + (base_multiplier - 1) * 0.6)
        twenty_four_month_target = current_price * base_multiplier
        
        # Determine LEAPS strategy
        expected_return = ((twenty_four_month_target - current_price) / current_price * 100)
        
        if expected_return > 60:
            recommendation = "STRONG_BUY"
            position_size = 4.0
        elif expected_return > 35:
            recommendation = "BUY"
            position_size = 3.0
        elif expected_return > 20:
            recommendation = "CONSIDER"
            position_size = 2.0
        else:
            recommendation = "AVOID"
            position_size = 0
        
        # Get optimal LEAPS contract with real data
        leaps_contract = self.select_optimal_leaps_contract(symbol, current_price, recommendation, expected_return)
        
        # Calculate Greeks for the recommended contract (always calculate if we have a strike and expiry)
        greeks_analysis = {}
        if leaps_contract.get('optimal_strike') and leaps_contract.get('expiry_date'):
            volatility = fundamentals.get('volatility_annual', 30)  # Use calculated volatility
            greeks_analysis = self.analyze_leaps_greeks(
                symbol=symbol,
                current_price=current_price,
                strike=leaps_contract['optimal_strike'],
                expiry_date=leaps_contract['expiry_date'],
                market_volatility=volatility
            )
        
        # Calculate confidence
        confidence = min(90, max(30, int(
            50 +  # Base
            (revenue_growth / 5) +  # Growth confidence
            (min(25, analyst_upside / 2)) +  # Analyst confidence
            (10 if fundamentals['num_analysts'] >= 5 else 5) +  # Coverage confidence
            (-5 if profit_margin < 0 else 0) +  # Profitability penalty
            (-3 if volatility > 80 else 0)  # Volatility penalty
        )))
        
        return {
            "price_prediction": {
                "12_month_target": twelve_month_target,
                "24_month_target": twenty_four_month_target,
                "confidence_level": confidence,
                "methodology": "Enhanced systematic multi-factor model",
                "key_assumptions": [f"{revenue_growth:.0f}% growth continues", "Market conditions stable"]
            },
            "catalyst_timeline": [
                {"event": "Earnings reports", "timeline": "Quarterly", "price_impact": "+5-10%"},
                {"event": "Growth execution", "timeline": "12-24 months", "price_impact": f"+{expected_return/2:.0f}%"}
            ],
            "risk_factors": [
                {"risk": "Growth deceleration", "probability": 35, "impact": f"-{expected_return/3:.0f}%"},
                {"risk": "Market volatility", "probability": 50, "impact": "-15%"},
                {"risk": "Profitability pressure", "probability": 30 if profit_margin < 5 else 20, "impact": "-10%"}
            ],
            "leaps_strategy": {
                "recommendation": recommendation,
                "optimal_strike": leaps_contract['optimal_strike'],
                "expiry_date": leaps_contract['expiry_date'],
                "position_size": position_size,
                "expected_return": expected_return,
                "contract_cost": leaps_contract['estimated_cost'],
                "has_real_data": leaps_contract['has_real_data'],
                "liquidity_info": leaps_contract.get('reason', 'Estimated'),
                "greeks_analysis": greeks_analysis
            },
            "overall_score": confidence,
            "is_systematic_model": True
        }
    
    def parse_gpt_text_fallback(self, gpt_text: str, fundamentals: dict) -> dict:
        """Extract key insights from GPT text when JSON parsing fails."""
        current_price = fundamentals['current_price']
        
        # Try to extract price targets from text
        import re
        
        # Look for price patterns
        price_patterns = [
            r'\$(\d+\.?\d*)',  # $25.50
            r'(\d+\.?\d*)\s*dollars',  # 25.50 dollars
            r'target.*?(\d+\.?\d*)',  # target 25.50
        ]
        
        prices_found = []
        for pattern in price_patterns:
            matches = re.findall(pattern, gpt_text)
            for match in matches:
                try:
                    price = float(match)
                    if current_price * 0.5 <= price <= current_price * 3:  # Reasonable range
                        prices_found.append(price)
                except:
                    continue
        
        # Use median of found prices or fallback
        if prices_found:
            target_price = np.median(prices_found)
        else:
            target_price = current_price * 1.25  # 25% upside fallback
        
        expected_return = ((target_price - current_price) / current_price * 100)
        
        # Use dynamic expiry calculation for GPT fallback too
        expiry_date = self.calculate_dynamic_expiry_dates(expected_return)
        
        return {
            "price_prediction": {
                "24_month_target": target_price,
                "confidence_level": 60,
                "methodology": "GPT analysis (text parsed)"
            },
            "leaps_strategy": {
                "recommendation": "BUY" if expected_return > 25 else "CONSIDER" if expected_return > 15 else "AVOID",
                "optimal_strike": current_price * 0.90,
                "expiry_date": expiry_date,  # Fixed future date
                "expected_return": expected_return
            },
            "overall_score": min(80, max(40, int(50 + expected_return))),
            "gpt_text_summary": gpt_text[:200] + "..."
        }
    
    def complete_systematic_analysis(self, symbol: str) -> dict:
        """Complete systematic analysis - all components integrated."""
        print(f"\n🎯 COMPLETE SYSTEMATIC ANALYSIS: {symbol}")
        print("=" * 80)
        
        # Stage 1: Comprehensive fundamentals
        print("📊 Comprehensive fundamentals...", end=' ')
        fundamentals = self.get_all_fundamental_data(symbol)
        if not fundamentals:
            print("❌ No fundamental data available")
            print(f"   💡 Suggestion: Check if '{symbol}' is a valid ticker symbol")
            return {}
        print("✅")
        
        # Stage 2: News sentiment
        print("📰 News sentiment analysis...", end=' ')
        news = self.get_news_sentiment(symbol)
        method = news.get('analysis_method', 'unknown')
        method_display = {
            'finbert': 'FinBERT',
            'keyword_fallback': 'keywords',
            'no_news': 'no news',
            'no_valid_articles': 'no articles',
            'error_fallback': 'error'
        }.get(method, method)
        print(f"✅ {news['sentiment']} ({news['valid_articles']} articles, {method_display})")
        
        # Stage 3: Sector analysis
        print("🏭 Sector analysis...", end=' ')
        sector = self.get_sector_analysis(fundamentals['sector'], fundamentals['industry'])
        print(f"✅ {sector['growth_outlook']} outlook")
        
        # Stage 4: Real option chain analysis
        print("📊 Real option chain analysis...", end=' ')
        option_data = self.get_yfinance_option_chains(symbol, fundamentals['current_price'])
        if option_data.get('leaps_exists'):
            print(f"✅ {option_data['liquid_contracts']} liquid LEAPS")
        else:
            print(f"❌ {option_data.get('reason', 'No LEAPS')}")
        
        # Stage 5: IBKR LEAPS verification (if market open)
        ibkr_data = {'available': False, 'reason': 'Market closed or IBKR unavailable'}
        if self.try_ibkr:
            print("🔌 IBKR LEAPS verification...", end=' ')
            if self.try_ibkr_connection():
                ibkr_data = self.get_ibkr_leaps_data(symbol)
                self.disconnect_ibkr()
                if ibkr_data.get('leaps_exists'):
                    print(f"✅ LEAPS confirmed")
                else:
                    print(f"❌ No LEAPS")
            else:
                print("❌ Connection failed")
        
        # Stage 6: Integrated GPT analysis (with current date context)
        today = datetime.now().strftime("%B %d, %Y")
        print(f"🤖 Integrated GPT analysis (Context: {today})...", end=' ')
        gpt_analysis = self.get_gpt_analysis(symbol, fundamentals, news, sector)
        print("✅")
        
        # Stage 7: IV Analysis (Enhanced)
        print("📈 IV analysis & skew detection...", end=' ')
        iv_analyzer = ImpliedVolatilityAnalyzer(symbol)
        iv_analysis = iv_analyzer.analyze_current_iv()
        if 'error' not in iv_analysis:
            iv_pct = iv_analysis.get('iv_percentile', 50)
            print(f"✅ IV @ {iv_pct:.0f}th percentile")
        else:
            print(f"⚠️ {iv_analysis.get('error', 'No IV data')}")
        
        # Stage 8: Multi-Expiry Spread Analysis
        print("🔄 Multi-expiry spread opportunities...", end=' ')
        spread_analyzer = MultiExpiryAnalyzer(symbol, fundamentals['current_price'])
        spread_opportunities = spread_analyzer.find_diagonal_spread_opportunities()
        if spread_opportunities:
            print(f"✅ {len(spread_opportunities)} opportunities found")
        else:
            print("⚠️ No spreads available")
        
        # Stage 8b: Cross-Strike Arbitrage (ZETA-style)
        print("💰 Cross-strike arbitrage detection...", end=' ')
        cross_strike_arb = spread_analyzer.find_cross_strike_arbitrage()
        if cross_strike_arb:
            print(f"✅ {len(cross_strike_arb)} arbitrage opportunities")
        else:
            print("⚠️ No arbitrage found")
        
        # Stage 9: Final systematic scoring
        print("🎯 Final systematic scoring...", end=' ')
        final_score = self.calculate_systematic_score(fundamentals, news, sector, gpt_analysis)
        
        # Calculate IV-adjusted verdict
        iv_rec = self.get_iv_adjusted_recommendation(final_score, iv_analysis)
        print(f"✅ {final_score}/100 -> {iv_rec['verdict']}")
        
        return {
            'symbol': symbol,
            'fundamentals': fundamentals,
            'news': news,
            'news_sentiment': news, # Alias for compatibility
            'sector': sector,
            'option_data': option_data,
            'ibkr_data': ibkr_data,
            'gpt_analysis': gpt_analysis,
            'iv_analysis': iv_analysis,
            'spread_opportunities': spread_opportunities,
            'cross_strike_arbitrage': cross_strike_arb,
            'final_score': final_score,
            'systematic_score': final_score, # Alias for compatibility
            'verdict': iv_rec['verdict'],
            'recommendation_details': iv_rec
        }
    
    def calculate_systematic_score(self, fundamentals: dict, news: dict, sector: dict, gpt: dict) -> int:
        """Calculate final systematic score using all components."""
        
        # Base score from fundamentals (40%)
        revenue_growth = fundamentals['revenue_growth']
        analyst_upside = fundamentals['analyst_upside']
        profit_margin = fundamentals['profit_margin']
        
        fundamental_score = (
            min(30, revenue_growth / 2) +  # Revenue growth (max 30)
            min(25, analyst_upside / 2) +  # Analyst optimism (max 25)
            (15 if profit_margin > 10 else 10 if profit_margin > 0 else 5 if fundamentals['operating_margin'] > 0 else 0)  # Profitability (max 15)
        )
        
        # News impact (15%)
        news_adjustment = (news['news_score'] - 50) * 0.3
        
        # Sector strength (15%)
        sector_adjustment = (sector['sector_score'] - 50) * 0.3
        
        # GPT enhancement (30%)
        gpt_score = gpt.get('overall_score', 50)
        gpt_adjustment = (gpt_score - 50) * 0.6
        
        # Combine all factors
        total_score = fundamental_score + news_adjustment + sector_adjustment + gpt_adjustment
        
        return max(10, min(100, int(total_score)))
    
    def get_iv_adjusted_recommendation(self, base_score: int, iv_analysis: dict) -> dict:
        """Adjust recommendation based on IV percentile."""
        if 'error' in iv_analysis:
            return {
                'adjusted_score': base_score,
                'verdict': self._score_to_verdict(base_score),
                'iv_adjustment': 0,
                'warning': None
            }
        
        iv_percentile = iv_analysis.get('iv_percentile', 50)
        
        # IV adjustment logic
        if iv_percentile >= 80:
            # Extreme IV - major warning
            adjustment = -15
            warning = f"⚠️ EXTREME IV ({iv_percentile:.0f}th percentile) - Strongly recommend WAITING for IV to drop"
            action = "WAIT for IV < 60th percentile before entering"
        elif iv_percentile >= 60:
            # High IV - caution
            adjustment = -10
            warning = f"⚠️ HIGH IV ({iv_percentile:.0f}th percentile) - Consider waiting for better entry"
            action = "CAUTION - IV above average, consider smaller position or wait"
        elif iv_percentile <= 20:
            # Low IV - bonus!
            adjustment = +5
            warning = f"✅ EXCELLENT IV ({iv_percentile:.0f}th percentile) - Great entry opportunity"
            action = "STRONG BUY - IV at historical lows, excellent timing"
        elif iv_percentile <= 40:
            # Below average IV - good
            adjustment = +3
            warning = f"✅ GOOD IV ({iv_percentile:.0f}th percentile) - Favorable entry conditions"
            action = "BUY - IV below average, good timing"
        else:
            # Normal IV
            adjustment = 0
            warning = None
            action = None
        
        adjusted_score = max(10, min(100, base_score + adjustment))
        
        return {
            'adjusted_score': adjusted_score,
            'base_score': base_score,
            'verdict': self._score_to_verdict(adjusted_score),
            'base_verdict': self._score_to_verdict(base_score),
            'iv_adjustment': adjustment,
            'iv_percentile': iv_percentile,
            'warning': warning,
            'recommended_action': action
        }
    
    def _score_to_verdict(self, score: int) -> str:
        """Convert score to verdict string."""
        if score >= 75:
            return "STRONG BUY LEAPS"
        elif score >= 60:
            return "BUY LEAPS"
        elif score >= 45:
            return "CONSIDER LEAPS"
        elif score >= 30:
            return "AVOID LEAPS"
        else:
            return "STRONG AVOID"
    
    def display_complete_analysis(self, analysis: dict):
        """Display complete systematic analysis."""
        if not analysis:
            return
        
        symbol = analysis['symbol']
        fund = analysis['fundamentals']
        news = analysis['news']
        sector = analysis['sector']
        option_data = analysis.get('option_data', {})
        ibkr = analysis['ibkr_data']
        gpt = analysis['gpt_analysis']
        score = analysis['final_score']
        iv_analysis = analysis.get('iv_analysis', {})
        
        # Get IV-adjusted recommendation
        iv_adjusted = self.get_iv_adjusted_recommendation(score, iv_analysis)
        
        print(f"\n" + "="*120)
        print(f"🎯 COMPLETE SYSTEMATIC LEAPS ANALYSIS: {symbol}")
        print(f"🏢 {fund['company_name']}")
        print("="*120)
        
        # Executive verdict with IV adjustment
        adjusted_score = iv_adjusted['adjusted_score']
        base_score = iv_adjusted['base_score']
        
        if adjusted_score >= 75:
            verdict = "🚀 STRONG BUY LEAPS"
            confidence = "HIGH"
        elif adjusted_score >= 60:
            verdict = "🟢 BUY LEAPS"
            confidence = "MEDIUM-HIGH"
        elif adjusted_score >= 45:
            verdict = "🟡 CONSIDER LEAPS"
            confidence = "MEDIUM"
        elif adjusted_score >= 30:
            verdict = "🔴 AVOID LEAPS"
            confidence = "LOW"
        else:
            verdict = "🔴 STRONG AVOID"
            confidence = "LOW"
        
        print(f"\n🏆 SYSTEMATIC VERDICT:")
        print(f"   {verdict} (Systematic Score: {adjusted_score}/100)")
        
        # Show IV adjustment if significant
        if iv_adjusted['iv_adjustment'] != 0:
            print(f"   Base Score: {base_score}/100 → IV Adjusted: {adjusted_score}/100 ({iv_adjusted['iv_adjustment']:+d} pts)")
        
        print(f"   Analysis Confidence: {confidence}")
        
        # Display IV warning/recommendation
        if iv_adjusted['warning']:
            print(f"\n   {iv_adjusted['warning']}")
        if iv_adjusted['recommended_action']:
            print(f"   📍 Recommended Action: {iv_adjusted['recommended_action']}")
        
        # Integrated price predictions
        price_pred = gpt.get('price_prediction', {})
        if price_pred:
            current = fund['current_price']
            target_12m = price_pred.get('12_month_target', current)
            target_24m = price_pred.get('24_month_target', current)
            
            print(f"\n🎯 INTEGRATED PRICE PREDICTIONS:")
            print(f"   Current Price: ${current:.2f}")
            print(f"   12-Month Target: ${target_12m:.2f} ({((target_12m-current)/current*100):+.0f}%)")
            print(f"   24-Month Target: ${target_24m:.2f} ({((target_24m-current)/current*100):+.0f}%)")
            print(f"   Methodology: {price_pred.get('methodology', 'Systematic model')}")
            print(f"   Confidence: {price_pred.get('confidence_level', 50)}%")
        
        # Enhanced LEAPS strategy with real contract data
        leaps_strat = gpt.get('leaps_strategy', {})
        if leaps_strat and leaps_strat.get('recommendation') not in ['AVOID']:
            print(f"\n🎯 ENHANCED LEAPS STRATEGY:")
            print(f"   Recommendation: {leaps_strat.get('recommendation', 'N/A')}")
            print(f"   Optimal Strike: ${leaps_strat.get('optimal_strike', 0):.2f}")
            print(f"   Expiry: {leaps_strat.get('expiry_date', 'N/A')} ✅")
            print(f"   Position Size: {leaps_strat.get('position_size', 0):.1f}% of portfolio")
            print(f"   Expected Return: {leaps_strat.get('expected_return', 0):.0f}%")
            
            # Show enhanced contract analysis
            if leaps_strat.get('has_real_data'):
                print(f"   Contract Cost: ${leaps_strat.get('contract_cost', 500):.0f} per contract")
                print(f"   Estimated Delta: {leaps_strat.get('estimated_delta', 0):.3f}")
                print(f"   Efficiency Ratio: {leaps_strat.get('efficiency_ratio', 0):.4f} (delta per $)")
                print(f"   Value Score: {leaps_strat.get('value_score', 0):.1f}")
                print(f"   Liquidity: {leaps_strat.get('liquidity_info', 'N/A')}")
                
                # Show intrinsic vs time value breakdown
                intrinsic = leaps_strat.get('intrinsic_value', 0)
                time_val = leaps_strat.get('time_value', 0)
                if intrinsic > 0 or time_val > 0:
                    print(f"   Value Breakdown: ${intrinsic:.2f} intrinsic + ${time_val:.2f} time value")
                
                # Show arbitrage opportunities if found
                arbitrage_ops = leaps_strat.get('arbitrage_opportunities', [])
                if arbitrage_ops:
                    print(f"\n💰 ARBITRAGE OPPORTUNITIES DETECTED:")
                    for i, arb in enumerate(arbitrage_ops, 1):
                        print(f"      {i}. ${arb['higher_strike']:.1f} strike cheaper than ${arb['lower_strike']:.1f} by ${arb['savings_per_contract']:.0f}/contract")
                        print(f"         Efficiency gain: {arb['efficiency_gain']:.4f} delta per $")
                
            else:
                print(f"   Contract Cost: ~${leaps_strat.get('contract_cost', 500):.0f} (estimated)")
                print(f"   Note: {leaps_strat.get('liquidity_info', 'Based on systematic model')}")
            
            # Show Greeks analysis if available
            greeks = leaps_strat.get('greeks_analysis', {})
            if greeks and not greeks.get('error'):
                print(f"\n🔢 OPTIONS GREEKS ANALYSIS:")
                print(f"   Delta: {greeks.get('delta', 0):.3f} - {greeks.get('interpretations', {}).get('delta', 'N/A')}")
                print(f"   Theta: {greeks.get('theta', 0):.3f} - {greeks.get('interpretations', {}).get('theta', 'N/A')}")
                print(f"   Vega: {greeks.get('vega', 0):.3f} - {greeks.get('interpretations', {}).get('vega', 'N/A')}")
                print(f"   LEAPS Suitability: {greeks.get('leaps_suitability', 'N/A')}")
                
                # Show theoretical vs market price if we have real data
                if greeks.get('theoretical_price'):
                    print(f"   Theoretical Price: ${greeks['theoretical_price']:.2f}")
                    
            elif greeks.get('error'):
                print(f"\n🔢 OPTIONS GREEKS: ⚠️ {greeks['error']}")
        
        # Real Option Chain Analysis Results
        if option_data.get('leaps_exists'):
            print(f"\n📊 REAL OPTION CHAIN ANALYSIS:")
            print(f"   Total LEAPS Expiries: {option_data.get('total_expiries', 0)}")
            print(f"   Liquid Contracts Found: {option_data.get('liquid_contracts', 0)}")
            
            # Show top 3 most liquid contracts
            best_contracts = option_data.get('best_contracts', [])[:3]
            if best_contracts:
                print(f"   Top Liquid Contracts:")
                for i, contract in enumerate(best_contracts, 1):
                    print(f"      {i}. ${contract['strike']:.1f} strike, {contract['expiry']} "
                          f"(${contract['contractCost']:.0f}, OI: {contract['openInterest']}, "
                          f"Spread: {contract['spreadPct']:.1f}%)")
        elif option_data.get('available'):
            print(f"\n📊 OPTION CHAIN STATUS: ❌ {option_data.get('reason', 'No LEAPS available')}")
        else:
            print(f"\n📊 OPTION CHAIN STATUS: ⚠️ Could not retrieve option data")
        
        # IBKR LEAPS verification results
        print(f"\n🔌 IBKR LEAPS VERIFICATION:")
        if ibkr.get('available') and ibkr.get('leaps_exists'):
            print(f"   ✅ LEAPS CONFIRMED in IBKR")
            print(f"   IBKR Price: ${ibkr.get('ibkr_price', 0):.2f}")
            print(f"   Available Expiries: {ibkr.get('leaps_expiries', 0)}")
        elif ibkr.get('available'):
            print(f"   ❌ NO LEAPS in IBKR - {ibkr.get('reason', 'Unknown')}")
        else:
            print(f"   ⏳ {ibkr.get('reason', 'IBKR check skipped')}")
        
        # Enhanced component breakdown with scoring details
        print(f"\n📊 ENHANCED SCORING BREAKDOWN:")
        
        # Calculate individual score components for transparency
        revenue_growth = fund['revenue_growth']
        analyst_upside = fund['analyst_upside']
        profit_margin = fund['profit_margin']
        
        # Fundamental score calculation (matches the scoring logic)
        fundamental_score = (
            min(30, revenue_growth / 2) +
            min(25, analyst_upside / 2) +
            (15 if profit_margin > 10 else 10 if profit_margin > 0 else 5 if fund['operating_margin'] > 0 else 0)
        )
        
        news_adjustment = (news['news_score'] - 50) * 0.3
        sector_adjustment = (sector['sector_score'] - 50) * 0.3
        gpt_score = gpt.get('overall_score', 50)
        gpt_adjustment = (gpt_score - 50) * 0.6
        
        print(f"   Fundamentals: {fundamental_score:.0f}/70 points")
        print(f"     • Revenue Growth: {revenue_growth:.0f}% → {min(30, revenue_growth / 2):.0f}/30 pts")
        print(f"     • Analyst Upside: {analyst_upside:+.0f}% → {min(25, analyst_upside / 2):.0f}/25 pts")
        print(f"     • Profitability: {profit_margin:.1f}% margin → {15 if profit_margin > 10 else 10 if profit_margin > 0 else 5 if fund['operating_margin'] > 0 else 0}/15 pts")
        
        print(f"   News Impact: {news_adjustment:+.1f} pts ({news['sentiment']} sentiment, score: {news['news_score']}/100)")
        print(f"   Sector Boost: {sector_adjustment:+.1f} pts ({sector['growth_outlook']} outlook, score: {sector['sector_score']}/100)")
        print(f"   GPT Enhancement: {gpt_adjustment:+.1f} pts (GPT score: {gpt_score}/100)")
        
        # Show risk penalties if applicable
        penalties = []
        short_percent = fund.get('short_percent_float', 0)
        institutional_percent = fund.get('institutional_percent', 0) * 100
        volatility = fund.get('volatility_annual', 0)
        volatility_trend = fund.get('volatility_trend', 0)
        momentum_score = fund.get('momentum_score', 0)
        
        if short_percent > 10:
            penalties.append(f"High short interest: {short_percent:.1f}%")
        if institutional_percent > 80:
            penalties.append(f"Over-owned: {institutional_percent:.0f}% institutional")
        if volatility > 80:
            penalties.append(f"High volatility: {volatility:.0f}%")
        if volatility_trend > 50:
            penalties.append(f"Rising volatility: +{volatility_trend:.0f}%")
        if momentum_score < -20:
            penalties.append(f"Negative momentum: {momentum_score:.1f}")
        if profit_margin < 0:
            penalties.append(f"Unprofitable: {profit_margin:.1f}% margin")
            
        if penalties:
            print(f"   Risk Penalties: {', '.join(penalties)}")
        
        # Show bonuses
        bonuses = []
        if institutional_percent < 20:
            bonuses.append(f"Under-discovered: {institutional_percent:.0f}% institutional")
        if short_percent < 2:
            bonuses.append(f"Low short interest: {short_percent:.1f}%")
        if momentum_score > 20:
            bonuses.append(f"Strong momentum: +{momentum_score:.1f}")
        if volatility < 20:
            bonuses.append(f"Low volatility: {volatility:.0f}%")
        if volatility_trend < -30:
            bonuses.append(f"Stabilizing volatility: {volatility_trend:.0f}%")
            
        if bonuses:
            print(f"   Opportunity Bonuses: {', '.join(bonuses)}")
        
        print(f"   TOTAL SYSTEMATIC SCORE: {score}/100")
        
        # Key catalysts
        catalysts = gpt.get('catalyst_timeline', [])
        if catalysts:
            print(f"\n🚀 KEY CATALYSTS:")
            for catalyst in catalysts[:3]:
                print(f"   • {catalyst.get('event', 'N/A')} ({catalyst.get('timeline', 'TBD')}) - {catalyst.get('price_impact', 'N/A')} impact")
        
        # Risk factors
        risks = gpt.get('risk_factors', [])
        if risks:
            print(f"\n⚠️  KEY RISKS:")
            for risk in risks[:3]:
                print(f"   • {risk.get('risk', 'N/A')} ({risk.get('probability', 0)}% probability) - {risk.get('impact', 'N/A')} impact")
        
        # IV Analysis Results
        iv_analysis = analysis.get('iv_analysis', {})
        if iv_analysis and 'error' not in iv_analysis:
            print(f"\n📈 IMPLIED VOLATILITY ANALYSIS:")
            print(f"   Current IV: {iv_analysis.get('current_iv', 0):.1%}")
            print(f"   IV Percentile: {iv_analysis.get('iv_percentile', 50):.0f}th (Historical comparison)")
            print(f"   IV Rank: {iv_analysis.get('iv_rank', 50):.0f}/100")
            print(f"   Historical Median IV: {iv_analysis.get('historical_median_iv', 0):.1%}")
            
            iv_skew = iv_analysis.get('iv_skew', {})
            if iv_skew:
                print(f"   IV Skew: {iv_skew.get('skew_type', 'unknown').replace('_', ' ').title()}")
                if iv_skew.get('arbitrage_potential'):
                    print(f"   💰 ARBITRAGE POTENTIAL: Significant skew detected!")
                    print(f"      Low Strike IV: {iv_skew.get('low_strike_iv', 0):.1%}")
                    print(f"      High Strike IV: {iv_skew.get('high_strike_iv', 0):.1%}")
            
            signal = iv_analysis.get('signal', '')
            if signal:
                print(f"   📊 Signal: {signal}")
        
        # Cross-Strike Arbitrage (ZETA-style - most important!)
        cross_strike_arb = analysis.get('cross_strike_arbitrage', [])
        if cross_strike_arb:
            print(f"\n💰 CROSS-STRIKE ARBITRAGE OPPORTUNITIES (ZETA-Style):")
            print("   (Lower strike + premium costs LESS than higher strike + premium)")
            for i, arb in enumerate(cross_strike_arb[:3], 1):
                print(f"\n   {i}. 🔥 ACTIONABLE ARBITRAGE - {arb['expiry']} ({arb['days_out']} days) [{arb['moneyness_region']}]")
                print(f"      ✅ BETTER:  ${arb['better_strike']:.2f} strike + ${arb['better_premium']:.2f} premium = ${arb['better_total_cost']:.2f} total")
                print(f"      ❌ WORSE:   ${arb['worse_strike']:.2f} strike + ${arb['worse_premium']:.2f} premium = ${arb['worse_total_cost']:.2f} total")
                print(f"      💵 SAVINGS: ${arb['savings_per_contract']:.2f} per contract ({arb['savings_pct']:.1f}% cheaper)")
                print(f"      📝 Strategy: Buy ${arb['better_strike']:.2f} strike instead of ${arb['worse_strike']:.2f}")
                print(f"      ⚠️  Note: Both strikes are {arb['moneyness_region']} - similar risk profile, better value!")
        
        # Multi-Expiry Spread Opportunities
        spreads = analysis.get('spread_opportunities', [])
        if spreads:
            print(f"\n🔄 MULTI-EXPIRY SPREAD OPPORTUNITIES:")
            print("   (Calendar/Diagonal spreads for advanced strategies)")
            for i, spread in enumerate(spreads[:3], 1):
                print(f"\n   {i}. ${spread['strike']:.2f} Strike:")
                print(f"      {spread['recommendation']}")
                print(f"      Shorter: {spread['shorter_expiry']} @ ${spread['shorter_price']:.2f} ({spread['shorter_days']} days)")
                print(f"      Longer:  {spread['longer_expiry']} @ ${spread['longer_price']:.2f} ({spread['longer_days']} days)")
                print(f"      Time Difference: {spread['time_difference_days']} days")
                print(f"      Price Difference: ${spread['price_difference']:.2f} (Decay: ${spread['decay_rate_per_day']:.4f}/day)")
                print(f"      Efficiency Ratio: {spread['efficiency_ratio']:.1%}")
                if spread.get('is_arbitrage'):
                    print(f"      🔥 TRUE ARBITRAGE: Longer expiry significantly cheaper!")
                print(f"      Total Cost Comparison: ${spread['total_cost_shorter']:.2f} vs ${spread['total_cost_longer']:.2f}")
        
        print("="*120)


    def create_batch_summary(self, analyses: list) -> None:
        """Create a tabulated summary for batch analysis triage."""
        if not analyses:
            return
        
        print(f"\n" + "="*140)
        print("🎯 BATCH ANALYSIS SUMMARY - LEAPS TRIAGE RANKING")
        print("="*140)
        
        # Prepare summary data
        summary_data = []
        for analysis in analyses:
            if not analysis:
                continue
                
            symbol = analysis['symbol']
            score = analysis['final_score']
            fund = analysis['fundamentals']
            leaps_strat = analysis['gpt_analysis'].get('leaps_strategy', {})
            option_data = analysis.get('option_data', {})
            
            # Determine verdict emoji
            if score >= 75:
                verdict = "🚀 STRONG BUY"
            elif score >= 60:
                verdict = "🟢 BUY"
            elif score >= 45:
                verdict = "🟡 CONSIDER"
            else:
                verdict = "🔴 AVOID"
            
            # Get key metrics
            current_price = fund['current_price']
            target_24m = analysis['gpt_analysis'].get('price_prediction', {}).get('24_month_target', current_price)
            expected_return = ((target_24m - current_price) / current_price * 100) if current_price > 0 else 0
            
            # LEAPS info
            strike = leaps_strat.get('optimal_strike', 0)
            expiry = leaps_strat.get('expiry_date', 'N/A')
            contract_cost = leaps_strat.get('contract_cost', 500)
            
            # Liquidity status
            if option_data.get('leaps_exists'):
                liquidity = f"{option_data.get('liquid_contracts', 0)} liquid"
            else:
                liquidity = "No LEAPS"
            
            summary_data.append([
                symbol,
                score,
                verdict,
                f"${current_price:.2f}",
                f"{expected_return:+.0f}%",
                f"${strike:.2f}",
                expiry[:7] if len(expiry) > 7 else expiry,  # Show YYYY-MM
                f"${contract_cost:.0f}",
                liquidity
            ])
        
        # Sort by score descending
        summary_data.sort(key=lambda x: x[1], reverse=True)
        
        # Create table
        headers = [
            "Ticker", "Score", "Verdict", "Price", "24M Return", 
            "Strike", "Expiry", "Cost", "Liquidity"
        ]
        
        print(tabulate(summary_data, headers=headers, tablefmt="grid", stralign="center"))
        
        # Top picks summary
        top_picks = [row for row in summary_data if row[1] >= 60][:3]
        if top_picks:
            print(f"\n🏆 TOP LEAPS PICKS:")
            for i, pick in enumerate(top_picks, 1):
                symbol, score, verdict, price, ret, strike, expiry, cost, liq = pick
                print(f"   {i}. {symbol} - {verdict} (Score: {score}) - {ret} expected return")
                print(f"      → {strike} strike @ {expiry} for ~{cost} ({liq})")
        
        print("="*140)


class ImpliedVolatilityAnalyzer:
    """Advanced IV analysis for LEAPS options."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        
    def get_historical_iv_data(self, lookback_days: int = 365) -> pd.DataFrame:
        """Get historical IV data from options chain history."""
        try:
            # Get historical options data (approximated from historical volatility)
            hist = self.ticker.history(period=f'{lookback_days}d')
            if hist.empty:
                return pd.DataFrame()
            
            # Calculate historical volatility as proxy for IV
            returns = np.log(hist['Close'] / hist['Close'].shift(1))
            hist['HV_30d'] = returns.rolling(window=30).std() * np.sqrt(252)
            hist['HV_60d'] = returns.rolling(window=60).std() * np.sqrt(252)
            hist['HV_90d'] = returns.rolling(window=90).std() * np.sqrt(252)
            
            return hist[['HV_30d', 'HV_60d', 'HV_90d']].dropna()
        except Exception as e:
            print(f"⚠️ Error getting historical IV: {e}")
            return pd.DataFrame()
    
    def analyze_current_iv(self) -> Dict:
        """Analyze current IV across all strikes and expiries."""
        try:
            # Get current options data
            expirations = self.ticker.options
            if not expirations:
                return {'error': 'No options data available'}
            
            all_ivs = []
            strike_iv_map = defaultdict(list)
            
            for exp in expirations[:6]:  # Analyze first 6 expiries
                try:
                    chain = self.ticker.option_chain(exp)
                    calls = chain.calls
                    
                    for _, row in calls.iterrows():
                        if 'impliedVolatility' in row and row['impliedVolatility'] > 0:
                            iv = row['impliedVolatility']
                            strike = row['strike']
                            all_ivs.append(iv)
                            strike_iv_map[strike].append(iv)
                except:
                    continue
            
            if not all_ivs:
                return {'error': 'No IV data available'}
            
            # Calculate IV metrics
            current_iv = np.median(all_ivs)
            iv_range = (np.min(all_ivs), np.max(all_ivs))
            
            # Get historical IV for comparison
            hist_iv = self.get_historical_iv_data()
            if not hist_iv.empty:
                hist_median = hist_iv['HV_30d'].median()
                iv_percentile = (sum(hist_iv['HV_30d'] < current_iv) / len(hist_iv)) * 100
                iv_rank = iv_percentile  # IV Rank approximation
            else:
                hist_median = current_iv
                iv_percentile = 50
                iv_rank = 50
            
            # Detect IV skew
            iv_skew = self.analyze_iv_skew(strike_iv_map)
            
            return {
                'current_iv': current_iv,
                'iv_range': iv_range,
                'iv_percentile': iv_percentile,
                'iv_rank': iv_rank,
                'historical_median_iv': hist_median,
                'iv_skew': iv_skew,
                'signal': self.get_iv_signal(iv_percentile, iv_skew)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_iv_skew(self, strike_iv_map: Dict) -> Dict:
        """Analyze IV skew across strikes."""
        if not strike_iv_map:
            return {'skew_type': 'unknown', 'skew_strength': 0}
        
        strikes = sorted(strike_iv_map.keys())
        if len(strikes) < 3:
            return {'skew_type': 'insufficient_data', 'skew_strength': 0}
        
        # Get IVs for low, mid, high strikes
        low_strikes = strikes[:len(strikes)//3]
        high_strikes = strikes[-len(strikes)//3:]
        
        low_iv = np.mean([np.mean(strike_iv_map[s]) for s in low_strikes])
        high_iv = np.mean([np.mean(strike_iv_map[s]) for s in high_strikes])
        
        skew = high_iv - low_iv
        
        if abs(skew) < 0.02:
            skew_type = 'flat'
        elif skew > 0:
            skew_type = 'positive_skew'  # Higher strikes have higher IV (bearish)
        else:
            skew_type = 'negative_skew'  # Lower strikes have higher IV (bullish)
        
        return {
            'skew_type': skew_type,
            'skew_strength': abs(skew),
            'low_strike_iv': low_iv,
            'high_strike_iv': high_iv,
            'arbitrage_potential': abs(skew) > 0.05  # Significant skew = arbitrage opportunity
        }
    
    def get_iv_signal(self, iv_percentile: float, iv_skew: Dict) -> str:
        """Generate trading signal based on IV analysis."""
        signals = []
        
        if iv_percentile < 20:
            signals.append("🟢 STRONG_BUY - IV at historical lows")
        elif iv_percentile < 40:
            signals.append("🟢 BUY - IV below average")
        elif iv_percentile > 80:
            signals.append("🔴 AVOID - IV at historical highs")
        elif iv_percentile > 60:
            signals.append("🟡 WAIT - IV above average")
        else:
            signals.append("🟡 NEUTRAL - IV at average levels")
        
        if iv_skew.get('arbitrage_potential'):
            signals.append(f"💰 ARBITRAGE - Significant {iv_skew['skew_type']}")
        
        return " | ".join(signals)


class MultiExpiryAnalyzer:
    """Analyze options across multiple expiries for spread opportunities."""
    
    def __init__(self, symbol: str, current_price: float):
        self.symbol = symbol
        self.current_price = current_price
        self.ticker = yf.Ticker(symbol)
    
    def find_cross_strike_arbitrage(self) -> List[Dict]:
        """Find cross-strike arbitrage opportunities (like ZETA $18 vs $19 example)."""
        arbitrage_opportunities = []
        
        try:
            expirations = self.ticker.options
            if not expirations:
                return arbitrage_opportunities
            
            # Focus on LEAPS expiries (12+ months out)
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_out = (exp_date - datetime.now()).days
                if days_out < 365:
                    continue
                
                try:
                    chain = self.ticker.option_chain(exp).calls
                    if chain.empty:
                        continue
                    
                    # Sort by strike
                    chain = chain.sort_values('strike')
                    
                    # Compare each strike with nearby strikes
                    for i, row in chain.iterrows():
                        strike1 = row['strike']
                        price1 = (row['bid'] + row['ask']) / 2
                        
                        if price1 <= 0:
                            continue
                        
                        # Calculate moneyness for strike1
                        moneyness1 = (self.current_price - strike1) / self.current_price
                        
                        total_cost1 = strike1 + price1
                        
                        # Compare with higher strikes ONLY if they have similar moneyness
                        for j, other_row in chain[chain['strike'] > strike1].iterrows():
                            strike2 = other_row['strike']
                            price2 = (other_row['bid'] + other_row['ask']) / 2
                            
                            if price2 <= 0:
                                continue
                            
                            # Calculate moneyness for strike2
                            moneyness2 = (self.current_price - strike2) / self.current_price
                            
                            # Only compare strikes that are:
                            # 1. Within $3 of each other (nearby strikes)
                            # 2. Have similar moneyness (both ITM, both ATM, or both OTM)
                            strike_diff = strike2 - strike1
                            if strike_diff > 3:
                                break
                            
                            # Check if both are in same moneyness region
                            # ITM: moneyness > 0.05, ATM: -0.05 to 0.05, OTM: < -0.05
                            both_itm = moneyness1 > 0.05 and moneyness2 > 0.05
                            both_atm = abs(moneyness1) <= 0.10 and abs(moneyness2) <= 0.10
                            both_otm = moneyness1 < -0.05 and moneyness2 < -0.05
                            
                            # Only compare if in same moneyness region
                            if not (both_itm or both_atm or both_otm):
                                continue
                            
                            total_cost2 = strike2 + price2
                            
                            # ZETA-style arbitrage: Lower strike + premium < Higher strike + premium
                            # This should be RARE - normally lower strike costs MORE total
                            if total_cost1 < total_cost2:
                                savings = total_cost2 - total_cost1
                                
                                # Stricter criteria for true arbitrage:
                                # 1. Savings >= $0.50 per share ($50 per contract)
                                # 2. Savings >= 2% of total cost (not just 1%)
                                # 3. Strike difference <= $2 (very nearby)
                                if (savings >= 0.50 and 
                                    (savings / total_cost2) >= 0.02 and
                                    strike_diff <= 2.5):
                                    
                                    arbitrage_opportunities.append({
                                        'expiry': exp,
                                        'days_out': days_out,
                                        'better_strike': strike1,
                                        'better_premium': price1,
                                        'better_total_cost': total_cost1,
                                        'worse_strike': strike2,
                                        'worse_premium': price2,
                                        'worse_total_cost': total_cost2,
                                        'savings_per_share': savings,
                                        'savings_per_contract': savings * 100,
                                        'savings_pct': (savings / total_cost2) * 100,
                                        'moneyness_region': 'ITM' if both_itm else 'ATM' if both_atm else 'OTM',
                                        'type': 'cross_strike_arbitrage',
                                        'description': f"${strike1:.2f} strike + ${price1:.2f} premium = ${total_cost1:.2f} vs ${strike2:.2f} strike + ${price2:.2f} premium = ${total_cost2:.2f}"
                                    })
                except:
                    continue
            
            # Sort by savings
            arbitrage_opportunities.sort(key=lambda x: x['savings_per_contract'], reverse=True)
            
        except Exception as e:
            print(f"⚠️ Error finding cross-strike arbitrage: {e}")
        
        return arbitrage_opportunities[:5]  # Top 5
    
    def find_diagonal_spread_opportunities(self) -> List[Dict]:
        """Find diagonal spread opportunities (same strike, different expiries)."""
        opportunities = []
        
        try:
            expirations = self.ticker.options
            if len(expirations) < 2:
                return opportunities
            
            # Focus on LEAPS expiries (12+ months out)
            leaps_expiries = []
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_out = (exp_date - datetime.now()).days
                if days_out >= 365:
                    leaps_expiries.append((exp, days_out))
            
            if len(leaps_expiries) < 2:
                return opportunities
            
            # Sort by days to expiry
            leaps_expiries.sort(key=lambda x: x[1])
            
            # Compare consecutive expiries
            for i in range(len(leaps_expiries) - 1):
                shorter_exp, shorter_days = leaps_expiries[i]
                longer_exp, longer_days = leaps_expiries[i + 1]
                
                try:
                    shorter_chain = self.ticker.option_chain(shorter_exp).calls
                    longer_chain = self.ticker.option_chain(longer_exp).calls
                    
                    # Find same strikes in both chains
                    common_strikes = set(shorter_chain['strike']) & set(longer_chain['strike'])
                    
                    for strike in common_strikes:
                        shorter_opt = shorter_chain[shorter_chain['strike'] == strike].iloc[0]
                        longer_opt = longer_chain[longer_chain['strike'] == strike].iloc[0]
                        
                        # Calculate metrics
                        shorter_price = (shorter_opt['bid'] + shorter_opt['ask']) / 2
                        longer_price = (longer_opt['bid'] + longer_opt['ask']) / 2
                        
                        if shorter_price <= 0 or longer_price <= 0:
                            continue
                        
                        # Time decay rate (premium per day)
                        time_diff_days = longer_days - shorter_days
                        price_diff = longer_price - shorter_price
                        decay_rate = price_diff / time_diff_days if time_diff_days > 0 else 0
                        
                        # Efficiency ratio (how much more premium per extra day)
                        efficiency = price_diff / longer_price if longer_price > 0 else 0
                        
                        # Enhanced arbitrage detection with stricter criteria
                        savings = shorter_price - longer_price  # How much cheaper is longer expiry
                        
                        # Only flag as arbitrage if:
                        # 1. Longer expiry is actually cheaper (savings > 0)
                        # 2. Time difference is meaningful (90+ days)
                        # 3. Savings is significant (>$0.50 per share or >5% of shorter price)
                        # 4. Not just market noise
                        is_arbitrage = (
                            longer_price < shorter_price and
                            time_diff_days >= 90 and  # At least 3 months difference
                            savings >= 0.50 and  # At least $50 per contract savings
                            (savings / shorter_price) >= 0.05  # At least 5% savings
                        )
                        
                        opportunities.append({
                            'strike': strike,
                            'shorter_expiry': shorter_exp,
                            'longer_expiry': longer_exp,
                            'shorter_price': shorter_price,
                            'longer_price': longer_price,
                            'shorter_days': shorter_days,
                            'longer_days': longer_days,
                            'time_difference_days': time_diff_days,
                            'price_difference': price_diff,
                            'decay_rate_per_day': decay_rate,
                            'efficiency_ratio': efficiency,
                            'is_arbitrage': is_arbitrage,
                            'total_cost_shorter': strike + shorter_price,
                            'total_cost_longer': strike + longer_price,
                            'recommendation': self.get_spread_recommendation(
                                is_arbitrage, efficiency, decay_rate, strike, self.current_price
                            )
                        })
                except:
                    continue
            
            # Sort by efficiency and filter for best opportunities
            opportunities.sort(key=lambda x: (x['is_arbitrage'], x['efficiency_ratio']), reverse=True)
            
        except Exception as e:
            print(f"⚠️ Error finding diagonal spreads: {e}")
        
        return opportunities[:5]  # Top 5 opportunities
    
    def get_spread_recommendation(self, is_arbitrage: bool, efficiency: float, 
                                  decay_rate: float, strike: float, current_price: float) -> str:
        """Generate recommendation for spread opportunity."""
        # True actionable arbitrage (rare and valuable)
        if is_arbitrage:
            return "🔥 STRONG_ARBITRAGE - Longer expiry significantly cheaper! ACTIONABLE"
        
        # Weak arbitrage (longer cheaper but not actionable due to spreads/time)
        if efficiency < 0 and abs(efficiency) < 0.1:
            return "🟡 WEAK_ARBITRAGE - Longer slightly cheaper (likely market noise)"
        
        # Normal positive efficiency spreads
        if efficiency > 0.3 and decay_rate > 0.02:
            return "🟢 EXCELLENT - High efficiency, good diagonal spread candidate"
        elif efficiency > 0.2:
            return "🟢 GOOD - Above average efficiency for calendar spreads"
        elif efficiency > 0.1:
            return "🟡 FAIR - Average efficiency"
        elif efficiency > 0:
            return "🟡 MARGINAL - Low efficiency, not recommended"
        else:
            return "⚠️ INVERTED - Longer cheaper (check spreads before acting)"
    
    def analyze_calendar_spread_value(self, target_strike: float = None) -> Dict:
        """Analyze calendar spread value for a specific strike."""
        if target_strike is None:
            target_strike = round(self.current_price * 1.1 / 5) * 5  # Slightly OTM, rounded to $5
        
        spreads = self.find_diagonal_spread_opportunities()
        target_spreads = [s for s in spreads if abs(s['strike'] - target_strike) < 2.5]
        
        if not target_spreads:
            return {'error': f'No data for strike ${target_strike}'}
        
        best_spread = target_spreads[0]
        
        return {
            'target_strike': target_strike,
            'best_spread': best_spread,
            'strategy': f"Buy {best_spread['longer_expiry']} @ ${best_spread['longer_price']:.2f}, "
                       f"Sell {best_spread['shorter_expiry']} @ ${best_spread['shorter_price']:.2f}",
            'net_cost': best_spread['price_difference'] * 100,  # Per contract
            'days_held': best_spread['time_difference_days'],
            'daily_theta_capture': best_spread['decay_rate_per_day']
        }


class PortfolioAnalyzer:
    """Portfolio-level LEAPS analysis and optimization."""
    
    def __init__(self):
        self.positions = []
    
    def add_position(self, symbol: str, strike: float, expiry: str, 
                    quantity: int, entry_price: float, current_price: float, delta: float = None):
        """Add a LEAPS position to the portfolio."""
        self.positions.append({
            'symbol': symbol,
            'strike': strike,
            'expiry': expiry,
            'quantity': quantity,
            'entry_price': entry_price,
            'current_price': current_price,
            'delta': delta or 0.6,  # Default delta for ITM LEAPS
            'market_value': quantity * current_price * 100,
            'cost_basis': quantity * entry_price * 100,
            'unrealized_pnl': quantity * (current_price - entry_price) * 100
        })
    
    def calculate_portfolio_greeks(self) -> Dict:
        """Calculate aggregate portfolio Greeks."""
        total_delta = sum(p['delta'] * p['quantity'] for p in self.positions)
        total_market_value = sum(p['market_value'] for p in self.positions)
        
        return {
            'total_delta': total_delta,
            'total_market_value': total_market_value,
            'delta_adjusted_exposure': total_delta * total_market_value,
            'equivalent_shares': int(total_delta * 100),  # How many shares this represents
        }
    
    def analyze_correlation(self) -> Dict:
        """Analyze correlation between portfolio holdings."""
        if len(self.positions) < 2:
            return {'message': 'Need at least 2 positions for correlation analysis'}
        
        symbols = list(set(p['symbol'] for p in self.positions))
        
        try:
            # Get historical price data
            data = yf.download(symbols, period='6mo', progress=False)['Close']
            
            if isinstance(data, pd.Series):
                return {'message': 'Only one symbol in portfolio'}
            
            # Calculate correlation matrix
            corr_matrix = data.corr()
            
            # Find highest correlations
            correlations = []
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    corr = corr_matrix.iloc[i, j]
                    correlations.append({
                        'symbol1': symbols[i],
                        'symbol2': symbols[j],
                        'correlation': corr,
                        'diversification_benefit': 1 - abs(corr)
                    })
            
            correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            avg_correlation = np.mean([abs(c['correlation']) for c in correlations])
            
            return {
                'average_correlation': avg_correlation,
                'top_correlations': correlations[:5],
                'diversification_score': (1 - avg_correlation) * 100,
                'warning': 'High correlation detected' if avg_correlation > 0.7 else None
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary."""
        total_cost = sum(p['cost_basis'] for p in self.positions)
        total_value = sum(p['market_value'] for p in self.positions)
        total_pnl = sum(p['unrealized_pnl'] for p in self.positions)
        
        greeks = self.calculate_portfolio_greeks()
        correlation = self.analyze_correlation()
        
        return {
            'num_positions': len(self.positions),
            'unique_symbols': len(set(p['symbol'] for p in self.positions)),
            'total_cost_basis': total_cost,
            'total_market_value': total_value,
            'total_unrealized_pnl': total_pnl,
            'return_pct': (total_pnl / total_cost * 100) if total_cost > 0 else 0,
            'portfolio_greeks': greeks,
            'correlation_analysis': correlation,
            'positions': self.positions
        }


def main():
    parser = argparse.ArgumentParser(description='Complete Systematic LEAPS Analysis')
    parser.add_argument('ticker', nargs='?', help='Ticker to analyze')
    parser.add_argument('--batch', nargs='*', help='Analyze multiple tickers')
    parser.add_argument('--no-gpt', action='store_true', help='Use systematic model only')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--force-ibkr', action='store_true', help='Force IBKR integration even when market is closed')
    parser.add_argument('--no-finbert', action='store_true', help='Disable FinBERT professional sentiment analysis')
    args = parser.parse_args()
    
    system = CompleteLEAPSSystem(
        use_gpt=not args.no_gpt, 
        try_ibkr=args.force_ibkr or True,
        use_finbert=not args.no_finbert
    )
    
    try:
        if args.batch is not None:
            # Batch analysis with summary
            tickers = [t.upper() for t in args.batch] if args.batch else []
            all_analyses = []
            
            for ticker in tickers:
                analysis = system.complete_systematic_analysis(ticker)
                all_analyses.append(analysis)
                
                if not args.json:
                    system.display_complete_analysis(analysis)
            
            # Create batch summary for triage
            if not args.json and len(all_analyses) > 1:
                system.create_batch_summary(all_analyses)
            
            # JSON output option
            if args.json:
                import json
                json_output = []
                for analysis in all_analyses:
                    if analysis:
                        # Clean up for JSON serialization
                        clean_analysis = {}
                        for key, value in analysis.items():
                            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                                clean_analysis[key] = value
                            elif hasattr(value, 'item'):  # numpy types
                                clean_analysis[key] = value.item()
                            else:
                                clean_analysis[key] = str(value)
                        json_output.append(clean_analysis)
                
                print(json.dumps(json_output, indent=2, default=str))
        
        elif args.ticker:
            # Single ticker analysis
            analysis = system.complete_systematic_analysis(args.ticker.upper())
            
            if args.json:
                import json
                # Clean for JSON
                clean_analysis = {}
                for key, value in analysis.items():
                    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                        clean_analysis[key] = value
                    elif hasattr(value, 'item'):  # numpy types
                        clean_analysis[key] = value.item()
                    else:
                        clean_analysis[key] = str(value)
                print(json.dumps(clean_analysis, indent=2, default=str))
            else:
                system.display_complete_analysis(analysis)
        
        else:
            print("🎯 ENHANCED SYSTEMATIC LEAPS ANALYSIS")
            print("Usage:")
            print("  python complete_leaps_system.py TICKER           # Complete analysis")
            print("  python complete_leaps_system.py --batch T1 T2    # Multiple tickers with summary")
            print("  python complete_leaps_system.py --no-gpt TICKER  # Systematic model only")
            print("  python complete_leaps_system.py --json TICKER    # JSON output")
            print()
            print("💡 NEW FEATURES:")
            print("   • Real option chain analysis with liquidity filters")
            print("   • Dynamic LEAPS expiry calculation")
            print("   • Enhanced scoring with short interest & institutional ownership")
            print("   • ~$500 contract cost targeting")
            print("   • Batch triage summary with rankings")
    
    except KeyboardInterrupt:
        print("\n⏹️ Analysis interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
