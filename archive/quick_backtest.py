#!/usr/bin/env python3
"""
Quick Gap Strategy Backtest
============================

Uses daily data (faster, more reliable) to validate gap trading approach.

Tests:
- Gap detection (open vs previous close)
- Entry at open (simplified - can't use VWAP without intraday)
- Exit at close (day trade)
- Win rate calculation

This is FASTER and MORE RELIABLE than intraday backtest.
Still validates if gap trading works.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from scipy import stats


def backtest_gap_strategy_daily(ticker: str, period: str = '2y') -> pd.DataFrame:
    """
    Backtest gap strategy using daily data.
    
    Simplified but valid:
    - Detects gaps at open
    - Enters at open
    - Exits at close (same day)
    - Tracks if gap continues or fades
    """
    try:
        print(f"  [{ticker}] Downloading...", end=" ", flush=True)
        
        # Download daily data (fast, reliable)
        df = yf.download(ticker, period=period, progress=False)
        
        if df.empty or len(df) < 100:
            print("✗ Insufficient data")
            return pd.DataFrame()
        
        print(f"✓ {len(df)} days")
        
        # Calculate gaps
        df['prev_close'] = df['Close'].shift(1)
        df['gap_pct'] = (df['Open'] - df['prev_close']) / df['prev_close'] * 100
        
        # Calculate intraday move
        df['intraday_pct'] = (df['Close'] - df['Open']) / df['Open'] * 100
        
        # Filter: Only gaps > 1%
        gaps = df[abs(df['gap_pct']) > 1.0].copy()
        
        if len(gaps) == 0:
            print(f"    No gaps found")
            return pd.DataFrame()
        
        # Simulate trades
        # If gap up: Go long, profit if closes higher than open
        # If gap down: Go short, profit if closes lower than open
        gaps['trade_direction'] = np.sign(gaps['gap_pct'])
        gaps['trade_pnl'] = gaps['trade_direction'] * gaps['intraday_pct']
        gaps['win'] = gaps['trade_pnl'] > 0
        
        # Add ticker and date
        gaps['ticker'] = ticker
        gaps['date'] = gaps.index
        
        print(f"    Found {len(gaps)} gap trades")
        
        return gaps[['ticker', 'date', 'gap_pct', 'intraday_pct', 'trade_pnl', 'win']]
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return pd.DataFrame()


def run_backtest(universe: list, period: str = '2y'):
    """Run backtest on universe."""
    print("="*80)
    print("QUICK GAP STRATEGY BACKTEST")
    print("="*80)
    print(f"Universe: {len(universe)} tickers")
    print(f"Period: {period}")
    print(f"Strategy: Trade gaps >1%, exit at close\n")
    
    all_trades = []
    
    for ticker in universe:
        trades = backtest_gap_strategy_daily(ticker, period)
        if not trades.empty:
            all_trades.append(trades)
    
    if not all_trades:
        print("\n✗ No trades generated")
        return
    
    combined = pd.concat(all_trades, ignore_index=True)
    
    # Analysis
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}\n")
    
    total = len(combined)
    winners = combined[combined['win'] == True]
    losers = combined[combined['win'] == False]
    
    win_rate = len(winners) / total * 100
    avg_win = winners['trade_pnl'].mean()
    avg_loss = losers['trade_pnl'].mean()
    
    # Risk-adjusted
    returns = combined['trade_pnl']
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    # Statistical significance
    t_stat, p_value = stats.ttest_1samp(returns, 0)
    
    # Bootstrap
    bootstrap_wr = []
    for _ in range(1000):
        sample = returns.sample(n=len(returns), replace=True)
        bootstrap_wr.append((sample > 0).sum() / len(sample) * 100)
    
    wr_ci_low = np.percentile(bootstrap_wr, 2.5)
    wr_ci_high = np.percentile(bootstrap_wr, 97.5)
    
    print(f"Total Trades: {total}")
    print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
    print(f"Losers: {len(losers)}")
    print(f"\nAverage Win: {avg_win:+.2f}%")
    print(f"Average Loss: {avg_loss:+.2f}%")
    print(f"Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x")
    print(f"\nSharpe Ratio: {sharpe:.2f}")
    print(f"P-Value: {p_value:.4f} ({'Significant' if p_value < 0.05 else 'Not significant'})")
    print(f"\nWin Rate 95% CI: [{wr_ci_low:.1f}%, {wr_ci_high:.1f}%]")
    
    # Validation
    print(f"\n{'='*80}")
    print(f"VALIDATION")
    print(f"{'='*80}\n")
    
    checks = []
    checks.append(('Win Rate >= 52%', win_rate >= 52))
    checks.append(('Sharpe >= 0.3', sharpe >= 0.3))
    checks.append(('Statistically Significant', p_value < 0.05))
    checks.append(('Sample Size >= 50', total >= 50))
    checks.append(('Avg Win > |Avg Loss|', abs(avg_win) > abs(avg_loss)))
    
    passed = sum([c[1] for c in checks])
    
    for check, result in checks:
        print(f"  {'✓' if result else '✗'} {check}")
    
    print(f"\nPassed: {passed}/5")
    
    if passed >= 3:
        print(f"\n✅ STRATEGY VALIDATED")
        print(f"\nGap trading shows edge. Proceed to:")
        print(f"  1. Live validation (manual execution)")
        print(f"  2. Paper trading (2 weeks)")
        print(f"  3. Live trading ($100 risk)")
    else:
        print(f"\n❌ STRATEGY NOT VALIDATED")
        print(f"\nGap trading doesn't show sufficient edge.")
        print(f"Recommendation: Focus on LEAPS only")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    combined.to_csv(f'data/output/gap_backtest_{timestamp}.csv', index=False)
    print(f"\nResults saved to: data/output/gap_backtest_{timestamp}.csv")
    
    return combined


if __name__ == "__main__":
    # Liquid universe for $20K account
    universe = [
        'AAPL', 'NVDA', 'TSLA', 'AMD', 'META', 'GOOGL', 'AMZN',
        'COIN', 'PLTR', 'HOOD', 'SOFI', 
        'SPY', 'QQQ', 'IWM',
        'UPST', 'AFRM'
    ]
    
    run_backtest(universe, period='2y')

