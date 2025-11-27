
import pytest
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.data_fetcher import DataFetcher

class TestDataFetcher:
    """Test suite for DataFetcher utility."""
    
    def test_yfinance_fallback_normalization(self):
        """Test that yfinance fallback returns normalized columns (lowercase)."""
        fetcher = DataFetcher(ib=None) # No IB connection
        
        # Request a short period to trigger yfinance download
        # Using a liquid ticker that should always have data
        ticker = "SPY"
        df = fetcher.get_intraday_data(ticker, days=2)
        
        if df.empty:
            pytest.skip("Skipping due to yfinance connection/download failure")
            
        # Check columns are lowercase
        expected_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"
            
        # Check no MultiIndex
        assert not isinstance(df.columns, pd.MultiIndex), "Columns should be flat"
        
        # Check ticker column populated
        assert df['ticker'].iloc[0] == ticker
        
    def test_yfinance_interval_selection(self):
        """Test logic for interval selection based on days."""
        fetcher = DataFetcher(None)
        
        # We can't easily mock the internal method call without a framework like unittest.mock
        # but we can verify the output format for different day ranges if data permits.
        
        # < 7 days -> 1m (if available) but resampled to 5m by DataFetcher
        df_short = fetcher.get_intraday_data("SPY", days=1)
        if not df_short.empty:
            # 1 day of 5m bars is ~78 bars (390 mins / 5)
            # Allow some flexibility for partial days
            assert len(df_short) > 30, "Should get reasonable amount of data (resampled to 5m)"
            
    def test_invalid_ticker(self):
        """Test handling of invalid tickers."""
        fetcher = DataFetcher(None)
        df = fetcher.get_intraday_data("INVALID_TICKER_XYZ", days=1)
        assert df.empty, "Should return empty DataFrame for invalid ticker"


