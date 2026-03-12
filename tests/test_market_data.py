import os
import pytest
from unittest.mock import patch

import market_data

@pytest.fixture(autouse=True)
def clean_env():
    # Make sure env var is clean before each test (though no longer strictly used for routing in new logic)
    if "USE_YFINANCE_FOR_EMAIL" in os.environ:
        del os.environ["USE_YFINANCE_FOR_EMAIL"]
    yield

@patch('market_data.get_current_prices_av')
@patch('market_data.get_prices_yq')
def test_get_current_prices_routing(mock_yq, mock_av):
    mock_yq.return_value = {'AAPL': 150.0}
    mock_av.return_value = {'AAPL': 155.0}

    # New Default: should map to Yahoo Finance (yq) first
    res = market_data.get_current_prices(['AAPL'])
    assert res == {'AAPL': 150.0}
    mock_yq.assert_called_once_with(['AAPL'])
    mock_av.assert_not_called()

@patch('market_data.get_current_prices_av')
@patch('market_data.get_prices_yq')
def test_get_current_prices_yq_fallback(mock_yq, mock_av):
    # Test fallback to AV if YQ completely fails / returns empties (all 0.0)
    mock_yq.return_value = {'AAPL': 0.0}
    mock_av.return_value = {'AAPL': 155.0}

    res = market_data.get_current_prices(['AAPL'])
    assert res == {'AAPL': 155.0}
    mock_yq.assert_called_once_with(['AAPL'])
    mock_av.assert_called_once_with(['AAPL'])


@patch('market_data.get_daily_changes_av')
@patch('market_data.get_weekly_changes_yq')
def test_get_weekly_changes_routing(mock_yq, mock_av):
    mock_yq.return_value = {'AAPL': 0.05}
    mock_av.return_value = {'AAPL': 0.02}

    # New Default: should map to Weekly YQ first
    res = market_data.get_weekly_changes(['AAPL'])
    assert res == {'AAPL': 0.05}
    mock_yq.assert_called_once()
    mock_av.assert_not_called()

@patch('market_data.get_indices_changes_yq')
def test_get_market_indices_change_routing(mock_yq):
    mock_yq.return_value = {'🇺🇸 S&P 500': 0.02}
    
    # New Default: should call yq
    res = market_data.get_market_indices_change()
    assert res == {'🇺🇸 S&P 500': 0.02}
    mock_yq.assert_called_once()


@pytest.mark.parametrize("function_name, av_patch, yq_patch, test_args", [
    ('get_technical_data', 'market_data.get_technical_data_av', 'market_data.get_technical_data_yq', (['AAPL'],)),
    ('get_latest_news', 'market_data.get_latest_news_av', 'market_data.get_latest_news_yq', (['AAPL'],)),
    ('get_portfolio_history', 'market_data.get_portfolio_history_av', 'market_data.get_portfolio_history_yq', (None,)),
])
def test_generic_method_routing(function_name, av_patch, yq_patch, test_args):
    with patch(av_patch) as mock_av, patch(yq_patch) as mock_yq:
        mock_av.return_value = "av_data"
        mock_yq.return_value = "yq_data"
        
        target_func = getattr(market_data, function_name)
        
        # New Default: should use yq
        res = target_func(*test_args)
        assert res == "yq_data"
        mock_yq.assert_called_once()

@patch('market_data.get_dividend_calendar_av')
@patch('market_data.get_dividend_calendar_yq')
def test_dividend_calendar_routing(mock_yq, mock_av):
    mock_yq.return_value = {'AAPL': {'Rate': 0.96}}
    mock_av.return_value = {'AAPL': {'Rate': 0.90}}
    
    res = market_data.get_dividend_calendar(['AAPL'])
    assert res == {'AAPL': {'Rate': 0.96}}
    mock_yq.assert_called_once()
    mock_av.assert_not_called()
    
    mock_yq.reset_mock()
    mock_av.reset_mock()
    
    # Test fallback if symbol missing in YQ
    mock_yq.return_value = {}
    res = market_data.get_dividend_calendar(['AAPL'])
    assert res == {'AAPL': {'Rate': 0.90}}
    mock_yq.assert_called_once()
    mock_av.assert_called_once()

@patch('market_data.get_fundamental_data_av')
@patch('market_data.get_fundamental_data_yq')
def test_fundamental_data_routing(mock_yq, mock_av):
    # Tests the new fundamental logic: Custom -> YQ -> AV fallback
    mock_yq.return_value = {'AAPL': {'Sector': 'Technology'}}
    mock_av.return_value = {'MSFT': {'Sector': 'Software'}}
    
    # 1. Custom mapping (VOO)
    res = market_data.get_fundamental_data(['VOO'])
    assert res['VOO']['Sector'] == 'US Broad Market'
    mock_yq.assert_not_called()
    mock_av.assert_not_called()
    
    # 2. YQ mapping
    res = market_data.get_fundamental_data(['AAPL'])
    assert res['AAPL']['Sector'] == 'Technology'
    mock_yq.assert_called_once()
    
    mock_yq.reset_mock()
    
    # 3. Fallback to AV if YQ gives Unknown
    mock_av.return_value = {'GOOGL': {'Sector': 'Communication Services'}}
    mock_yq.return_value = {'GOOGL': {'Sector': 'Unknown'}}
    res = market_data.get_fundamental_data(['GOOGL'])
    assert res['GOOGL']['Sector'] == 'Communication Services'
    mock_av.assert_called_once()
