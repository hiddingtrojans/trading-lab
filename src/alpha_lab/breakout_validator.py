#!/usr/bin/env python3
"""
Breakout Validator
==================

Walk-forward backtesting and validation with proper embargo.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ============================================================================
# WALK-FORWARD BACKTEST ENGINE
# ============================================================================

class WalkForwardValidator:
    """Walk-forward validation engine with proper embargo."""
    
    def __init__(self, embargo_days: int = 5, holdout_months: int = 6):
        self.embargo_days = embargo_days
        self.holdout_months = holdout_months
        self.results = []
        
    def create_forward_labels(self, 
                             data: pd.DataFrame,
                             forward_days: int = 30) -> pd.Series:
        """
        Create forward return labels.
        
        Args:
            data: DataFrame with 'date', 'symbol', 'price'
            forward_days: Days ahead to predict
            
        Returns:
            Series of forward returns
        """
        print(f"\nCreating {forward_days}-day forward return labels...")
        
        # Sort by symbol and date
        data = data.sort_values(['symbol', 'date'])
        
        # Calculate forward returns
        labels = []
        
        for symbol in data['symbol'].unique():
            sym_data = data[data['symbol'] == symbol].copy()
            sym_data = sym_data.sort_values('date')
            
            # Forward return = (price_t+N - price_t) / price_t
            fwd_ret = sym_data['price'].shift(-forward_days) / sym_data['price'] - 1
            
            labels.append(pd.DataFrame({
                'date': sym_data['date'],
                'symbol': symbol,
                'fwd_return': fwd_ret
            }))
        
        labels_df = pd.concat(labels, ignore_index=True)
        
        # Merge back to original data
        result = data.merge(labels_df, on=['date', 'symbol'], how='left')
        
        print(f"Labels created: {(~result['fwd_return'].isna()).sum()} valid, "
              f"{result['fwd_return'].isna().sum()} NaN")
        
        return result['fwd_return']
    
    def split_holdout(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into training and holdout sets.
        
        Args:
            data: Full dataset
            
        Returns:
            train_data, holdout_data
        """
        dates = pd.to_datetime(data['date'])
        cutoff_date = dates.max() - pd.Timedelta(days=self.holdout_months * 30)
        
        train_mask = dates < cutoff_date
        holdout_mask = dates >= cutoff_date
        
        train_data = data[train_mask].copy()
        holdout_data = data[holdout_mask].copy()
        
        print(f"\nTrain/Holdout split:")
        print(f"  Train: {len(train_data)} samples ({train_data['date'].min()} to {train_data['date'].max()})")
        print(f"  Holdout: {len(holdout_data)} samples ({holdout_data['date'].min()} to {holdout_data['date'].max()})")
        
        return train_data, holdout_data
    
    def rolling_walk_forward(self,
                            data: pd.DataFrame,
                            model,
                            window_months: int = 12,
                            step_months: int = 1) -> pd.DataFrame:
        """
        Rolling walk-forward backtest.
        
        Args:
            data: Full dataset with features and labels
            model: Model object with fit() and predict() methods
            window_months: Training window in months
            step_months: Step size in months
            
        Returns:
            DataFrame with predictions and actuals
        """
        print(f"\nRunning rolling walk-forward backtest...")
        print(f"  Training window: {window_months} months")
        print(f"  Step size: {step_months} months")
        print(f"  Embargo: {self.embargo_days} days")
        
        data = data.copy()
        data['date'] = pd.to_datetime(data['date'])
        data = data.sort_values('date')
        
        # Feature columns (exclude metadata)
        feature_cols = [c for c in data.columns 
                       if c not in ['date', 'symbol', 'price', 'fwd_return']]
        
        results = []
        
        start_date = data['date'].min()
        end_date = data['date'].max() - pd.Timedelta(days=self.holdout_months * 30)
        
        current_date = start_date + pd.Timedelta(days=window_months * 30)
        fold = 0
        
        while current_date < end_date:
            fold += 1
            
            # Training window
            train_start = current_date - pd.Timedelta(days=window_months * 30)
            train_end = current_date - pd.Timedelta(days=self.embargo_days)
            
            # Test window
            test_start = current_date
            test_end = current_date + pd.Timedelta(days=step_months * 30)
            
            # Extract data
            train_mask = (data['date'] >= train_start) & (data['date'] < train_end)
            test_mask = (data['date'] >= test_start) & (data['date'] < test_end)
            
            train_data = data[train_mask]
            test_data = data[test_mask]
            
            if len(train_data) < 100 or len(test_data) < 10:
                current_date += pd.Timedelta(days=step_months * 30)
                continue
            
            # Prepare features and labels
            X_train = train_data[feature_cols].fillna(0).values
            y_train = train_data['fwd_return'].values
            
            X_test = test_data[feature_cols].fillna(0).values
            y_test = test_data['fwd_return'].values
            
            # Remove NaN labels
            train_valid = ~np.isnan(y_train)
            test_valid = ~np.isnan(y_test)
            
            X_train = X_train[train_valid]
            y_train = y_train[train_valid]
            
            X_test = X_test[test_valid]
            y_test = y_test[test_valid]
            test_data_valid = test_data[test_valid]
            
            if len(y_train) < 50 or len(y_test) < 5:
                current_date += pd.Timedelta(days=step_months * 30)
                continue
            
            print(f"\n  Fold {fold}: Train {len(X_train)}, Test {len(X_test)}")
            print(f"    Train: {train_start.date()} to {train_end.date()}")
            print(f"    Test:  {test_start.date()} to {test_end.date()}")
            
            # Train model
            try:
                model.fit(X_train, y_train)
                
                # Predict
                if hasattr(model, 'predict_with_uncertainty'):
                    preds, uncertainty = model.predict_with_uncertainty(X_test)
                else:
                    preds = model.predict(X_test)
                    uncertainty = np.zeros_like(preds)
                
                # Store results
                fold_results = test_data_valid[['date', 'symbol', 'price', 'fwd_return']].copy()
                fold_results['prediction'] = preds
                fold_results['uncertainty'] = uncertainty
                fold_results['fold'] = fold
                
                results.append(fold_results)
                
                # Fold metrics
                ic = np.corrcoef(preds, y_test)[0, 1]
                print(f"    IC: {ic:.4f}")
                
            except Exception as e:
                print(f"    Error in fold {fold}: {e}")
            
            # Move to next window
            current_date += pd.Timedelta(days=step_months * 30)
        
        if not results:
            raise ValueError("No valid folds in walk-forward backtest")
        
        all_results = pd.concat(results, ignore_index=True)
        
        print(f"\nWalk-forward complete: {fold} folds, {len(all_results)} predictions")
        
        return all_results
    
    def calculate_metrics(self, results: pd.DataFrame) -> Dict:
        """Calculate performance metrics."""
        print("\nCalculating performance metrics...")
        
        preds = results['prediction'].values
        actuals = results['fwd_return'].values
        
        # Remove NaNs
        valid = ~(np.isnan(preds) | np.isnan(actuals))
        preds = preds[valid]
        actuals = actuals[valid]
        
        # Information Coefficient
        ic = np.corrcoef(preds, actuals)[0, 1]
        
        # Rank IC
        pred_ranks = pd.Series(preds).rank(pct=True)
        actual_ranks = pd.Series(actuals).rank(pct=True)
        rank_ic = np.corrcoef(pred_ranks, actual_ranks)[0, 1]
        
        # Top/Bottom decile returns
        results_valid = results[valid].copy()
        results_valid['pred_decile'] = pd.qcut(preds, 10, labels=False, duplicates='drop')
        
        decile_rets = results_valid.groupby('pred_decile')['fwd_return'].mean()
        
        top_decile_ret = decile_rets.iloc[-1] if len(decile_rets) > 0 else 0
        bottom_decile_ret = decile_rets.iloc[0] if len(decile_rets) > 0 else 0
        long_short_ret = top_decile_ret - bottom_decile_ret
        
        # Hit rate (directional accuracy)
        hit_rate = ((np.sign(preds) == np.sign(actuals)).sum() / len(preds)
                    if len(preds) > 0 else 0)
        
        # Sharpe ratio of long-short portfolio
        if len(decile_rets) > 0:
            ls_sharpe = (long_short_ret / results_valid.groupby('pred_decile')['fwd_return'].std().mean()
                        if results_valid.groupby('pred_decile')['fwd_return'].std().mean() > 0 else 0)
        else:
            ls_sharpe = 0
        
        metrics = {
            'ic': ic,
            'rank_ic': rank_ic,
            'hit_rate': hit_rate,
            'top_decile_return': top_decile_ret,
            'bottom_decile_return': bottom_decile_ret,
            'long_short_return': long_short_ret,
            'long_short_sharpe': ls_sharpe,
            'n_predictions': len(preds)
        }
        
        print("\nPerformance Metrics:")
        print("=" * 50)
        for key, val in metrics.items():
            if 'return' in key or 'rate' in key:
                print(f"  {key}: {val:.2%}")
            else:
                print(f"  {key}: {val:.4f}")
        
        return metrics
    
    def generate_ranked_predictions(self,
                                   results: pd.DataFrame,
                                   top_n: int = 25,
                                   min_prediction: float = 0.05) -> pd.DataFrame:
        """
        Generate ranked list of top predictions.
        
        Args:
            results: Results DataFrame from walk-forward
            top_n: Number of top predictions to return
            min_prediction: Minimum prediction threshold
            
        Returns:
            DataFrame with top predictions ranked
        """
        print(f"\nGenerating top {top_n} ranked predictions...")
        
        # Get most recent predictions
        latest_date = results['date'].max()
        recent_results = results[results['date'] == latest_date].copy()
        
        # Filter by minimum prediction
        recent_results = recent_results[recent_results['prediction'] >= min_prediction]
        
        # Sort by prediction (descending)
        ranked = recent_results.sort_values('prediction', ascending=False)
        
        # Add rank
        ranked['rank'] = range(1, len(ranked) + 1)
        
        # Calculate risk score (based on uncertainty)
        if 'uncertainty' in ranked.columns:
            ranked['risk_score'] = pd.qcut(ranked['uncertainty'], 5, labels=['Low', 'Medium-Low', 'Medium', 'Medium-High', 'High'], duplicates='drop')
        else:
            ranked['risk_score'] = 'Unknown'
        
        top_picks = ranked.head(top_n)
        
        print(f"\nTop {len(top_picks)} predictions:")
        print("=" * 80)
        print(f"{'Rank':<6} {'Symbol':<8} {'Price':<10} {'Predicted':<12} {'Risk':<12}")
        print("-" * 80)
        
        for _, row in top_picks.iterrows():
            print(f"{int(row['rank']):<6} {row['symbol']:<8} ${row['price']:<9.2f} "
                  f"{row['prediction']:>+10.2%}  {str(row['risk_score']):<12}")
        
        return top_picks


# ============================================================================
# ARTIFACT GENERATOR
# ============================================================================

class ArtifactGenerator:
    """Generate plots and reports."""
    
    @staticmethod
    def plot_performance(results: pd.DataFrame, 
                        output_dir: str = 'data/output/breakout_artifacts'):
        """Generate performance plots."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\nGenerating performance plots in {output_dir}...")
        
        # 1. Equity curve (top decile)
        fig, ax = plt.subplots(figsize=(12, 6))
        
        results_sorted = results.sort_values('date')
        results_sorted['pred_decile'] = pd.qcut(results_sorted['prediction'], 
                                                 10, labels=False, duplicates='drop')
        
        # Top decile cumulative returns
        top_decile = results_sorted[results_sorted['pred_decile'] == 9]
        if len(top_decile) > 0:
            top_returns = top_decile.groupby('date')['fwd_return'].mean()
            cum_returns = (1 + top_returns).cumprod()
            
            ax.plot(cum_returns.index, cum_returns.values, linewidth=2, label='Top Decile')
            ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
            ax.set_xlabel('Date')
            ax.set_ylabel('Cumulative Return')
            ax.set_title('Top Decile Equity Curve')
            ax.legend()
            ax.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f'{output_dir}/equity_curve.png', dpi=150)
            plt.close()
        
        # 2. IC over time
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ic_by_date = []
        for date in results_sorted['date'].unique():
            date_data = results_sorted[results_sorted['date'] == date]
            if len(date_data) > 10:
                ic = np.corrcoef(date_data['prediction'], date_data['fwd_return'])[0, 1]
                ic_by_date.append({'date': date, 'ic': ic})
        
        if ic_by_date:
            ic_df = pd.DataFrame(ic_by_date)
            ax.plot(ic_df['date'], ic_df['ic'], linewidth=1.5)
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax.set_xlabel('Date')
            ax.set_ylabel('Information Coefficient')
            ax.set_title('IC Over Time')
            ax.grid(alpha=0.3)
            
            # Add rolling mean
            ic_df['ic_ma'] = ic_df['ic'].rolling(10).mean()
            ax.plot(ic_df['date'], ic_df['ic_ma'], linewidth=2, 
                   color='red', alpha=0.7, label='10-period MA')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig(f'{output_dir}/ic_over_time.png', dpi=150)
            plt.close()
        
        # 3. Returns by decile
        fig, ax = plt.subplots(figsize=(10, 6))
        
        decile_returns = results_sorted.groupby('pred_decile')['fwd_return'].mean()
        
        if len(decile_returns) > 0:
            ax.bar(range(len(decile_returns)), decile_returns.values)
            ax.set_xlabel('Prediction Decile')
            ax.set_ylabel('Mean Forward Return')
            ax.set_title('Returns by Prediction Decile')
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f'{output_dir}/returns_by_decile.png', dpi=150)
            plt.close()
        
        # 4. Prediction distribution
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        ax1.hist(results['prediction'], bins=50, alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Prediction')
        ax1.set_ylabel('Count')
        ax1.set_title('Prediction Distribution')
        ax1.grid(alpha=0.3)
        
        ax2.scatter(results['prediction'], results['fwd_return'], 
                   alpha=0.3, s=10)
        ax2.set_xlabel('Prediction')
        ax2.set_ylabel('Actual Forward Return')
        ax2.set_title('Prediction vs Actual')
        ax2.grid(alpha=0.3)
        
        # Add regression line
        valid = ~(np.isnan(results['prediction']) | np.isnan(results['fwd_return']))
        if valid.sum() > 0:
            z = np.polyfit(results[valid]['prediction'], 
                          results[valid]['fwd_return'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(results['prediction'].min(), 
                               results['prediction'].max(), 100)
            ax2.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/prediction_analysis.png', dpi=150)
        plt.close()
        
        print(f"Plots saved to {output_dir}")
    
    @staticmethod
    def generate_report(ranked_predictions: pd.DataFrame,
                       metrics: Dict,
                       output_dir: str = 'data/output/breakout_artifacts'):
        """Generate text report."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        report_path = f'{output_dir}/breakout_report.txt'
        
        print(f"\nGenerating report: {report_path}")
        
        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("BREAKOUT PREDICTION SYSTEM - RESEARCH REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("PERFORMANCE METRICS\n")
            f.write("-"*80 + "\n")
            for key, val in metrics.items():
                if 'return' in key or 'rate' in key:
                    f.write(f"{key:30s}: {val:>10.2%}\n")
                else:
                    f.write(f"{key:30s}: {val:>10.4f}\n")
            
            f.write("\n\nTOP 5 PREDICTIONS\n")
            f.write("-"*80 + "\n")
            f.write(f"{'Rank':<6} {'Symbol':<10} {'Price':<12} {'Predicted':<15} {'Risk':<12}\n")
            f.write("-"*80 + "\n")
            
            for _, row in ranked_predictions.head(5).iterrows():
                f.write(f"{int(row['rank']):<6} {row['symbol']:<10} "
                       f"${row['price']:<11.2f} {row['prediction']:>+13.2%}  "
                       f"{str(row['risk_score']):<12}\n")
            
            f.write("\n\nEXTENDED WATCHLIST (Next 20)\n")
            f.write("-"*80 + "\n")
            f.write(f"{'Rank':<6} {'Symbol':<10} {'Price':<12} {'Predicted':<15} {'Risk':<12}\n")
            f.write("-"*80 + "\n")
            
            for _, row in ranked_predictions.iloc[5:25].iterrows():
                f.write(f"{int(row['rank']):<6} {row['symbol']:<10} "
                       f"${row['price']:<11.2f} {row['prediction']:>+13.2%}  "
                       f"{str(row['risk_score']):<12}\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"Report saved to {report_path}")


print("Breakout Validator - Complete")
