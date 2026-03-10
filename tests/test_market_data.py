from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest

from market_data import get_current_prices, get_technical_data, get_weekly_changes, get_usd_to_cad_rate

@patch('market_data.yf.download')
def test_get_current_prices_single_symbol(mock_download):
    # Mock yf.download return value for a single symbol
    mock_df = pd.DataFrame({'Close': [150.0]}, index=['2026-03-09'])
    mock_download.return_value = mock_df

    prices = get_current_prices(['AAPL'])
    
    assert prices == {'AAPL': 150.0}
    mock_download.assert_called_once()

@patch('market_data.yf.download')
def test_get_current_prices_multiple_symbols(mock_download):
    # Mock yf.download return value for multiple symbols (MultiIndex-like structures)
    # yfinance returns a dataframe where columns are (PriceType, Ticker) when passing multiple symbols
    # But market_data's yfinance concurrent fallback handles standard multi-symbol returns gracefully via 'Close'[sym]
    
    data = {'AAPL': [150.0], 'MSFT': [400.0]}
    df_close = pd.DataFrame(data, index=['2026-03-09'])
    
    # yfinance multi-ticker download returns MultiIndex columns (Price, Ticker)
    columns = pd.MultiIndex.from_tuples([('Close', 'AAPL'), ('Close', 'MSFT')])
    mock_df = pd.DataFrame([[150.0, 400.0]], index=['2026-03-09'], columns=columns)
    mock_download.return_value = mock_df

    prices = get_current_prices(['AAPL', 'MSFT'])
    
    assert prices == {'AAPL': 150.0, 'MSFT': 400.0}

@patch('market_data.get_current_prices')
def test_get_usd_to_cad_rate(mock_prices):
    from market_data import fx_cache
    fx_cache.clear()
    
    # Test valid return > 1.0
    mock_prices.return_value = {'CAD=X': 1.35}
    assert get_usd_to_cad_rate() == 1.35
    
    fx_cache.clear()
    # Test fallback behavior when data is missing or invalid
    mock_prices.return_value = {'CAD=X': 0.0}
    assert get_usd_to_cad_rate() == 1.40
    
    fx_cache.clear()
    mock_prices.return_value = {}
    assert get_usd_to_cad_rate() == 1.40

@patch('market_data.yf.download')
def test_get_weekly_changes(mock_download):
    # Mocking data for start and end week
    columns = pd.MultiIndex.from_tuples([('Close', 'AAPL'), ('Close', 'MSFT')])
    mock_df = pd.DataFrame([
        [100.0, 200.0],
        [110.0, 190.0]
    ], columns=columns)
    mock_download.return_value = mock_df

    changes = get_weekly_changes(['AAPL', 'MSFT'])
    
    # AAPL went 100 -> 110 (+10%)
    # MSFT went 200 -> 190 (-5%)
    assert changes['AAPL'] == 0.10
    assert changes['MSFT'] == -0.05
