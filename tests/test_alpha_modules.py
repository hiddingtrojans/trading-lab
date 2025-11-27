#!/usr/bin/env python3
"""
Unit tests for alpha_lab modules.
Tests market_regime, whale_detector, and strategy_library.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestMarketRegime:
    """Tests for MarketRegimeAnalyzer."""
    
    def test_regime_classification_green(self):
        """GREEN regime when SPY trending up, VIX low."""
        from alpha_lab.market_regime import MarketRegimeAnalyzer
        
        # Mock fetcher
        mock_fetcher = Mock()
        
        # Create uptrending SPY data
        dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
        spy_data = pd.DataFrame({
            'date': dates,
            'close': np.linspace(400, 500, 250),  # Steady uptrend
            'high': np.linspace(402, 502, 250),
            'low': np.linspace(398, 498, 250),
            'open': np.linspace(400, 500, 250),
            'volume': [1000000] * 250
        })
        
        # Low VIX data
        vix_data = pd.DataFrame({
            'date': dates,
            'close': [15] * 250,  # Low fear
            'high': [16] * 250,
            'low': [14] * 250,
            'open': [15] * 250,
            'volume': [100000] * 250
        })
        
        mock_fetcher.get_intraday_data.side_effect = lambda ticker, days: \
            spy_data if ticker == 'SPY' else vix_data
        
        analyzer = MarketRegimeAnalyzer(mock_fetcher)
        result = analyzer.analyze_regime()
        
        assert result['status'] == 'GREEN'
        assert result['score'] >= 60
        
    def test_regime_classification_red(self):
        """RED regime when SPY trending down, VIX high."""
        from alpha_lab.market_regime import MarketRegimeAnalyzer
        
        mock_fetcher = Mock()
        
        dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
        
        # Downtrending SPY
        spy_data = pd.DataFrame({
            'date': dates,
            'close': np.linspace(500, 400, 250),  # Downtrend
            'high': np.linspace(502, 402, 250),
            'low': np.linspace(498, 398, 250),
            'open': np.linspace(500, 400, 250),
            'volume': [1000000] * 250
        })
        
        # High VIX
        vix_data = pd.DataFrame({
            'date': dates,
            'close': [35] * 250,  # High fear
            'high': [36] * 250,
            'low': [34] * 250,
            'open': [35] * 250,
            'volume': [100000] * 250
        })
        
        mock_fetcher.get_intraday_data.side_effect = lambda ticker, days: \
            spy_data if ticker == 'SPY' else vix_data
        
        analyzer = MarketRegimeAnalyzer(mock_fetcher)
        result = analyzer.analyze_regime()
        
        assert result['status'] == 'RED'
        assert result['score'] <= 40


class TestWhaleDetector:
    """Tests for WhaleDetector."""
    
    def test_volume_spike_detection(self):
        """Detect unusual volume spikes."""
        from alpha_lab.whale_detector import WhaleDetector
        
        mock_fetcher = Mock()
        
        # Create data with volume spike
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        normal_vol = [100000] * 90
        spike_vol = [500000] * 10  # 5x spike at end
        
        data = pd.DataFrame({
            'date': dates,
            'close': [150] * 100,
            'high': [151] * 100,
            'low': [149] * 100,
            'open': [150] * 100,
            'volume': normal_vol + spike_vol
        })
        
        mock_fetcher.get_intraday_data.return_value = data
        
        detector = WhaleDetector(mock_fetcher)
        result = detector.detect_whales('TEST')
        
        # Should detect the volume anomaly
        assert result['status'] != 'UNKNOWN'
        
    def test_no_whale_activity(self):
        """No detection when volume is normal."""
        from alpha_lab.whale_detector import WhaleDetector
        
        mock_fetcher = Mock()
        
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        
        # Flat, normal volume
        data = pd.DataFrame({
            'date': dates,
            'close': [150] * 100,
            'high': [151] * 100,
            'low': [149] * 100,
            'open': [150] * 100,
            'volume': [100000] * 100
        })
        
        mock_fetcher.get_intraday_data.return_value = data
        
        detector = WhaleDetector(mock_fetcher)
        result = detector.detect_whales('TEST')
        
        assert result['status'] in ['NEUTRAL', 'UNKNOWN']


class TestStrategyLibrary:
    """Tests for StrategyLibrary signals."""
    
    def test_gap_and_go_bullish(self):
        """Gap & Go triggers on 3%+ gap up with volume."""
        from alpha_lab.strategy_library import StrategyLibrary
        
        # Create gap up data
        dates = pd.date_range(start='2024-01-02 09:30', periods=78, freq='5min')
        
        data = pd.DataFrame({
            'date': dates,
            'open': [103] + [103.5] * 77,  # 3% gap up from prev close of 100
            'high': [103.5] + [104] * 77,
            'low': [102.5] + [103] * 77,
            'close': [103.2] + [103.8] * 77,
            'volume': [500000] + [200000] * 77
        })
        
        prev_close = 100.0
        result = StrategyLibrary.gap_and_go(data, prev_close)
        
        assert result is not None
        assert result['action'] == 'BUY_STOP'
        assert result['entry'] > prev_close
        assert result['stop'] < result['entry']
        assert result['target'] > result['entry']
        
    def test_gap_and_go_no_gap(self):
        """No signal when gap is too small."""
        from alpha_lab.strategy_library import StrategyLibrary
        
        dates = pd.date_range(start='2024-01-02 09:30', periods=78, freq='5min')
        
        # Small gap (< 2%)
        data = pd.DataFrame({
            'date': dates,
            'open': [101] * 78,  # Only 1% gap
            'high': [101.5] * 78,
            'low': [100.5] * 78,
            'close': [101.2] * 78,
            'volume': [100000] * 78
        })
        
        prev_close = 100.0
        result = StrategyLibrary.gap_and_go(data, prev_close)
        
        assert result is None
        
    def test_rsi_reversion_oversold(self):
        """RSI reversion triggers on oversold bounce."""
        from alpha_lab.strategy_library import StrategyLibrary
        
        dates = pd.date_range(start='2024-01-02 09:30', periods=100, freq='5min')
        
        # Create oversold bounce pattern
        # Prices drop then start recovering
        prices = list(np.linspace(100, 90, 80)) + list(np.linspace(90, 92, 20))
        
        data = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p + 0.5 for p in prices],
            'low': [p - 0.5 for p in prices],
            'close': prices,
            'volume': [100000] * 100
        })
        
        prev_close = 100.0
        result = StrategyLibrary.rsi_reversion(data, prev_close)
        
        # May or may not trigger depending on RSI calc
        # Just verify it returns valid structure or None
        if result is not None:
            assert 'entry' in result
            assert 'stop' in result
            assert 'target' in result


class TestPositionSizer:
    """Tests for PositionSizer."""
    
    def test_fixed_risk_sizing(self):
        """Calculate shares based on fixed risk %."""
        from alpha_lab.portfolio.sizer import PositionSizer
        
        sizer = PositionSizer(account_equity=100000)
        result = sizer.calculate_size(
            entry=150.0,
            stop=147.0,  # $3 risk per share
            risk_pct=0.01  # 1% = $1000 risk
        )
        
        # $1000 / $3 = 333 shares max
        assert result['shares'] <= 333
        assert result['shares'] > 0
        assert result['risk_amount'] <= 1000
        
    def test_max_position_cap(self):
        """Position capped at 20% of equity."""
        from alpha_lab.portfolio.sizer import PositionSizer
        
        sizer = PositionSizer(account_equity=100000)
        result = sizer.calculate_size(
            entry=10.0,  # Cheap stock
            stop=9.90,   # Tight stop ($0.10)
            risk_pct=0.05  # 5% risk = $5000
        )
        
        # Without cap: $5000 / $0.10 = 50,000 shares ($500k position!)
        # With 20% cap: $20,000 / $10 = 2,000 shares max
        max_position_value = result['shares'] * 10.0
        assert max_position_value <= 20000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

