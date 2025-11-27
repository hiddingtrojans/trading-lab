#!/usr/bin/env python3
"""
Breakout Predictor System
=========================

Comprehensive system to identify stocks likely to "explode" upwards in 1-8 weeks.
Uses IBKR data with dynamic universe optimization, ensemble ranking, and proper CV.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import lightgbm as lgb
from sklearn.preprocessing import RobustScaler
from ib_insync import IB, Stock, util
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# PART 1: DYNAMIC UNIVERSE BUILDER
# ============================================================================

class UniverseBuilder:
    """Build optimized universe of stocks from IBKR."""
    
    def __init__(self, ib: IB, config: Dict):
        self.ib = ib
        self.cfg = config
        
    def get_universe_from_ibkr(self, 
                               scan_codes: List[str] = None,
                               max_stocks: int = 2000) -> List[str]:
        """
        Pull universe of US stocks from IBKR scanners.
        
        Args:
            scan_codes: List of scanner codes to use
            max_stocks: Maximum stocks to retrieve
            
        Returns:
            List of ticker symbols
        """
        from ib_insync import ScannerSubscription
        
        if scan_codes is None:
            scan_codes = [
                'MOST_ACTIVE',
                'HOT_BY_VOLUME', 
                'TOP_PERC_GAIN',
                'TOP_VOLUME',
                'HOT_BY_PRICE'
            ]
        
        all_symbols = set()
        
        print(f"Pulling universe from IBKR using {len(scan_codes)} scanner codes...")
        
        for scan_code in scan_codes:
            try:
                scanner_sub = ScannerSubscription(
                    instrument='STK',
                    locationCode='STK.US',
                    scanCode=scan_code,
                    numberOfRows=max_stocks // len(scan_codes)
                )
                
                scan_data = self.ib.reqScannerData(scanner_sub)
                self.ib.sleep(2)
                
                for item in scan_data:
                    symbol = item.contractDetails.contract.symbol
                    all_symbols.add(symbol)
                    
                print(f"  {scan_code}: {len(scan_data)} stocks")
                
            except Exception as e:
                print(f"  Warning: {scan_code} failed: {e}")
                continue
        
        print(f"Total unique symbols: {len(all_symbols)}")
        return sorted(list(all_symbols))
    
    def filter_universe_dynamic(self, 
                               symbols: List[str],
                               lookback_days: int = 252) -> List[str]:
        """
        Dynamically filter universe based on historical breakout distributions.
        
        Args:
            symbols: List of symbols to filter
            lookback_days: Days of history to analyze
            
        Returns:
            Filtered list of symbols
        """
        print(f"\nDynamically filtering {len(symbols)} symbols...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 100)
        
        valid_symbols = []
        stats = []
        
        # Download data in chunks for efficiency
        chunk_size = 50
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i+chunk_size]
            
            try:
                data = yf.download(
                    chunk, 
                    start=start_date, 
                    end=end_date,
                    group_by='ticker',
                    threads=True,
                    progress=False
                )
                
                for symbol in chunk:
                    try:
                        if len(chunk) == 1:
                            df = data
                        else:
                            if symbol not in data.columns.get_level_values(0):
                                continue
                            df = data[symbol]
                        
                        if df.empty or len(df) < 200:
                            continue
                        
                        # Calculate key metrics
                        close = df['Close'].dropna()
                        volume = df['Volume'].dropna()
                        
                        if len(close) < 200:
                            continue
                        
                        price = close.iloc[-1]
                        avg_volume = volume.tail(20).mean()
                        dollar_volume = price * avg_volume
                        volatility = close.pct_change().tail(60).std() * np.sqrt(252)
                        
                        # Calculate breakout potential score
                        returns_20d = close.pct_change(20).dropna()
                        returns_60d = close.pct_change(60).dropna()
                        
                        # Check if stock has had big moves in the past
                        historical_breakouts = (returns_20d > 0.15).sum()
                        
                        # Store stats
                        stats.append({
                            'symbol': symbol,
                            'price': price,
                            'dollar_volume': dollar_volume,
                            'volatility': volatility,
                            'historical_breakouts': historical_breakouts,
                            'avg_return_20d': returns_20d.mean(),
                            'max_return_20d': returns_20d.max()
                        })
                        
                        valid_symbols.append(symbol)
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"  Warning: chunk {i//chunk_size} failed: {e}")
                continue
            
            if (i // chunk_size + 1) % 5 == 0:
                print(f"  Processed {i+chunk_size}/{len(symbols)} symbols...")
        
        # Convert to DataFrame for analysis
        stats_df = pd.DataFrame(stats)
        
        if stats_df.empty:
            print("Warning: No valid symbols found")
            return []
        
        # Dynamic filtering based on distributions
        print("\nOptimizing universe boundaries...")
        
        # Remove extreme outliers and penny stocks
        price_lower = stats_df['price'].quantile(0.02)  # Adaptive
        price_upper = stats_df['price'].quantile(0.98)
        
        dv_threshold = stats_df['dollar_volume'].quantile(0.25)  # Bottom quartile
        vol_upper = stats_df['volatility'].quantile(0.95)  # Remove ultra-high vol
        
        print(f"  Price range: ${price_lower:.2f} - ${price_upper:.2f}")
        print(f"  Min dollar volume: ${dv_threshold:,.0f}")
        print(f"  Max volatility: {vol_upper:.2%}")
        
        # Apply filters
        filtered = stats_df[
            (stats_df['price'] >= price_lower) &
            (stats_df['price'] <= price_upper) &
            (stats_df['dollar_volume'] >= dv_threshold) &
            (stats_df['volatility'] <= vol_upper) &
            (stats_df['historical_breakouts'] >= 2)  # Has history of breakouts
        ]
        
        print(f"\nFiltered universe: {len(filtered)} stocks")
        
        return filtered['symbol'].tolist(), stats_df


# ============================================================================
# PART 2: COMPREHENSIVE SIGNAL ENGINEERING
# ============================================================================

class SignalEngineer:
    """Engineer comprehensive signals for breakout prediction."""
    
    @staticmethod
    def fetch_historical_data(symbols: List[str], 
                             lookback_days: int = 500) -> pd.DataFrame:
        """Fetch historical data for all symbols."""
        print(f"\nFetching {lookback_days} days of data for {len(symbols)} symbols...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        data = yf.download(
            symbols,
            start=start_date,
            end=end_date,
            group_by='ticker',
            threads=True,
            progress=False
        )
        
        return data
    
    @staticmethod
    def engineer_momentum_signals(df: pd.DataFrame) -> pd.DataFrame:
        """Engineer momentum-based signals."""
        close = df['Close'] if 'Close' in df else df['close']
        
        signals = pd.DataFrame(index=df.index)
        
        # Multiple timeframe momentum
        for period in [5, 10, 20, 40, 60]:
            signals[f'mom_{period}d'] = close.pct_change(period)
        
        # Acceleration
        signals['mom_accel'] = signals['mom_10d'] - signals['mom_20d']
        
        # Relative momentum (vs MA)
        for period in [20, 50, 200]:
            ma = close.rolling(period).mean()
            signals[f'rel_ma{period}'] = (close - ma) / ma
        
        return signals
    
    @staticmethod
    def engineer_volatility_signals(df: pd.DataFrame) -> pd.DataFrame:
        """Engineer volatility contraction signals."""
        close = df['Close'] if 'Close' in df else df['close']
        returns = close.pct_change()
        
        signals = pd.DataFrame(index=df.index)
        
        # Historical volatility at multiple windows
        for period in [10, 20, 60]:
            signals[f'hvol_{period}d'] = returns.rolling(period).std() * np.sqrt(252)
        
        # Volatility contraction (squeeze)
        signals['vol_squeeze'] = signals['hvol_10d'] / signals['hvol_60d']
        signals['vol_regime'] = signals['hvol_20d'].rolling(60).rank(pct=True)
        
        # Bollinger Band width
        bb_period = 20
        bb_std = 2
        ma = close.rolling(bb_period).mean()
        std = close.rolling(bb_period).std()
        signals['bb_width'] = (std * bb_std * 2) / ma
        signals['bb_squeeze'] = signals['bb_width'].rolling(60).rank(pct=True)
        
        return signals
    
    @staticmethod
    def engineer_volume_signals(df: pd.DataFrame) -> pd.DataFrame:
        """Engineer volume surge signals."""
        volume = df['Volume'] if 'Volume' in df else df['volume']
        close = df['Close'] if 'Close' in df else df['close']
        
        signals = pd.DataFrame(index=df.index)
        
        # Volume ratios
        for period in [5, 10, 20]:
            vol_ma = volume.rolling(period).mean()
            signals[f'vol_ratio_{period}d'] = volume / vol_ma
        
        # Dollar volume
        signals['dollar_vol'] = close * volume
        signals['dollar_vol_ratio'] = signals['dollar_vol'] / signals['dollar_vol'].rolling(20).mean()
        
        # On-Balance Volume
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        signals['obv_trend'] = obv / obv.rolling(20).mean()
        
        # Volume-price divergence
        price_mom = close.pct_change(10)
        vol_mom = volume.pct_change(10)
        signals['vp_divergence'] = vol_mom - price_mom
        
        return signals
    
    @staticmethod
    def engineer_relative_strength(df: pd.DataFrame, 
                                   benchmark_data: pd.DataFrame) -> pd.DataFrame:
        """Engineer relative strength vs benchmark."""
        close = df['Close'] if 'Close' in df else df['close']
        
        # Align benchmark to stock data
        bench_close = benchmark_data['Close'].reindex(df.index, method='ffill')
        
        signals = pd.DataFrame(index=df.index)
        
        # Relative strength at multiple timeframes
        for period in [5, 10, 20, 60]:
            stock_ret = close.pct_change(period)
            bench_ret = bench_close.pct_change(period)
            signals[f'rs_{period}d'] = stock_ret - bench_ret
        
        # Relative strength rank
        signals['rs_rank'] = signals['rs_20d'].rolling(60).rank(pct=True)
        
        return signals
    
    @staticmethod
    def engineer_microstructure_signals(df: pd.DataFrame) -> pd.DataFrame:
        """Engineer microstructure signals."""
        high = df['High'] if 'High' in df else df['high']
        low = df['Low'] if 'Low' in df else df['low']
        close = df['Close'] if 'Close' in df else df['close']
        
        signals = pd.DataFrame(index=df.index)
        
        # True Range
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        
        signals['atr'] = tr.rolling(14).mean()
        signals['atr_pct'] = signals['atr'] / close
        
        # High-Low range
        signals['hl_range'] = (high - low) / close
        signals['hl_squeeze'] = signals['hl_range'].rolling(20).mean() / signals['hl_range'].rolling(60).mean()
        
        # Gap signals
        signals['gap'] = (close - close.shift()) / close.shift()
        signals['gap_up_count'] = (signals['gap'] > 0.02).rolling(20).sum()
        
        return signals
    
    @staticmethod
    def engineer_pattern_signals(df: pd.DataFrame) -> pd.DataFrame:
        """Engineer pattern-based signals."""
        close = df['Close'] if 'Close' in df else df['close']
        high = df['High'] if 'High' in df else df['high']
        low = df['Low'] if 'Low' in df else df['low']
        
        signals = pd.DataFrame(index=df.index)
        
        # Higher highs / higher lows
        signals['higher_high'] = (high > high.shift()).rolling(5).sum()
        signals['higher_low'] = (low > low.shift()).rolling(5).sum()
        signals['uptrend_strength'] = signals['higher_high'] + signals['higher_low']
        
        # Consolidation detection
        signals['range_20d'] = close.rolling(20).max() - close.rolling(20).min()
        signals['consolidation'] = signals['range_20d'] / close.rolling(20).mean()
        
        # Distance from 52-week high
        signals['dist_52w_high'] = (close.rolling(252).max() - close) / close
        
        return signals
    
    def build_all_features(self, 
                          symbols: List[str],
                          lookback_days: int = 500) -> pd.DataFrame:
        """Build all features for all symbols."""
        print("\nEngineering comprehensive signal suite...")
        
        # Fetch benchmark (SPY) first
        spy_data = yf.download('SPY', 
                              start=datetime.now() - timedelta(days=lookback_days),
                              end=datetime.now(),
                              progress=False)
        
        # Normalize SPY column names
        if isinstance(spy_data.columns, pd.MultiIndex):
            spy_data.columns = spy_data.columns.get_level_values(0)
        
        all_features = []
        
        # Process each symbol individually to avoid yfinance multi-level column issues
        for i, symbol in enumerate(symbols):
            try:
                if (i + 1) % 10 == 0:
                    print(f"  Processing {i+1}/{len(symbols)} symbols...")
                
                # Download single symbol
                sym_data = yf.download(
                    symbol,
                    start=datetime.now() - timedelta(days=lookback_days),
                    end=datetime.now(),
                    progress=False
                )
                
                if sym_data.empty or len(sym_data) < 100:
                    continue
                
                # Normalize column names
                if isinstance(sym_data.columns, pd.MultiIndex):
                    sym_data.columns = sym_data.columns.get_level_values(0)
                
                # Engineer all signal groups
                mom_sigs = self.engineer_momentum_signals(sym_data)
                vol_sigs = self.engineer_volatility_signals(sym_data)
                volume_sigs = self.engineer_volume_signals(sym_data)
                rs_sigs = self.engineer_relative_strength(sym_data, spy_data)
                micro_sigs = self.engineer_microstructure_signals(sym_data)
                pattern_sigs = self.engineer_pattern_signals(sym_data)
                
                # Combine all features
                features = pd.concat([
                    mom_sigs, vol_sigs, volume_sigs, 
                    rs_sigs, micro_sigs, pattern_sigs
                ], axis=1)
                
                features['symbol'] = symbol
                features['price'] = sym_data['Close']
                
                all_features.append(features)
                
            except Exception as e:
                print(f"  Warning: Failed to engineer features for {symbol}: {e}")
                continue
        
        if not all_features:
            raise ValueError("No features engineered for any symbols")
        
        # Combine all symbols
        combined = pd.concat(all_features)
        combined = combined.reset_index()
        combined = combined.rename(columns={'Date': 'date'})
        
        print(f"Feature engineering complete: {len(combined)} rows, {len(combined.columns)} features")
        print(f"  Successfully processed {len(all_features)}/{len(symbols)} symbols")
        
        return combined


# ============================================================================
# PART 3: NESTED CV WITH PURGE/EMBARGO
# ============================================================================

class NestedCV:
    """Nested cross-validation with purge and embargo."""
    
    @staticmethod
    def purge_embargo_split(dates: pd.DatetimeIndex,
                           train_frac: float = 0.7,
                           embargo_days: int = 5,
                           n_splits: int = 5) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Create time-series splits with purge and embargo.
        
        Args:
            dates: DatetimeIndex of dates
            train_frac: Fraction of data for training
            embargo_days: Days to embargo between train/test
            n_splits: Number of splits
            
        Returns:
            List of (train_idx, test_idx) tuples
        """
        splits = []
        unique_dates = dates.unique()
        n_dates = len(unique_dates)
        
        # Calculate split points
        test_size = n_dates // n_splits
        
        for i in range(n_splits):
            # Test set
            test_start = i * test_size
            test_end = min((i + 1) * test_size, n_dates)
            
            if test_end >= n_dates:
                break
            
            test_dates = unique_dates[test_start:test_end]
            
            # Train set (all data before test, with embargo)
            embargo_date = test_dates[0] - pd.Timedelta(days=embargo_days)
            train_dates = unique_dates[unique_dates < embargo_date]
            
            if len(train_dates) < 30:  # Minimum training days
                continue
            
            # Convert to indices
            train_idx = dates.isin(train_dates)
            test_idx = dates.isin(test_dates)
            
            splits.append((np.where(train_idx)[0], np.where(test_idx)[0]))
        
        return splits
    
    @staticmethod
    def nested_cv_optimize(X: pd.DataFrame,
                          y: pd.Series,
                          param_grid: Dict,
                          embargo_days: int = 5) -> Tuple[Dict, float]:
        """
        Nested CV for hyperparameter optimization.
        
        Args:
            X: Features
            y: Target (forward returns)
            param_grid: Parameter grid to search
            embargo_days: Embargo period
            
        Returns:
            best_params, best_score
        """
        print("\nRunning nested CV for hyperparameter optimization...")
        
        dates = pd.to_datetime(X['date'])
        X_vals = X.drop(columns=['date', 'symbol'], errors='ignore').values
        y_vals = y.values
        
        # Outer loop splits
        outer_splits = NestedCV.purge_embargo_split(dates, embargo_days=embargo_days, n_splits=3)
        
        best_params = None
        best_score = -np.inf
        
        # Try each parameter combination
        from itertools import product
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        print(f"Testing {len(param_combinations)} parameter combinations...")
        
        for params_tuple in param_combinations:
            params = dict(zip(param_names, params_tuple))
            
            # Inner CV scores
            cv_scores = []
            
            for train_idx, test_idx in outer_splits:
                X_train, X_test = X_vals[train_idx], X_vals[test_idx]
                y_train, y_test = y_vals[train_idx], y_vals[test_idx]
                
                # Handle NaNs
                train_valid = ~np.isnan(y_train).ravel()
                test_valid = ~np.isnan(y_test).ravel()
                
                X_train = X_train[train_valid]
                y_train = y_train[train_valid]
                X_test = X_test[test_valid]
                y_test = y_test[test_valid]
                
                if len(y_train) < 100 or len(y_test) < 10:
                    continue
                
                # Clean training data
                X_train_clean = np.nan_to_num(X_train, nan=0.0, posinf=1e10, neginf=-1e10)
                X_train_clean = np.clip(X_train_clean, -1e10, 1e10)
                
                X_test_clean = np.nan_to_num(X_test, nan=0.0, posinf=1e10, neginf=-1e10)
                X_test_clean = np.clip(X_test_clean, -1e10, 1e10)
                
                # Train model
                train_data = lgb.Dataset(X_train_clean, label=y_train)
                model = lgb.train(params, train_data, num_boost_round=300)
                
                # Predict and score
                preds = model.predict(X_test_clean)
                
                # Score: IC (information coefficient)
                ic = np.corrcoef(preds, y_test)[0, 1]
                cv_scores.append(ic)
            
            if cv_scores:
                mean_score = np.mean(cv_scores)
                
                if mean_score > best_score:
                    best_score = mean_score
                    best_params = params
        
        print(f"Best IC: {best_score:.4f}")
        print(f"Best params: {best_params}")
        
        return best_params, best_score


# ============================================================================
# PART 4: ENSEMBLE RANKING MODEL
# ============================================================================

class EnsembleRanker:
    """Ensemble model for breakout prediction."""
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {
            'objective': 'regression',
            'metric': 'rmse',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1
        }
        self.models = []
        self.scaler = RobustScaler()
        
    def fit(self, X: np.ndarray, y: np.ndarray, n_models: int = 5):
        """Fit ensemble of models."""
        print(f"\nTraining ensemble of {n_models} models...")
        
        # Remove infinities and extreme values
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        
        # Clip extreme values
        X_clean = np.clip(X_clean, -1e10, 1e10)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_clean)
        
        for i in range(n_models):
            print(f"  Training model {i+1}/{n_models}...")
            
            # Add some randomness via bagging
            params = self.params.copy()
            params['bagging_seed'] = i
            params['feature_fraction_seed'] = i
            
            train_data = lgb.Dataset(X_scaled, label=y)
            model = lgb.train(params, train_data, num_boost_round=500)
            
            self.models.append(model)
        
        print("Ensemble training complete")
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using ensemble average."""
        # Remove infinities and extreme values
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        X_clean = np.clip(X_clean, -1e10, 1e10)
        
        X_scaled = self.scaler.transform(X_clean)
        
        preds = np.array([model.predict(X_scaled) for model in self.models])
        return preds.mean(axis=0)
    
    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict with uncertainty estimate."""
        # Remove infinities and extreme values
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        X_clean = np.clip(X_clean, -1e10, 1e10)
        
        X_scaled = self.scaler.transform(X_clean)
        
        preds = np.array([model.predict(X_scaled) for model in self.models])
        
        mean_pred = preds.mean(axis=0)
        std_pred = preds.std(axis=0)
        
        return mean_pred, std_pred


# Save to be continued in next file...
print("Breakout Predictor System - Part 1 Complete")
