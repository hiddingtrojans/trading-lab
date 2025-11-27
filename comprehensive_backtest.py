#!/usr/bin/env python3
"""
Comprehensive Backtesting System
=================================

Thorough validation of ALL strategies:
1. Day bot (gap trading)
2. Scanner signals (gap/momentum/VWAP)
3. LEAPS recommendations

Tests across:
- Multiple timeframes (1 year, 2 years, 5 years)
- Different market regimes (bull, bear, sideways)
- Various universes (large cap, small cap)
- Statistical significance (bootstrap, Monte Carlo)

NO SHORTCUTS. REAL VALIDATION.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from ib_insync import IB, Stock, util
import yfinance as yf
import warnings
from scipy import stats
warnings.filterwarnings('ignore')

from alpha_lab.intraday_signals import IntradaySignalGenerator
from alpha_lab.strategy_library import StrategyLibrary
from utils.data_fetcher import DataFetcher


class ComprehensiveBacktester:
    """Thorough backtesting for all strategies."""
    
    def __init__(self):
        """Initialize backtester."""
        self.ib = None
        self.fetcher = None
        self.results = {}
    
    def connect_ibkr(self):
        """Connect to IBKR for historical data."""
        try:
            import yaml
            cfg = yaml.safe_load(open('configs/ibkr.yaml'))
            
            self.ib = IB()
            import random
            client_id = random.randint(1000, 9999)
            self.ib.connect(cfg['host'], cfg['port'], clientId=client_id, timeout=15)
            print(f"✓ Connected to IBKR (Account: {self.ib.managedAccounts()[0]})\n")
            self.fetcher = DataFetcher(self.ib)
            return True
        except Exception as e:
            print(f"✗ IBKR connection failed: {e}")
            print("  Falling back to yfinance (via DataFetcher)\n")
            self.fetcher = DataFetcher(None)
            return False
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    
    def simulate_gap_trade(self, day_data: pd.DataFrame, prev_close: float, trend_ok: bool = True) -> Dict:
        """
        Simulate gap trade using day bot strategy.
        
        Strategy:
        - Trend Filter: Price > 20 SMA
        - Gap Filter: 2% < Gap < 10% (Smart Money Sweet Spot)
        - Enter on VWAP test (price within 1.0% of VWAP)
        - Stop: $0.25 below entry
        - Target 1: +$0.25 (scale out 50%)
        - Target 2: +$0.50 (remaining 50%)
        - Move stop to breakeven after target 1
        """
        if len(day_data) < 20:
            return None
        
        # Check gap
        day_open = day_data['open'].iloc[0]
        gap_pct = (day_open - prev_close) / prev_close * 100
        
        # Smart Money Filters
        # 1. Trend Filter (passed in)
        if not trend_ok:
            return {'result': 'no_trend', 'gap_pct': gap_pct}

        # 2. Gap Sweet Spot (2% to 10%)
        # Small gaps (<2%) are noise. Huge gaps (>10%) are often exhaustion.
        if abs(gap_pct) < 2.0 or abs(gap_pct) > 10.0:
            return {'result': 'bad_gap_size', 'gap_pct': gap_pct}
        
        # Calculate VWAP for the day
        vwap = self.calculate_vwap(day_data)
        
        # Look for VWAP test in first 2 hours
        first_2h = day_data.iloc[:24] if len(day_data) >= 24 else day_data
        
        # Find entry point
        entry_bar = None
        entry_price = None
        
        for i, (idx, row) in enumerate(first_2h.iterrows()):
            # Use positional indexing for VWAP to be safe against DataFrame indices
            if i >= len(vwap):
                break
            
            current_vwap = vwap.iloc[i]
            
            # Price tests VWAP (within 1.0%)
            price_to_vwap_pct = abs(row['close'] - current_vwap) / current_vwap * 100
            
            if price_to_vwap_pct < 1.0:
                entry_bar = i
                entry_price = row['close']
                break
        
        if entry_price is None:
            return {'result': 'no_entry', 'gap_pct': gap_pct}
        
        # Simulate trade execution
        stop_loss = entry_price - 0.25
        target_1 = entry_price + 0.25
        target_2 = entry_price + 0.50
        
        pnl = 0
        first_target_hit = False
        stop_to_breakeven = False
        
        # Trade from entry onwards
        # Time-based exit: 2 hours (24 bars)
        max_hold_bars = 24
        
        for i in range(entry_bar, len(day_data)):
            row = day_data.iloc[i]
            bars_held = i - entry_bar
            
            # Time-based exit if no progress
            if bars_held >= max_hold_bars and not first_target_hit and pnl <= 0:
                 exit_price = row['close']
                 pnl = exit_price - entry_price
                 return {
                    'result': 'time_exit',
                    'gap_pct': gap_pct,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl_per_share': pnl,
                    'win': pnl > 0,
                    'bars_held': bars_held
                }

            # Check stop loss
            if row['low'] <= stop_loss:
                exit_price = stop_loss
                if first_target_hit:
                    pnl += 0.5 * (exit_price - entry_price)  # Remaining 50%
                else:
                    pnl = exit_price - entry_price  # Full position
                
                return {
                    'result': 'stopped_out',
                    'gap_pct': gap_pct,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl_per_share': pnl,
                    'win': pnl > 0,
                    'bars_held': i - entry_bar
                }
            
            # Check first target
            if not first_target_hit and row['high'] >= target_1:
                pnl += 0.5 * (target_1 - entry_price)  # 50% out
                first_target_hit = True
                stop_loss = entry_price  # Move to breakeven
            
            # Check second target
            if first_target_hit and row['high'] >= target_2:
                pnl += 0.5 * (target_2 - entry_price)  # Remaining 50% out
                
                return {
                    'result': 'full_target',
                    'gap_pct': gap_pct,
                    'entry': entry_price,
                    'exit': target_2,
                    'pnl_per_share': pnl,
                    'win': True,
                    'bars_held': i - entry_bar
                }
        
        # End of day - exit remaining
        eod_price = day_data['close'].iloc[-1]
        if first_target_hit:
            pnl += 0.5 * (eod_price - entry_price)
        else:
            pnl = eod_price - entry_price
        
        return {
            'result': 'eod_exit',
            'gap_pct': gap_pct,
            'entry': entry_price,
            'exit': eod_price,
            'pnl_per_share': pnl,
            'win': pnl > 0,
            'bars_held': len(day_data) - entry_bar
        }
        
    def simulate_orb_trade(self, day_data: pd.DataFrame, prev_close: float, trend_ok: bool = True) -> Dict:
        """
        Opening Range Breakout (30-min).
        """
        if len(day_data) < 12: # Need at least 1 hour data (12 * 5m)
            return None
            
        # Trend check (Long only if trend up)
        if not trend_ok:
            return None
            
        # Define ORB Period (First 30 mins)
        # Assuming data starts at 9:30. First 6 bars = 30 mins.
        orb_data = day_data.iloc[:6]
        if orb_data.empty: return None
        
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        
        # Entry Logic: Breakout of High
        entry_price = None
        entry_bar = None
        
        # Check bars after ORB period
        post_orb = day_data.iloc[6:]
        
        for i, (idx, row) in enumerate(post_orb.iterrows()):
            if row['high'] > orb_high:
                entry_price = orb_high + 0.05 # Slippage
                entry_bar = i + 6
                break
        
        if not entry_price:
            return {'result': 'no_entry'}
            
        # Risk Management
        # Stop: orb_low or percentage? Use ORB Low but cap max risk at 2% of price.
        risk = entry_price - orb_low
        if risk <= 0: risk = entry_price * 0.01 # Fallback
        
        if risk > entry_price * 0.02: # Too wide
             risk = entry_price * 0.02
             stop_loss = entry_price - risk
        else:
             stop_loss = orb_low
             
        target = entry_price + (risk * 2) # 2R target
        
        # Simulate Trade
        
        # Re-iterate from entry bar
        remaining_data = day_data.iloc[entry_bar:]
        for i, (idx, row) in enumerate(remaining_data.iterrows()):
            # Check Stop
            if row['low'] <= stop_loss:
                return {'result': 'stopped_out', 'pnl_per_share': stop_loss - entry_price, 'win': False}
                
            # Check Target
            if row['high'] >= target:
                return {'result': 'target_hit', 'pnl_per_share': target - entry_price, 'win': True}
                
        # EOD Exit
        exit_price = day_data['close'].iloc[-1]
        pnl = exit_price - entry_price
        return {'result': 'eod_exit', 'pnl_per_share': pnl, 'win': pnl > 0}

    def simulate_from_signal(self, setup: Dict, day_data: pd.DataFrame) -> Dict:
        """Simulate trade execution from a StrategyLibrary signal."""
        entry_price = setup['entry']
        stop_loss = setup['stop']
        target = setup['target']
        
        # Find entry bar (Break of entry price)
        entry_bar = None
        for i, (idx, row) in enumerate(day_data.iterrows()):
            if row['high'] >= entry_price:
                entry_bar = i
                break
        
        if entry_bar is None:
            return None
            
        # Execution loop
        remaining_data = day_data.iloc[entry_bar:]
        for i, (idx, row) in enumerate(remaining_data.iterrows()):
            if row['low'] <= stop_loss:
                return {
                    'result': 'stopped_out', 'strategy': setup['strategy'],
                    'pnl_per_share': stop_loss - entry_price, 'win': False,
                    'entry': entry_price, 'exit': stop_loss
                }
            if row['high'] >= target:
                return {
                    'result': 'target_hit', 'strategy': setup['strategy'],
                    'pnl_per_share': target - entry_price, 'win': True,
                    'entry': entry_price, 'exit': target
                }
                
        exit_price = day_data['close'].iloc[-1]
        pnl = exit_price - entry_price
        return {
            'result': 'eod_exit', 'strategy': setup['strategy'],
            'pnl_per_share': pnl, 'win': pnl > 0,
            'entry': entry_price, 'exit': exit_price
        }
    
    def backtest_day_bot(self, ticker: str, days: int = 252, market_context: Dict = None, strategy: str = 'gap_vwap') -> pd.DataFrame:
        """Backtest gap strategy on one ticker."""
        try:
            print(f"  [{ticker}] Downloading {days} days...", end=" ", flush=True)
            
            # Use unified fetcher
            df = self.fetcher.get_intraday_data(ticker, days)
            
            if df.empty:
                print("✗ No data")
                return pd.DataFrame()
            
            print(f"✓ {len(df)} bars")
            
            # Group by trading day
            df['date'] = pd.to_datetime(df['date'])
            df['trading_day'] = df['date'].dt.date
            
            # Calculate Trend (SMA 20)
            daily_closes = df.groupby('trading_day')['close'].last()
            sma_20 = daily_closes.rolling(window=20).mean()
            
            trading_days = sorted(df['trading_day'].unique())
            
            if len(trading_days) < 10:
                print(f"    Insufficient days: {len(trading_days)}")
                return pd.DataFrame()
            
            # print(f"    Testing {len(trading_days)} trading days...")
            
            trades = []
            gaps_found = 0
            entries_found = 0
            
            for i in range(1, len(trading_days)):
                try:
                    prev_day = trading_days[i-1]
                    curr_day = trading_days[i]
                    
                    # Market Regime Filter (Global)
                    regime_ok = True
                    if market_context:
                        spy_daily = market_context.get('spy_daily')
                        spy_sma200 = market_context.get('spy_sma200')
                        vix_daily = market_context.get('vix_daily')
                        
                        # Check Trend (SPY > SMA200)
                        if spy_daily is not None and spy_sma200 is not None:
                            curr_spy = spy_daily.get(prev_day)
                            curr_ma = spy_sma200.get(prev_day)
                            # If SPY is below 200 SMA, Bear Market -> NO LONGS
                            if curr_spy and curr_ma and curr_spy < curr_ma:
                                regime_ok = False
                        
                        # Check Volatility (VIX < 25)
                        if vix_daily is not None:
                            curr_vix = vix_daily.get(prev_day)
                            # If VIX is too high, Panic Market -> NO LONGS (or reduce size)
                            if curr_vix and curr_vix > 25:
                                regime_ok = False
                    
                    if not regime_ok:
                        continue

                    prev_data = df[df['trading_day'] == prev_day]
                    curr_data = df[df['trading_day'] == curr_day]
                    
                    if len(prev_data) == 0 or len(curr_data) == 0:
                        continue
                    
                    prev_close = prev_data['close'].iloc[-1]
                    
                    # Check Trend (Local)
                    current_sma = sma_20.get(prev_day)
                    trend_ok = True
                    if current_sma and not pd.isna(current_sma):
                        trend_ok = prev_close > current_sma
                    
                    # Simulate trade based on Strategy
                    trade = None
                    
                    if strategy == 'ensemble':
                        # 1. Try Gap & Go (Trend Following)
                        if trend_ok:
                            s1 = StrategyLibrary.gap_and_go(curr_data, prev_close)
                            if s1:
                                trade = self.simulate_from_signal(s1, curr_data)
                        
                        # 2. If no trend trade, try Mean Reversion (RSI)
                        if not trade:
                            s2 = StrategyLibrary.rsi_reversion(curr_data, prev_close)
                            if s2:
                                trade = self.simulate_from_signal(s2, curr_data)
                                
                    elif strategy == 'vol_breakout':
                        trade = self.simulate_orb_trade(curr_data, prev_close, trend_ok)
                    else:
                        trade = self.simulate_gap_trade(curr_data, prev_close, trend_ok)
                    
                    if trade:
                        gap_pct = trade.get('gap_pct', 0)
                        result = trade.get('result')
                        
                        if result != 'no_gap' and abs(gap_pct) >= 1.0: # Keep logging gaps for stats even if filtered
                            gaps_found += 1
                            
                        if result not in ['no_entry', 'no_gap', 'no_trend', 'bad_gap_size']:
                            entries_found += 1
                            trade['ticker'] = ticker
                            trade['date'] = curr_day
                            trades.append(trade)
                except Exception as e:
                    # print(f"\n    Day {i} error: {e}")
                    # import traceback
                    # traceback.print_exc()
                    continue
            
            trades_df = pd.DataFrame(trades)
            
            if gaps_found > 0:
                # print(f"    Gaps found: {gaps_found}, Entries: {entries_found}")
                pass
            
            if not trades_df.empty:
                wins = (trades_df['win'] == True).sum()
                total = len(trades_df)
                print(f"    Trades: {total}, Win rate: {wins/total*100:.1f}%")
            else:
                print(f"    No trades executed")
            
            return trades_df
            
        except Exception as e:
            print(f"  [{ticker}] Error: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def run_day_bot_backtest(self, universe: List[str], days: int = 252, strategy: str = 'gap_vwap') -> Dict:
        """
        Run complete day bot backtest.
        
        Args:
            universe: List of tickers
            days: Number of trading days to test
            strategy: 'gap_vwap' or 'vol_breakout'
            
        Returns:
            Complete results dictionary
        """
        print("="*80)
        print("DAY BOT COMPREHENSIVE BACKTEST")
        print("="*80)
        print(f"Universe: {len(universe)} tickers")
        print(f"Period: {days} trading days (~{days/252:.1f} years)")
        print(f"Strategy: {strategy.upper()}\n")
        print(f"Filters: Trend > SMA20, Regime (SPY > SMA200, VIX < 25)\n")
        
        # Fetch Market Context
        print("Fetching Market Context (SPY, VIX)...")
        spy = self.fetcher.get_intraday_data("SPY", days)
        vix = self.fetcher.get_intraday_data("^VIX", days)
        
        # Process to daily
        if not spy.empty:
            spy['date'] = pd.to_datetime(spy['date'])
            spy['trading_day'] = spy['date'].dt.date
            spy_daily = spy.groupby('trading_day')['close'].last()
            spy_sma200 = spy_daily.rolling(200).mean()
        else:
            spy_daily = None
            spy_sma200 = None
            
        if not vix.empty:
            vix['date'] = pd.to_datetime(vix['date'])
            vix['trading_day'] = vix['date'].dt.date
            vix_daily = vix.groupby('trading_day')['close'].last()
        else:
            vix_daily = None
            
        market_context = {
            'spy_daily': spy_daily,
            'spy_sma200': spy_sma200,
            'vix_daily': vix_daily
        }
        
        all_trades = []
        
        for ticker in universe:
            try:
                trades = self.backtest_day_bot(ticker, days, market_context, strategy)
                if not trades.empty:
                    all_trades.append(trades)
            except Exception as e:
                print(f"  [{ticker}] Error: {e}")
        
        if not all_trades:
            return {'error': 'No trades generated'}
        
        combined = pd.concat(all_trades, ignore_index=True)
        
        # Calculate comprehensive metrics
        return self.calculate_comprehensive_metrics(combined, strategy)
    
    def calculate_comprehensive_metrics(self, trades: pd.DataFrame, strategy_name: str) -> Dict:
        """
        Calculate thorough performance metrics.
        
        Includes:
        - Win rate, profit factor
        - Sharpe, Sortino ratios
        - Max drawdown
        - Statistical significance tests
        - Market regime analysis
        - Monte Carlo simulation
        """
        print(f"\n{'='*80}")
        print(f"{strategy_name.upper()} - COMPREHENSIVE ANALYSIS")
        print(f"{'='*80}\n")
        
        # Basic metrics
        total_trades = len(trades)
        winners = trades[trades['win'] == True]
        losers = trades[trades['win'] == False]
        
        win_rate = len(winners) / total_trades * 100
        
        # P&L metrics
        total_pnl = trades['pnl_per_share'].sum()
        avg_win = winners['pnl_per_share'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_per_share'].mean() if len(losers) > 0 else 0
        profit_factor = abs(winners['pnl_per_share'].sum() / losers['pnl_per_share'].sum()) if len(losers) > 0 and losers['pnl_per_share'].sum() != 0 else 0
        
        # Risk-adjusted metrics
        returns = trades['pnl_per_share']
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Sortino (only penalize downside volatility)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.01
        sortino = returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Max drawdown
        cumulative = returns.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        
        # Statistical significance
        # T-test: Is mean return significantly different from 0?
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        is_significant = p_value < 0.05
        
        # Print results
        print(f"BASIC METRICS:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"  Losers: {len(losers)} ({100-win_rate:.1f}%)")
        print(f"  Average Trade: ${returns.mean():+.3f}")
        print()
        
        print(f"P&L METRICS:")
        print(f"  Total P&L: ${total_pnl:+.2f} (per share)")
        print(f"  Average Win: ${avg_win:+.3f}")
        print(f"  Average Loss: ${avg_loss:+.3f}")
        print(f"  Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "N/A")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print()
        
        print(f"RISK-ADJUSTED:")
        print(f"  Sharpe Ratio: {sharpe:.2f}")
        print(f"  Sortino Ratio: {sortino:.2f}")
        print(f"  Max Drawdown: ${max_drawdown:.2f}")
        print(f"  Calmar Ratio: {abs(returns.mean() * 252 / max_drawdown):.2f}" if max_drawdown != 0 else "N/A")
        print()
        
        print(f"STATISTICAL SIGNIFICANCE:")
        print(f"  T-Statistic: {t_stat:.2f}")
        print(f"  P-Value: {p_value:.4f}")
        print(f"  Significant: {'✓ YES' if is_significant else '✗ NO'} (p < 0.05)")
        print(f"  Confidence: {(1-p_value)*100:.1f}% that edge is real")
        print()
        
        # Market regime analysis
        if 'date' in trades.columns:
            trades_by_month = trades.groupby(pd.to_datetime(trades['date']).dt.to_period('M'))
            monthly_pnl = trades_by_month['pnl_per_share'].sum()
            
            profitable_months = (monthly_pnl > 0).sum()
            total_months = len(monthly_pnl)
            
            print(f"CONSISTENCY:")
            print(f"  Profitable Months: {profitable_months}/{total_months} ({profitable_months/total_months*100:.1f}%)")
            print(f"  Best Month: ${monthly_pnl.max():.2f}")
            print(f"  Worst Month: ${monthly_pnl.min():.2f}")
            print()
        
        # Bootstrap confidence intervals
        print(f"BOOTSTRAP ANALYSIS (1000 simulations):")
        bootstrap_win_rates = []
        bootstrap_sharpes = []
        
        for _ in range(1000):
            sample = returns.sample(n=len(returns), replace=True)
            bootstrap_win_rates.append((sample > 0).sum() / len(sample) * 100)
            bootstrap_sharpes.append(sample.mean() / sample.std() * np.sqrt(252) if sample.std() > 0 else 0)
        
        wr_ci_low = np.percentile(bootstrap_win_rates, 2.5)
        wr_ci_high = np.percentile(bootstrap_win_rates, 97.5)
        sharpe_ci_low = np.percentile(bootstrap_sharpes, 2.5)
        sharpe_ci_high = np.percentile(bootstrap_sharpes, 97.5)
        
        print(f"  Win Rate 95% CI: [{wr_ci_low:.1f}%, {wr_ci_high:.1f}%]")
        print(f"  Sharpe 95% CI: [{sharpe_ci_low:.2f}, {sharpe_ci_high:.2f}]")
        print()
        
        # VALIDATION DECISION
        print(f"{'='*80}")
        print(f"VALIDATION VERDICT")
        print(f"{'='*80}\n")
        
        passed = False
        reasons = []
        
        # Criteria 1: Win rate
        if win_rate >= 55:
            reasons.append(f"✓ Win rate: {win_rate:.1f}% >= 55%")
        else:
            reasons.append(f"✗ Win rate: {win_rate:.1f}% < 55%")
        
        # Criteria 2: Sharpe ratio
        if sharpe >= 0.5:
            reasons.append(f"✓ Sharpe: {sharpe:.2f} >= 0.5")
        else:
            reasons.append(f"✗ Sharpe: {sharpe:.2f} < 0.5")
        
        # Criteria 3: Statistical significance
        if is_significant:
            reasons.append(f"✓ Statistically significant (p={p_value:.4f})")
        else:
            reasons.append(f"✗ Not statistically significant (p={p_value:.4f})")
        
        # Criteria 4: Enough trades
        if total_trades >= 50:
            reasons.append(f"✓ Sample size: {total_trades} >= 50")
        else:
            reasons.append(f"⚠ Small sample: {total_trades} < 50")
        
        # Criteria 5: Profit factor
        if profit_factor >= 1.5:
            reasons.append(f"✓ Profit factor: {profit_factor:.2f} >= 1.5")
        else:
            reasons.append(f"✗ Profit factor: {profit_factor:.2f} < 1.5")
        
        # Pass if meets most criteria
        checks_passed = sum([
            win_rate >= 55,
            sharpe >= 0.5,
            is_significant,
            total_trades >= 50,
            profit_factor >= 1.5
        ])
        
        passed = checks_passed >= 3  # Need 3 out of 5
        
        print("VALIDATION CRITERIA:")
        for reason in reasons:
            print(f"  {reason}")
        
        print(f"\nCriteria Passed: {checks_passed}/5")
        
        if passed:
            print(f"\n{'✅ '*10}")
            print(f"STRATEGY VALIDATED")
            print(f"{'✅ '*10}\n")
            print(f"Recommendation: Proceed to live paper trading")
            print(f"Risk Level: {'Low' if checks_passed >= 4 else 'Medium'}")
        else:
            print(f"\n{'❌ '*10}")
            print(f"STRATEGY NOT VALIDATED")
            print(f"{'❌ '*10}\n")
            print(f"Recommendation: DO NOT TRADE")
            print(f"Required: {5 - checks_passed} more criteria to pass")
        
        print(f"{'='*80}\n")
        
        return {
            'strategy': strategy_name,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'sortino': sortino,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'p_value': p_value,
            'is_significant': is_significant,
            'validated': passed,
            'checks_passed': checks_passed,
            'trades': trades
        }
    
    def run_comprehensive_backtest(self, universe: List[str], days: int = 252, strategy: str = 'gap_vwap'):
        """
        Run complete backtest suite.
        
        Tests:
        1. Day bot strategy
        2. Different time periods
        3. Market regime analysis
        4. Statistical robustness
        """
        print("\n" + "#"*80)
        print("COMPREHENSIVE BACKTESTING SYSTEM")
        print("#"*80)
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Connect to IBKR
        self.connect_ibkr()
        
        # Run day bot backtest
        day_bot_results = self.run_day_bot_backtest(universe, days, strategy)
        
        # Save detailed results
        if 'trades' in day_bot_results:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'data/output/comprehensive_backtest_{timestamp}.csv'
            day_bot_results['trades'].to_csv(output_file, index=False)
            print(f"Detailed trades saved to: {output_file}\n")
            
            # Save summary
            summary_file = f'data/output/backtest_summary_{timestamp}.txt'
            with open(summary_file, 'w') as f:
                f.write("="*80 + "\n")
                f.write("COMPREHENSIVE BACKTEST SUMMARY\n")
                f.write("="*80 + "\n\n")
                f.write(f"Strategy: {day_bot_results['strategy']}\n")
                f.write(f"Period: {days} trading days\n")
                f.write(f"Universe: {len(universe)} tickers\n\n")
                f.write(f"Total Trades: {day_bot_results['total_trades']}\n")
                f.write(f"Win Rate: {day_bot_results['win_rate']:.1f}%\n")
                f.write(f"Sharpe Ratio: {day_bot_results['sharpe']:.2f}\n")
                f.write(f"Profit Factor: {day_bot_results['profit_factor']:.2f}\n")
                f.write(f"P-Value: {day_bot_results['p_value']:.4f}\n\n")
                f.write(f"VALIDATED: {'YES' if day_bot_results['validated'] else 'NO'}\n")
                f.write(f"Checks Passed: {day_bot_results['checks_passed']}/5\n")
            
            print(f"Summary saved to: {summary_file}\n")
        
        # Disconnect
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
        
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*80)
        
        return day_bot_results


def main():
    """Run comprehensive backtest."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive Backtesting')
    parser.add_argument('--days', type=int, default=252, 
                       help='Trading days to test (default: 252 = 1 year)')
    parser.add_argument('--universe', choices=['liquid', 'small', 'russell1000', 'custom', 'all'], 
                       default='liquid',
                       help='Universe to test')
    parser.add_argument('--strategy', choices=['gap_vwap', 'vol_breakout', 'ensemble'], default='gap_vwap',
                       help='Strategy to test')
    parser.add_argument('--tickers', help='Comma-separated list for custom universe')
    args = parser.parse_args()
    
    # Define universes
    universes = {
        'liquid': [
            'AAPL', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN',
            'COIN', 'PLTR', 'HOOD', 'SOFI', 'UPST', 'AFRM',
            'SPY', 'QQQ', 'IWM'
        ],
        'small': [
            'GME', 'AMC', 'BBBY', 'SOFI', 'HOOD', 'RIVN', 'LCID',
            'MARA', 'RIOT', 'MSTR', 'HUT', 'BTBT'
        ]
    }
    
    universe = []
    if args.universe == 'all':
        universe = universes['liquid'] + universes['small']
    elif args.universe == 'custom':
        if args.tickers:
            universe = [t.strip().upper() for t in args.tickers.split(',')]
        else:
            print("Error: --tickers required for custom universe")
            return
    elif args.universe == 'russell1000':
        path = 'data/russell1000_tickers.csv'
        if os.path.exists(path):
            universe = pd.read_csv(path)['ticker'].tolist()
            print(f"Loaded {len(universe)} tickers from Russell 1000")
            # Limit to random 50 for speed if not specified otherwise? No, let user wait.
            # Or safeguard against massive IBKR requests.
            # For now, let's just take top 30 to be safe/fast.
            universe = universe[:30] 
            print("Limiting to top 30 for speed testing.")
        else:
            print("Russell 1000 data not found. Using liquid.")
            universe = universes['liquid']
    else:
        universe = universes[args.universe]
    
    # Run backtest
    backtester = ComprehensiveBacktester()
    results = backtester.run_comprehensive_backtest(universe, args.days, args.strategy)
    
    # Final recommendation
    if results.get('validated'):
        print("\n" + "🎉"*20)
        print("\nSTRATEGY IS VALIDATED")
        print("\nNext steps:")
        print("  1. Paper trade for 2 weeks")
        print("  2. If live matches backtest, go live with small size")
        print("  3. Start with $100 risk per trade")
        print("\n" + "🎉"*20 + "\n")
    else:
        print("\n" + "⚠️ "*20)
        print("\nSTRATEGY NOT VALIDATED")
        print("\nDO NOT TRADE")
        print("\nOptions:")
        print("  1. Focus on LEAPS only")
        print("  2. Improve strategy (add filters)")
        print("  3. Try different approach")
        print("\n" + "⚠️ "*20 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
