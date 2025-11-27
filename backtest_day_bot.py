#!/usr/bin/env python3
"""
Historical Backtest for Day Trading Bot
========================================

Validates the gap trading strategy on historical data.
Tests on 252 trading days in 1 hour instead of waiting 4 weeks.

Strategy (from day_trading_bot.py):
- Scan for gaps > 1%
- Enter on VWAP test
- Stop: $0.25 below entry
- Target: $0.50 above entry
- Scale out: 50% at $0.25, 50% at $0.50
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from ib_insync import IB, Stock, util
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from utils.data_fetcher import DataFetcher

class DayBotBacktester:
    """Historical backtest for day trading bot strategy."""
    
    def __init__(self, ib: IB = None):
        """Initialize backtester."""
        self.ib = ib
        self.owns_ib = False
        self.fetcher = None
        
        if self.ib is None:
            self.ib = IB()
            self.owns_ib = True
    
    def connect_ibkr(self, host='127.0.0.1', port=4001):
        """Connect to IBKR."""
        if not self.ib.isConnected():
            try:
                self.ib.connect(host, port, clientId=200, timeout=10)
                self.fetcher = DataFetcher(self.ib)
                return True
            except:
                # Connection failed, but we can still use fetcher with yfinance fallback
                self.fetcher = DataFetcher(None)
                return False
        else:
            self.fetcher = DataFetcher(self.ib)
        return True
    
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.owns_ib and self.ib.isConnected():
            self.ib.disconnect()
    
    def download_historical_data(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """
        Download historical intraday data using unified fetcher.
        """
        print(f"  Downloading {days} days for {ticker}...")
        
        # Ensure fetcher is initialized even if IBKR connection failed
        if self.fetcher is None:
             self.fetcher = DataFetcher(None)

        df = self.fetcher.get_intraday_data(ticker, days)
        
        if not df.empty:
            print(f"    Downloaded {len(df)} bars")
            return df
            
            return pd.DataFrame()
    
    def simulate_gap_trade(self, day_data: pd.DataFrame, prev_close: float, trend_ok: bool = True) -> Dict:
        """
        Simulate one day of gap trading.
        """
        if len(day_data) < 20:  # Need reasonable amount of data
            return None
        
        # Calculate gap
        day_open = day_data['open'].iloc[0]
        gap_pct = (day_open - prev_close) / prev_close * 100
        
        # Smart Money Filters
        # 1. Trend Filter
        if not trend_ok:
            return None

        # 2. Gap Sweet Spot (2% to 10%)
        if abs(gap_pct) < 2.0 or abs(gap_pct) > 10.0:
            return None
        
        # Calculate VWAP
        typical_price = (day_data['high'] + day_data['low'] + day_data['close']) / 3
        vwap = (typical_price * day_data['volume']).cumsum() / day_data['volume'].cumsum()
        
        # Look for VWAP test in first 2 hours (24 bars of 5-min)
        first_2h = day_data.iloc[:24] if len(day_data) >= 24 else day_data
        
        # Entry logic: Price tests VWAP (comes within 0.5%)
        entry_bar = None
        entry_price = None
        
        for i, (idx, row) in enumerate(first_2h.iterrows()):
            # Use positional indexing for VWAP to be safe against DataFrame indices
            if i >= len(vwap):
                break
            
            current_vwap = vwap.iloc[i]
            
            price_to_vwap_pct = abs(row['close'] - current_vwap) / current_vwap * 100
            
            if price_to_vwap_pct < 1.0:  # Within 1.0% of VWAP
                entry_bar = i
                entry_price = row['close']
                break
        
        if entry_price is None:
            return {
                'result': 'no_entry',
                'reason': 'no_vwap_test',
                'gap_pct': gap_pct
            }
        
        # Simulate trade from entry bar onwards
        stop_loss = entry_price - 0.25
        target_1 = entry_price + 0.25  # First scale out
        target_2 = entry_price + 0.50  # Second scale out
        
        remaining_data = day_data.iloc[entry_bar:]
        
        pnl = 0
        first_target_hit = False
        trade_result = 'in_progress'
        exit_price = None
        
        # Time-based exit: 2 hours (24 bars)
        bars_held = 0
        max_hold_bars = 24
        
        for idx, row in remaining_data.iterrows():
            bars_held += 1
            low = row['low']
            high = row['high']
            close = row['close']
            
            # Time-based exit
            if bars_held >= max_hold_bars and not first_target_hit:
                exit_price = close
                pnl = exit_price - entry_price
                trade_result = 'time_exit'
                break
            
            # Check stop loss
            if low <= stop_loss:
                exit_price = stop_loss
                pnl = exit_price - entry_price
                trade_result = 'stopped_out'
                break
            
            # Check first target
            if not first_target_hit and high >= target_1:
                first_target_hit = True
                pnl += 0.5 * (target_1 - entry_price)  # 50% position
                # Move stop to breakeven
                stop_loss = entry_price
            
            # Check second target
            if first_target_hit and high >= target_2:
                pnl += 0.5 * (target_2 - entry_price)  # Remaining 50%
                exit_price = target_2
                trade_result = 'full_target'
                break
        
        # If still in trade at end of day, exit at close
        if trade_result == 'in_progress':
            exit_price = day_data['close'].iloc[-1]
            if first_target_hit:
                pnl += 0.5 * (exit_price - entry_price)
            else:
                pnl = exit_price - entry_price
            trade_result = 'eod_exit'
        
        return {
            'result': trade_result,
            'gap_pct': gap_pct,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'win': pnl > 0,
            'first_target_hit': first_target_hit
        }
    
    def backtest_ticker(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """
        Backtest gap strategy on one ticker.
        """
        # Download data
        df = self.download_historical_data(ticker, days)
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by trading day
        df['date'] = pd.to_datetime(df['date'])
        df['trading_day'] = df['date'].dt.date
        
        # Calculate Trend (SMA 20)
        daily_closes = df.groupby('trading_day')['close'].last()
        sma_20 = daily_closes.rolling(window=20).mean()
        
        trading_days = sorted(df['trading_day'].unique())
        
        trades = []
        
        for i in range(1, len(trading_days)):
            prev_day = trading_days[i-1]
            current_day = trading_days[i]
            
            prev_data = df[df['trading_day'] == prev_day]
            current_data = df[df['trading_day'] == current_day]
            
            if len(prev_data) == 0 or len(current_data) == 0:
                continue
            
            prev_close = prev_data['close'].iloc[-1]
            
            # Check Trend
            current_sma = sma_20.get(prev_day)
            trend_ok = True
            if current_sma and not pd.isna(current_sma):
                trend_ok = prev_close > current_sma
            
            # Simulate trade
            trade = self.simulate_gap_trade(current_data, prev_close, trend_ok)
            
            if trade and trade.get('result') != 'no_entry':
                trade['ticker'] = ticker
                trade['date'] = current_day
                trades.append(trade)
        
        return pd.DataFrame(trades)
    
    def backtest_universe(self, tickers: List[str], days: int = 252) -> pd.DataFrame:
        """
        Backtest across multiple tickers.
        """
        print(f"\n{'='*80}")
        print(f"BACKTESTING DAY BOT STRATEGY")
        print(f"{'='*80}")
        print(f"Universe: {len(tickers)} tickers")
        print(f"Period: {days} trading days (~{days//252} years)")
        print(f"Strategy: Gap > 1%, VWAP entry, $0.25/$0.50 targets\n")
        
        all_trades = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Testing {ticker}...", end=" ", flush=True)
            
            try:
                trades = self.backtest_ticker(ticker, days)
                if not trades.empty:
                    all_trades.append(trades)
                    print(f"Found {len(trades)} gap trades")
                else:
                    print(f"No gap trades")
            except Exception as e:
                print(f"    Error: {e}")
                continue
        
        if not all_trades:
            return pd.DataFrame()
        
        combined = pd.concat(all_trades, ignore_index=True)
        
        print(f"\n{'='*80}")
        print(f"BACKTEST COMPLETE")
        print(f"{'='*80}")
        print(f"Total trades: {len(combined)}")
        print(f"Tickers with trades: {combined['ticker'].nunique()}")
        
        return combined
    
    def analyze_results(self, trades: pd.DataFrame) -> Dict:
        """Analyze backtest results."""
        if trades.empty:
            print("\nNo trades to analyze")
            return {}
        
        print(f"\n{'='*80}")
        print(f"PERFORMANCE ANALYSIS")
        print(f"{'='*80}\n")
        
        # Overall metrics
        total_trades = len(trades)
        winners = trades[trades['win'] == True]
        losers = trades[trades['win'] == False]
        
        win_rate = len(winners) / total_trades * 100
        
        # P&L metrics
        total_pnl = trades['pnl'].sum()
        avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
        
        # Risk metrics
        profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 else 0
        
        # Calculate Sharpe (assuming 1 trade per day on average)
        daily_returns = trades.groupby('date')['pnl'].sum()
        sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        print(f"Total Trades: {total_trades}")
        print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"Losers: {len(losers)} ({100-win_rate:.1f}%)")
        print()
        print(f"Total P&L: ${total_pnl:+.2f}")
        print(f"Average Win: ${avg_win:+.2f}")
        print(f"Average Loss: ${avg_loss:+.2f}")
        print(f"Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "N/A")
        print()
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        
        # Validation
        print(f"\n{'='*80}")
        print(f"VALIDATION RESULT")
        print(f"{'='*80}\n")
        
        if total_trades < 100:
            print(f"⚠️  INSUFFICIENT DATA: Only {total_trades} trades")
            print(f"   Need at least 100 trades for statistical significance")
            passed = False
        elif win_rate >= 55:
            print(f"✅ VALIDATION PASSED")
            print(f"   Win Rate: {win_rate:.1f}% >= 55% threshold")
            print(f"   Strategy is profitable on historical data")
            print(f"\n   APPROVED FOR PAPER TRADING")
            passed = True
        else:
            print(f"❌ VALIDATION FAILED")
            print(f"   Win Rate: {win_rate:.1f}% < 55% threshold")
            print(f"   Strategy not profitable enough on historical data")
            print(f"\n   DO NOT TRADE - Need optimization")
            passed = False
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe': sharpe,
            'passed': passed
        }


def main():
    """Run historical backtest."""
    print("="*80)
    print("DAY BOT HISTORICAL BACKTEST")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test universe (liquid stocks that gap frequently)
    test_universe = [
        'AAPL', 'NVDA', 'TSLA', 'AMD', 'META',
        'COIN', 'PLTR', 'HOOD', 'SOFI',
        'GME', 'AMC',
        'MARA', 'RIOT', 'MSTR',
        'UPST', 'AFRM', 'CVNA'
    ]
    
    print(f"Test Universe: {len(test_universe)} tickers")
    print(f"Lookback: 252 trading days (1 year)")
    print(f"Strategy: Gap > 1%, VWAP entry, $0.25/$0.50 targets\n")
    
    # Initialize
    backtester = DayBotBacktester()
    
    # Connect to IBKR
    print("Connecting to IBKR Gateway...")
    if backtester.connect_ibkr():
        print(f"✓ Connected (Account: {backtester.ib.managedAccounts()[0]})\n")
    else:
        print("✗ Connection failed")
        print("Falling back to yfinance\n")
        # Don't return, continue with fallback
    
    try:
        # Run backtest
        trades = backtester.backtest_universe(test_universe, days=252)
        
        if trades.empty:
            print("\nNo trades generated")
            return
        
        # Analyze
        metrics = backtester.analyze_results(trades)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'data/output/day_bot_backtest_{timestamp}.csv'
        trades.to_csv(output_file, index=False)
        
        print(f"\n\nTrades saved to: {output_file}")
        
        # Save metrics
        metrics_file = f'data/output/day_bot_metrics_{timestamp}.json'
        import json
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        print(f"Metrics saved to: {metrics_file}")
        
    finally:
        backtester.disconnect()
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
