import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlmodel import Session
from backend.models import MarketDataCache, UserSettings
from backend.alpha_vantage import fetch_av_data, get_fundamental_data_av

@pytest.fixture
def mock_db_session():
    session = MagicMock(spec=Session)
    return session

@pytest.fixture
def mock_cache_hit():
    cache = MarketDataCache(
        endpoint="GLOBAL_QUOTE",
        symbol="AAPL",
        data=json.dumps({"Global Quote": {"05. price": "150.0"}}),
        updated_at=datetime.utcnow()
    )
    return cache

@patch("backend.alpha_vantage.get_session")
@patch("backend.alpha_vantage.get_api_key")
@patch("requests.get")
def test_fetch_av_data_no_key_no_cache(mock_get, mock_get_api_key, mock_get_session, mock_db_session):
    # Setup: No API key (demo mode) and No cache in DB
    mock_get_api_key.return_value = "demo"
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_db_session.exec.return_value.first.return_value = None
    
    result = fetch_av_data("GLOBAL_QUOTE", "AAPL")
    
    # Assert: Should not call requests.get and return empty dict
    assert result == {}
    mock_get.assert_not_called()

@patch("backend.alpha_vantage.get_session")
@patch("backend.alpha_vantage.get_api_key")
@patch("requests.get")
def test_fetch_av_data_no_key_with_expired_cache(mock_get, mock_get_api_key, mock_get_session, mock_db_session, mock_cache_hit):
    # Setup: No API key (demo mode) but Cache exists and is expired
    mock_get_api_key.return_value = "demo"
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    # Make cache expired (e.g., 2 days old)
    mock_cache_hit.updated_at = datetime.utcnow() - timedelta(days=2)
    mock_db_session.exec.return_value.first.return_value = mock_cache_hit
    
    result = fetch_av_data("GLOBAL_QUOTE", "AAPL")
    
    # Assert: Should return the expired cache and NOT call requests.get
    assert result == json.loads(mock_cache_hit.data)
    mock_get.assert_not_called()

@patch("backend.alpha_vantage.get_session")
@patch("backend.alpha_vantage.get_api_key")
@patch("requests.get")
def test_fetch_av_data_with_valid_key_and_expired_cache(mock_get, mock_get_api_key, mock_get_session, mock_db_session, mock_cache_hit):
    # Setup: Valid API key and Expired cache
    mock_get_api_key.return_value = "REAL_KEY"
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_cache_hit.updated_at = datetime.utcnow() - timedelta(days=2)
    mock_db_session.exec.return_value.first.return_value = mock_cache_hit
    
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"Global Quote": {"05. price": "160.0"}}
    mock_get.return_value = mock_response
    
    # Patch time.sleep to speed up tests
    with patch("time.sleep"):
        result = fetch_av_data("GLOBAL_QUOTE", "AAPL")
    
    # Assert: Should fetch fresh data from API
    assert result == {"Global Quote": {"05. price": "160.0"}}
    mock_get.assert_called_once()
    assert mock_db_session.commit.called

@patch("backend.alpha_vantage.get_session")
@patch("backend.alpha_vantage.get_api_key")
@patch("requests.get")
def test_fetch_av_data_prevents_caching_info_payloads(mock_get, mock_get_api_key, mock_get_session, mock_db_session):
    # Setup: Valid key, no cache, but API returns "Information" (Rate limit)
    mock_get_api_key.return_value = "REAL_KEY"
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_db_session.exec.return_value.first.return_value = None
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"Information": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day..."}
    mock_get.return_value = mock_response
    
    result = fetch_av_data("GLOBAL_QUOTE", "AAPL")
    
    # Assert: Should NOT call db_session.add or commit
    assert result == {}
    assert not mock_db_session.add.called
    assert not mock_db_session.commit.called

def test_get_fundamental_data_av_sector_mapping():
    # Test that ETFs are mapped to custom sectors without calling fetch_av_data
    with patch("backend.alpha_vantage.fetch_av_data") as mock_fetch:
        symbols = ["VOO", "NVDA", "AAPL"]
        # VOO is hardcoded, NVDA is hardcoded, AAPL is NOT hardcoded
        
        # Mock what it returns for non-hardcoded symbols
        mock_fetch.return_value = {"Symbol": "AAPL", "Sector": "Technology"}
        
        result = get_fundamental_data_av(symbols)
        
        assert result["VOO"]["Sector"] == "US Broad Market"
        assert result["NVDA"]["Sector"] == "Technology"
        # AAPL was fetched
        mock_fetch.assert_called_with("OVERVIEW", "AAPL")
        assert result["AAPL"]["Sector"] == "Technology"
        
        # VOO and NVDA should NOT have triggered an OVERVIEW fetch
        # But wait, NVDA is in custom_sectors in the current code (as of my last edit)
        # Check custom_sectors in alpha_vantage.py: NVDA is indeed there
        assert mock_fetch.call_count == 1 # Only AAPL

from backend.database import get_processed_database_url

def test_database_url_processing():
    # Test Supabase hostname preservation and sslmode addition
    with patch("os.getenv") as mock_env:
        mock_env.return_value = "postgres://user:pass@db.xyz.supabase.co:5432/postgres"
        url = get_processed_database_url()
        assert "postgresql://" in url
        assert "db.xyz.supabase.co" in url
        assert "sslmode=require" in url

    # Test SQLite default
    with patch("os.getenv") as mock_env:
        mock_env.return_value = "sqlite:///./test.db"
        url = get_processed_database_url()
        assert url == "sqlite:///./test.db"
