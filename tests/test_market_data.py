import os
import pytest
from unittest.mock import patch

import market_data

@pytest.fixture(autouse=True)
def clean_env():
    # Make sure env var is clean before each test
    if "USE_YFINANCE_FOR_EMAIL" in os.environ:
        del os.environ["USE_YFINANCE_FOR_EMAIL"]
    yield
    if "USE_YFINANCE_FOR_EMAIL" in os.environ:
        del os.environ["USE_YFINANCE_FOR_EMAIL"]

@patch('market_data.get_current_prices_av')
@patch('market_data.get_prices_yq')
def test_get_current_prices_routing(mock_yq, mock_av):
    mock_yq.return_value = {'AAPL': 150.0}
    mock_av.return_value = {'AAPL': 155.0}

    # Default should map to Alpha Vantage
    res = market_data.get_current_prices(['AAPL'])
    assert res == {'AAPL': 155.0}
    mock_av.assert_called_once_with(['AAPL'])
    mock_yq.assert_not_called()

    mock_av.reset_mock()
    mock_yq.reset_mock()

    # With Yfinance Email mode should map to YahooQuery
    os.environ["USE_YFINANCE_FOR_EMAIL"] = "true"
    res = market_data.get_current_prices(['AAPL'])
    assert res == {'AAPL': 150.0}
    mock_yq.assert_called_once_with(['AAPL'])
    mock_av.assert_not_called()

@patch('market_data.get_current_prices_av')
@patch('market_data.get_prices_yq')
def test_get_current_prices_yq_fallback(mock_yq, mock_av):
    # Test fallback to AV if YQ completely fails / returns empties on Email mode
    mock_yq.return_value = {}  # YQ fails
    mock_av.return_value = {'AAPL': 155.0}

    os.environ["USE_YFINANCE_FOR_EMAIL"] = "true"
    res = market_data.get_current_prices(['AAPL'])
    assert res == {'AAPL': 155.0}
    mock_yq.assert_called_once_with(['AAPL'])
    mock_av.assert_called_once_with(['AAPL'])


@patch('market_data.get_daily_changes_av')
@patch('market_data.get_weekly_changes_yq')
def test_get_weekly_changes_routing(mock_yq, mock_av):
    mock_yq.return_value = {'AAPL': 0.05}
    mock_av.return_value = {'AAPL': 0.02}

    res = market_data.get_weekly_changes(['AAPL'])
    assert res == {'AAPL': 0.02}
    mock_av.assert_called_once()
    mock_yq.assert_not_called()

    mock_av.reset_mock()
    mock_yq.reset_mock()
    
    os.environ["USE_YFINANCE_FOR_EMAIL"] = "true"
    res = market_data.get_weekly_changes(['AAPL'])
    assert res == {'AAPL': 0.05}
    mock_yq.assert_called_once()
    mock_av.assert_not_called()


@patch('market_data.get_indices_changes_yq')
def test_get_market_indices_change_routing(mock_yq):
    mock_yq.return_value = {'🇺🇸 S&P 500': 0.02}
    
    res = market_data.get_market_indices_change()
    assert res == {'🇺🇸 S&P 500': 0.0, '🇺🇸 NASDAQ': 0.0, '🇨🇦 TSX': 0.0}
    mock_yq.assert_not_called()
    
    os.environ["USE_YFINANCE_FOR_EMAIL"] = "true"
    res = market_data.get_market_indices_change()
    assert res == {'🇺🇸 S&P 500': 0.02}
    mock_yq.assert_called_once()


@pytest.mark.parametrize("function_name, av_patch, yq_patch, test_args", [
    ('get_technical_data', 'market_data.get_technical_data_av', 'market_data.get_technical_data_yq', (['AAPL'],)),
    ('get_latest_news', 'market_data.get_latest_news_av', 'market_data.get_latest_news_yq', (['AAPL'],)),
    ('get_dividend_calendar', 'market_data.get_dividend_calendar_av', 'market_data.get_dividend_calendar_yq', (['AAPL'],)),
    ('get_fundamental_data', 'market_data.get_fundamental_data_av', 'market_data.get_fundamental_data_yq', (['AAPL'],)),
    ('get_portfolio_history', 'market_data.get_portfolio_history_av', 'market_data.get_portfolio_history_yq', (None,)),
])
def test_generic_method_routing(function_name, av_patch, yq_patch, test_args):
    with patch(av_patch) as mock_av, patch(yq_patch) as mock_yq:
        mock_av.return_value = "av_data"
        mock_yq.return_value = "yq_data"
        
        target_func = getattr(market_data, function_name)
        
        # Test Default flow
        res = target_func(*test_args)
        assert res == "av_data"
        mock_av.assert_called_once()
        mock_yq.assert_not_called()
        
        mock_av.reset_mock()
        mock_yq.reset_mock()
        
        # Test Email flow
        os.environ["USE_YFINANCE_FOR_EMAIL"] = "true"
        res = target_func(*test_args)
        assert res == "yq_data"
        mock_yq.assert_called_once()
        mock_av.assert_not_called()
