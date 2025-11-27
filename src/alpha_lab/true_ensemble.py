#!/usr/bin/env python3
"""
True Ensemble Model
===================

Combines LightGBM, XGBoost, CatBoost, and Neural Networks.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, List
from sklearn.preprocessing import RobustScaler
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
import lightgbm as lgb
import xgboost as xgb
import catboost as cb
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)


class TrueEnsemble:
    """
    True ensemble combining multiple algorithm families:
    - Gradient Boosting: LightGBM, XGBoost, CatBoost
    - Neural Network: MLP
    - Linear: Ridge (for diversity)
    """
    
    def __init__(self, optimize_params: bool = True, n_trials: int = 50):
        """
        Initialize true ensemble.
        
        Args:
            optimize_params: Whether to use Optuna for hyperparameter tuning
            n_trials: Number of Optuna trials (if optimizing)
        """
        self.optimize_params = optimize_params
        self.n_trials = n_trials
        self.models = {}
        self.weights = {}
        self.scaler = RobustScaler()
        self.feature_names = None
        
    def _optimize_lgb(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Optimize LightGBM parameters with Optuna."""
        print("  Optimizing LightGBM...")
        
        def objective(trial):
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'verbosity': -1,
                'learning_rate': trial.suggest_float('lr', 0.01, 0.3, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 15, 127),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
                'bagging_freq': 5,
                'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 20, 200, log=True),
                'lambda_l1': trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
                'lambda_l2': trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),
            }
            
            # Quick 3-fold CV
            cv_scores = []
            n_folds = 3
            fold_size = len(X) // n_folds
            
            for fold in range(n_folds):
                val_start = fold * fold_size
                val_end = (fold + 1) * fold_size if fold < n_folds - 1 else len(X)
                
                train_idx = np.concatenate([np.arange(0, val_start), np.arange(val_end, len(X))])
                val_idx = np.arange(val_start, val_end)
                
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y[train_idx], y[val_idx]
                
                train_data = lgb.Dataset(X_tr, label=y_tr)
                val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
                
                model = lgb.train(
                    params,
                    train_data,
                    num_boost_round=300,
                    valid_sets=[val_data],
                    callbacks=[lgb.early_stopping(50, verbose=False)]
                )
                
                preds = model.predict(X_val)
                
                # Information Coefficient
                ic = np.corrcoef(preds, y_val)[0, 1]
                cv_scores.append(ic)
            
            return np.mean(cv_scores)
        
        study = optuna.create_study(direction='maximize', study_name='lgb')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        best_params = study.best_params
        
        # Rename 'lr' to 'learning_rate' for LightGBM
        if 'lr' in best_params:
            best_params['learning_rate'] = best_params.pop('lr')
        
        best_params.update({
            'objective': 'regression',
            'metric': 'rmse',
            'verbosity': -1,
            'bagging_freq': 5
        })
        
        print(f"    Best IC: {study.best_value:.4f}")
        return best_params
    
    def _optimize_xgb(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Optimize XGBoost parameters."""
        print("  Optimizing XGBoost...")
        
        def objective(trial):
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'verbosity': 0,
                'learning_rate': trial.suggest_float('lr', 0.01, 0.3, log=True),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            }
            
            cv_scores = []
            n_folds = 3
            fold_size = len(X) // n_folds
            
            for fold in range(n_folds):
                val_start = fold * fold_size
                val_end = (fold + 1) * fold_size if fold < n_folds - 1 else len(X)
                
                train_idx = np.concatenate([np.arange(0, val_start), np.arange(val_end, len(X))])
                val_idx = np.arange(val_start, val_end)
                
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y[train_idx], y[val_idx]
                
                model = xgb.XGBRegressor(**params, n_estimators=300, early_stopping_rounds=50)
                model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
                
                preds = model.predict(X_val)
                ic = np.corrcoef(preds, y_val)[0, 1]
                cv_scores.append(ic)
            
            return np.mean(cv_scores)
        
        study = optuna.create_study(direction='maximize', study_name='xgb')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        best_params = study.best_params
        
        # Rename 'lr' to 'learning_rate' for XGBoost
        if 'lr' in best_params:
            best_params['learning_rate'] = best_params.pop('lr')
        
        best_params.update({
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'verbosity': 0
        })
        
        print(f"    Best IC: {study.best_value:.4f}")
        return best_params
    
    def _optimize_catboost(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Optimize CatBoost parameters."""
        print("  Optimizing CatBoost...")
        
        def objective(trial):
            params = {
                'loss_function': 'RMSE',
                'verbose': False,
                'learning_rate': trial.suggest_float('lr', 0.01, 0.3, log=True),
                'depth': trial.suggest_int('depth', 4, 10),
                'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-8, 10.0, log=True),
                'bagging_temperature': trial.suggest_float('bagging_temperature', 0, 1),
                'random_strength': trial.suggest_float('random_strength', 1e-8, 10.0, log=True),
            }
            
            cv_scores = []
            n_folds = 3
            fold_size = len(X) // n_folds
            
            for fold in range(n_folds):
                val_start = fold * fold_size
                val_end = (fold + 1) * fold_size if fold < n_folds - 1 else len(X)
                
                train_idx = np.concatenate([np.arange(0, val_start), np.arange(val_end, len(X))])
                val_idx = np.arange(val_start, val_end)
                
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y[train_idx], y[val_idx]
                
                model = cb.CatBoostRegressor(**params, iterations=300, early_stopping_rounds=50)
                model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
                
                preds = model.predict(X_val)
                ic = np.corrcoef(preds, y_val)[0, 1]
                cv_scores.append(ic)
            
            return np.mean(cv_scores)
        
        study = optuna.create_study(direction='maximize', study_name='catboost')
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        best_params = study.best_params
        
        # Rename 'lr' to 'learning_rate' for CatBoost
        if 'lr' in best_params:
            best_params['learning_rate'] = best_params.pop('lr')
        
        best_params.update({
            'loss_function': 'RMSE',
            'verbose': False
        })
        
        print(f"    Best IC: {study.best_value:.4f}")
        return best_params
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fit all models in ensemble."""
        print("\nTraining True Ensemble (5 diverse models)...")
        
        # Clean data
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        X_clean = np.clip(X_clean, -1e10, 1e10)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_clean)
        
        # Get optimized parameters
        if self.optimize_params:
            print("\nHyperparameter Optimization (this will take 10-20 minutes)...")
            lgb_params = self._optimize_lgb(X_scaled, y)
            xgb_params = self._optimize_xgb(X_scaled, y)
            cb_params = self._optimize_catboost(X_scaled, y)
        else:
            # Default parameters
            lgb_params = {
                'objective': 'regression',
                'learning_rate': 0.05,
                'num_leaves': 31,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbosity': -1
            }
            xgb_params = {
                'objective': 'reg:squarederror',
                'learning_rate': 0.05,
                'max_depth': 6,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'verbosity': 0
            }
            cb_params = {
                'loss_function': 'RMSE',
                'learning_rate': 0.05,
                'depth': 6,
                'verbose': False
            }
        
        print("\nTraining individual models...")
        
        # 1. LightGBM
        print("  [1/5] Training LightGBM...")
        train_data = lgb.Dataset(X_scaled, label=y)
        self.models['lgb'] = lgb.train(lgb_params, train_data, num_boost_round=500)
        
        # 2. XGBoost
        print("  [2/5] Training XGBoost...")
        self.models['xgb'] = xgb.XGBRegressor(**xgb_params, n_estimators=500)
        self.models['xgb'].fit(X_scaled, y, verbose=False)
        
        # 3. CatBoost
        print("  [3/5] Training CatBoost...")
        self.models['cat'] = cb.CatBoostRegressor(**cb_params, iterations=500)
        self.models['cat'].fit(X_scaled, y, verbose=False)
        
        # 4. Neural Network
        print("  [4/5] Training Neural Network...")
        self.models['nn'] = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=256,
            learning_rate='adaptive',
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42,
            verbose=False
        )
        self.models['nn'].fit(X_scaled, y)
        
        # 5. Ridge (linear baseline)
        print("  [5/5] Training Ridge Regression...")
        self.models['ridge'] = Ridge(alpha=1.0)
        self.models['ridge'].fit(X_scaled, y)
        
        # Calculate ensemble weights based on training IC
        print("\nCalculating ensemble weights...")
        self._calculate_weights(X_scaled, y)
        
        print("True Ensemble training complete")
        print(f"  Model weights: {self.weights}")
    
    def _calculate_weights(self, X: np.ndarray, y: np.ndarray):
        """Calculate weights for each model based on IC."""
        ics = {}
        
        for name, model in self.models.items():
            preds = self._predict_single(model, X, name)
            ic = np.corrcoef(preds, y)[0, 1]
            ics[name] = max(ic, 0)  # Use max(ic, 0) to avoid negative weights
        
        # Normalize to sum to 1
        total_ic = sum(ics.values())
        if total_ic > 0:
            self.weights = {name: ic/total_ic for name, ic in ics.items()}
        else:
            # Equal weights if all ICs are negative
            self.weights = {name: 1/len(self.models) for name in self.models}
    
    def _predict_single(self, model, X: np.ndarray, model_name: str) -> np.ndarray:
        """Predict from a single model."""
        if model_name == 'lgb':
            return model.predict(X)
        else:
            return model.predict(X)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using weighted ensemble."""
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        X_clean = np.clip(X_clean, -1e10, 1e10)
        X_scaled = self.scaler.transform(X_clean)
        
        # Get predictions from all models
        predictions = {}
        for name, model in self.models.items():
            predictions[name] = self._predict_single(model, X_scaled, name)
        
        # Weighted average
        ensemble_pred = sum(
            self.weights[name] * predictions[name]
            for name in self.models
        )
        
        return ensemble_pred
    
    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict with uncertainty from model disagreement."""
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        X_clean = np.clip(X_clean, -1e10, 1e10)
        X_scaled = self.scaler.transform(X_clean)
        
        # Get predictions from all models
        all_preds = []
        for name, model in self.models.items():
            preds = self._predict_single(model, X_scaled, name)
            all_preds.append(preds)
        
        all_preds = np.array(all_preds)
        
        # Weighted mean and std
        mean_pred = sum(
            self.weights[name] * all_preds[i]
            for i, name in enumerate(self.models)
        )
        
        # Uncertainty = standard deviation across models
        std_pred = np.std(all_preds, axis=0)
        
        return mean_pred, std_pred


print("True Ensemble Module - Loaded")
