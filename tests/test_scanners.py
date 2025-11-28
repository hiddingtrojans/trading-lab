"""
Tests for scanner modules.

Run with: pytest tests/test_scanners.py -v
"""

import pytest
import os
import sys
import tempfile
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestUniverses:
    """Test centralized universe definitions."""
    
    def test_universes_import(self):
        from alpha_lab.universes import SMALL_CAP, MID_CAP, LIQUID_TECH, get_universe
        
        assert len(SMALL_CAP) > 50
        assert len(MID_CAP) > 20
        assert len(LIQUID_TECH) > 10
    
    def test_get_universe(self):
        from alpha_lab.universes import get_universe
        
        small = get_universe('small_cap')
        mid = get_universe('mid_cap')
        all_tickers = get_universe('all')
        tradeable = get_universe('tradeable')
        
        assert len(small) > 0
        assert len(mid) > 0
        assert len(all_tickers) >= len(small)
        assert len(tradeable) > 0
    
    def test_no_duplicates_in_all(self):
        from alpha_lab.universes import get_universe
        
        all_tickers = get_universe('all')
        assert len(all_tickers) == len(set(all_tickers))


class TestConfig:
    """Test configuration loading."""
    
    def test_config_loads(self):
        from alpha_lab.config import load_config, get_config
        
        config = load_config()
        assert 'account' in config
        assert 'extension' in config
        assert 'filters' in config
    
    def test_get_config_nested(self):
        from alpha_lab.config import get_config
        
        # Test nested access
        size = get_config('account.size')
        assert size is not None
        assert isinstance(size, (int, float))
        
        reject = get_config('extension.hard_reject_5d')
        assert reject is not None
    
    def test_get_config_default(self):
        from alpha_lab.config import get_config
        
        # Non-existent key should return default
        result = get_config('nonexistent.key', default=42)
        assert result == 42
    
    def test_config_namespace(self):
        from alpha_lab.config import get_cfg
        
        cfg = get_cfg()
        assert hasattr(cfg, 'account')
        assert hasattr(cfg.account, 'size')


class TestSignalTracker:
    """Test signal tracking."""
    
    @pytest.fixture
    def tracker(self):
        from alpha_lab.signal_tracker import SignalTracker
        
        # Use temp file for test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'signals': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'open': 0}}, f)
            temp_path = f.name
        
        tracker = SignalTracker(db_path=temp_path)
        yield tracker
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_log_signal(self, tracker):
        signal_id = tracker.log_signal(
            ticker='TEST',
            action='BUY NOW',
            entry=100.0,
            stop=95.0,
            target=115.0,
            reason='Test signal'
        )
        
        assert signal_id is not None
        assert 'TEST' in signal_id
        
        # Check stats updated
        stats = tracker.get_stats()
        assert stats['total_signals'] == 1
        assert stats['open'] == 1
    
    def test_get_open_signals(self, tracker):
        # Log a signal
        tracker.log_signal('TEST', 'BUY NOW', 100, 95, 115)
        
        open_signals = tracker.get_open_signals()
        assert len(open_signals) == 1
        assert open_signals[0]['ticker'] == 'TEST'
    
    def test_stats_calculation(self, tracker):
        stats = tracker.get_stats()
        
        assert 'total_signals' in stats
        assert 'wins' in stats
        assert 'losses' in stats
        assert 'win_rate' in stats


class TestPositionManager:
    """Test position management."""
    
    @pytest.fixture
    def manager(self):
        from alpha_lab.position_manager import PositionManager
        
        # Use temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'positions': [], 'closed': [], 'settings': {}}, f)
            temp_path = f.name
        
        manager = PositionManager(db_path=temp_path, account_size=100000)
        yield manager
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_add_position(self, manager):
        pos_id = manager.add_position(
            ticker='NVDA',
            shares=10,
            entry=450.0,
            stop=430.0,
            target=500.0
        )
        
        assert pos_id is not None
        assert 'NVDA' in pos_id
        
        # Check position exists
        positions = [p for p in manager.positions['positions'] if p['status'] == 'OPEN']
        assert len(positions) == 1
    
    def test_risk_calculation(self, manager):
        manager.add_position('TEST', 100, 50.0, 45.0, 60.0)
        
        # Risk should be (50-45) * 100 = 500
        positions = [p for p in manager.positions['positions'] if p['ticker'] == 'TEST']
        assert positions[0]['total_risk'] == 500.0
    
    def test_close_position(self, manager):
        manager.add_position('TEST', 100, 50.0, 45.0, 60.0)
        
        result = manager.close_position('TEST', 55.0, 'Manual exit')
        
        assert result is not None
        assert result['pnl'] == 500.0  # (55-50) * 100
        assert result['pnl_pct'] == 10.0
    
    def test_risk_summary(self, manager):
        manager.add_position('TEST1', 100, 50.0, 45.0, 60.0)
        manager.add_position('TEST2', 50, 100.0, 90.0, 120.0)
        
        # Note: get_risk_summary fetches live prices, so we can't test exact values
        # Just verify structure
        summary = manager.get_risk_summary()
        
        assert 'position_count' in summary
        assert 'total_risk' in summary
        assert 'risk_pct_of_account' in summary


class TestExtensionFilter:
    """Test that extension filter works correctly."""
    
    def test_extension_config_exists(self):
        from alpha_lab.config import get_config
        
        reject = get_config('extension.hard_reject_5d')
        assert reject == 20  # Default should be 20%
    
    def test_penalty_thresholds(self):
        from alpha_lab.config import get_config
        
        high = get_config('extension.penalty_threshold_high')
        mid = get_config('extension.penalty_threshold_mid')
        low = get_config('extension.penalty_threshold_low')
        
        # Should be in descending order
        assert high > mid > low


if __name__ == "__main__":
    pytest.main([__file__, '-v'])

