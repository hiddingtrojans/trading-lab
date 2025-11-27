#!/usr/bin/env python3
"""
Enhanced Feature Engineering with Fundamentals
===============================================

Adds fundamental, event-driven, and sector features.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')


class FundamentalEngineer:
    """Engineer fundamental features from yfinance."""
    
    @staticmethod
    def get_fundamentals(symbol: str) -> Dict:
        """
        Extract fundamental data for a symbol.
        
        Returns dict with all available fundamental metrics.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            fundamentals = {
                # Valuation
                'pe_ratio': info.get('forwardPE', np.nan),
                'trailing_pe': info.get('trailingPE', np.nan),
                'peg_ratio': info.get('pegRatio', np.nan),
                'pb_ratio': info.get('priceToBook', np.nan),
                'ps_ratio': info.get('priceToSalesTrailing12Months', np.nan),
                'ev_to_revenue': info.get('enterpriseToRevenue', np.nan),
                'ev_to_ebitda': info.get('enterpriseToEbitda', np.nan),
                
                # Profitability
                'profit_margin': info.get('profitMargins', np.nan),
                'operating_margin': info.get('operatingMargins', np.nan),
                'gross_margin': info.get('grossMargins', np.nan),
                'ebitda_margin': info.get('ebitdaMargins', np.nan),
                'roe': info.get('returnOnEquity', np.nan),
                'roa': info.get('returnOnAssets', np.nan),
                
                # Growth
                'revenue_growth': info.get('revenueGrowth', np.nan),
                'earnings_growth': info.get('earningsGrowth', np.nan),
                'revenue_per_share': info.get('revenuePerShare', np.nan),
                'earnings_per_share': info.get('trailingEps', np.nan),
                
                # Financial Health
                'current_ratio': info.get('currentRatio', np.nan),
                'quick_ratio': info.get('quickRatio', np.nan),
                'debt_to_equity': info.get('debtToEquity', np.nan),
                'total_cash': info.get('totalCash', np.nan),
                'total_debt': info.get('totalDebt', np.nan),
                'free_cash_flow': info.get('freeCashflow', np.nan),
                'operating_cash_flow': info.get('operatingCashflow', np.nan),
                
                # Ownership & Trading
                'insider_holding': info.get('heldPercentInsiders', np.nan),
                'institutional_holding': info.get('heldPercentInstitutions', np.nan),
                'short_ratio': info.get('shortRatio', np.nan),
                'short_percent': info.get('shortPercentOfFloat', np.nan),
                
                # Analyst Sentiment
                'analyst_rating': info.get('recommendationMean', np.nan),
                'num_analyst_opinions': info.get('numberOfAnalystOpinions', np.nan),
                'target_price': info.get('targetMeanPrice', np.nan),
                
                # Size & Sector
                'market_cap': info.get('marketCap', np.nan),
                'enterprise_value': info.get('enterpriseValue', np.nan),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
            }
            
            # Calculate derived metrics
            current_price = info.get('currentPrice', info.get('regularMarketPrice', np.nan))
            if not np.isnan(current_price) and not np.isnan(fundamentals['target_price']):
                fundamentals['price_to_target'] = current_price / fundamentals['target_price']
            else:
                fundamentals['price_to_target'] = np.nan
            
            # Cash flow quality
            if not np.isnan(fundamentals['free_cash_flow']) and not np.isnan(fundamentals['market_cap']):
                fundamentals['fcf_yield'] = fundamentals['free_cash_flow'] / fundamentals['market_cap']
            else:
                fundamentals['fcf_yield'] = np.nan
            
            return fundamentals
            
        except Exception as e:
            # Return all NaNs if data unavailable
            return {k: np.nan for k in [
                'pe_ratio', 'trailing_pe', 'peg_ratio', 'pb_ratio', 'ps_ratio',
                'ev_to_revenue', 'ev_to_ebitda', 'profit_margin', 'operating_margin',
                'gross_margin', 'ebitda_margin', 'roe', 'roa', 'revenue_growth',
                'earnings_growth', 'revenue_per_share', 'earnings_per_share',
                'current_ratio', 'quick_ratio', 'debt_to_equity', 'total_cash',
                'total_debt', 'free_cash_flow', 'operating_cash_flow',
                'insider_holding', 'institutional_holding', 'short_ratio',
                'short_percent', 'analyst_rating', 'num_analyst_opinions',
                'target_price', 'market_cap', 'enterprise_value', 'price_to_target',
                'fcf_yield'
            ]} | {'sector': 'Unknown', 'industry': 'Unknown'}
    
    @staticmethod
    def get_earnings_events(symbol: str) -> Dict:
        """Get earnings-related event features."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Earnings calendar
            calendar = ticker.calendar
            
            features = {}
            
            if calendar is not None and not calendar.empty:
                # Next earnings date
                if 'Earnings Date' in calendar.index:
                    next_earnings = pd.to_datetime(calendar.loc['Earnings Date'].iloc[0])
                    days_to_earnings = (next_earnings - datetime.now()).days
                    features['days_to_earnings'] = days_to_earnings
                    features['earnings_within_30d'] = 1 if 0 < days_to_earnings < 30 else 0
                else:
                    features['days_to_earnings'] = np.nan
                    features['earnings_within_30d'] = 0
            else:
                features['days_to_earnings'] = np.nan
                features['earnings_within_30d'] = 0
            
            # Recent earnings surprises
            earnings_history = ticker.earnings_history
            if earnings_history is not None and not earnings_history.empty and len(earnings_history) > 0:
                # Most recent surprise
                recent = earnings_history.iloc[0]
                features['last_earnings_surprise'] = recent.get('Surprise(%)', np.nan)
                
                # Average surprise over last 4 quarters
                if len(earnings_history) >= 4:
                    features['avg_surprise_4q'] = earnings_history.iloc[:4]['Surprise(%)'].mean()
                else:
                    features['avg_surprise_4q'] = np.nan
            else:
                features['last_earnings_surprise'] = np.nan
                features['avg_surprise_4q'] = np.nan
            
            return features
            
        except Exception as e:
            return {
                'days_to_earnings': np.nan,
                'earnings_within_30d': 0,
                'last_earnings_surprise': np.nan,
                'avg_surprise_4q': np.nan
            }
    
    @staticmethod
    def get_sector_relative_features(symbol: str, sector: str) -> Dict:
        """Calculate features relative to sector."""
        try:
            sector_etfs = {
                'Technology': 'XLK',
                'Financial Services': 'XLF',
                'Healthcare': 'XLV',
                'Energy': 'XLE',
                'Industrials': 'XLI',
                'Consumer Cyclical': 'XLY',
                'Consumer Defensive': 'XLP',
                'Utilities': 'XLU',
                'Real Estate': 'XLRE',
                'Basic Materials': 'XLB',
                'Communication Services': 'XLC'
            }
            
            sector_etf = sector_etfs.get(sector, 'SPY')
            
            # Download recent data
            stock_data = yf.download(symbol, period='60d', progress=False)
            sector_data = yf.download(sector_etf, period='60d', progress=False)
            
            if stock_data.empty or sector_data.empty:
                return {'sector_momentum': np.nan, 'vs_sector': np.nan, 'sector_correlation': np.nan}
            
            stock_returns = stock_data['Close'].pct_change()
            sector_returns = sector_data['Close'].pct_change()
            
            # Sector momentum
            sector_20d = sector_returns.tail(20).sum()
            
            # Stock performance vs sector
            stock_20d = stock_returns.tail(20).sum()
            relative_perf = stock_20d - sector_20d
            
            # Correlation with sector
            correlation = stock_returns.tail(60).corr(sector_returns.tail(60))
            
            return {
                'sector_momentum': sector_20d,
                'vs_sector': relative_perf,
                'sector_correlation': correlation
            }
            
        except Exception as e:
            return {'sector_momentum': np.nan, 'vs_sector': np.nan, 'sector_correlation': np.nan}


def add_all_enhanced_features(base_features: pd.DataFrame) -> pd.DataFrame:
    """
    Add fundamental, event, and sector features to base technical features.
    
    Args:
        base_features: DataFrame with technical features, must have 'symbol' column
        
    Returns:
        Enhanced DataFrame with all features
    """
    print("\nAdding fundamental and event-driven features...")
    
    # Get unique symbols
    symbols = base_features['symbol'].unique()
    
    # Store enhanced features
    enhanced_rows = []
    
    for i, symbol in enumerate(symbols):
        if (i + 1) % 25 == 0:
            print(f"  Processing fundamentals {i+1}/{len(symbols)}...")
        
        try:
            # Get base data for this symbol
            symbol_data = base_features[base_features['symbol'] == symbol].copy()
            
            # Get fundamental features (constant across time for same symbol)
            fundamentals = FundamentalEngineer.get_fundamentals(symbol)
            earnings_events = FundamentalEngineer.get_earnings_events(symbol)
            
            sector = fundamentals.get('sector', 'Unknown')
            sector_features = FundamentalEngineer.get_sector_relative_features(symbol, sector)
            
            # Add fundamental features to each row for this symbol
            for col, val in fundamentals.items():
                if col not in ['sector', 'industry']:  # Keep as categorical
                    # Clean infinity and invalid values
                    if isinstance(val, str) or (isinstance(val, float) and np.isinf(val)):
                        val = np.nan
                    symbol_data[f'fund_{col}'] = val
            
            for col, val in earnings_events.items():
                symbol_data[f'event_{col}'] = val
            
            for col, val in sector_features.items():
                symbol_data[f'sector_{col}'] = val
            
            enhanced_rows.append(symbol_data)
            
        except Exception as e:
            print(f"  Warning: Failed to enhance {symbol}: {e}")
            enhanced_rows.append(symbol_data)
            continue
    
    enhanced_df = pd.concat(enhanced_rows, ignore_index=True)
    
    print(f"Enhanced features complete: {len(enhanced_df.columns)} total features")
    
    return enhanced_df


print("Enhanced Features Module - Loaded")
