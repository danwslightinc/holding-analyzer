from backend.alpha_vantage import (
    get_current_prices_av,
    get_daily_changes_av,
    get_technical_data_av,
    get_latest_news_av,
    get_fundamental_data_av,
    get_dividend_calendar_av,
    get_portfolio_history_av
)
from backend.cache import cache_result, fx_cache
import pandas as pd

# ETF Look-Through Weights (Approximate)
ETF_SECTOR_WEIGHTS = {
    'VOO': {
        'Technology': 0.31, 'Financial Services': 0.13, 'Healthcare': 0.12, 
        'Consumer Cyclical': 0.10, 'Communication Services': 0.09, 'Industrials': 0.08, 
        'Consumer Defensive': 0.06, 'Energy': 0.04, 'Real Estate': 0.02, 'Basic Materials': 0.02, 'Utilities': 0.03
    },
    'XQQ.TO': {
        'Technology': 0.51, 'Communication Services': 0.16, 'Consumer Cyclical': 0.13, 
        'Healthcare': 0.06, 'Consumer Defensive': 0.04, 'Industrials': 0.04, 'Utilities': 0.01,
        'Financial Services': 0.01
    },
    'XIU.TO': {
        'Financial Services': 0.35, 'Energy': 0.18, 'Industrials': 0.12, 
        'Basic Materials': 0.12, 'Technology': 0.09, 'Utilities': 0.05, 
        'Communication Services': 0.05, 'Consumer Defensive': 0.03, 'Consumer Cyclical': 0.01
    },
    'XEI.TO': {
        'Energy': 0.30, 'Financial Services': 0.30, 'Utilities': 0.15, 
        'Communication Services': 0.10, 'Real Estate': 0.05, 'Basic Materials': 0.05, 'Industrials': 0.05
    },
    'VDY.TO': {
        'Financial Services': 0.56, 'Energy': 0.20, 'Utilities': 0.09, 
        'Communication Services': 0.07, 'Industrials': 0.03, 'Basic Materials': 0.02, 
        'Consumer Defensive': 0.02, 'Consumer Cyclical': 0.01
    },
    'QQQ': {
        'Technology': 0.51, 'Communication Services': 0.16, 'Consumer Cyclical': 0.13, 
        'Healthcare': 0.06, 'Consumer Defensive': 0.04, 'Industrials': 0.04, 'Utilities': 0.01,
        'Financial Services': 0.01
    },
    'AVUV': {
        'Financial Services': 0.26, 'Consumer Cyclical': 0.18, 'Industrials': 0.17, 
        'Energy': 0.16, 'Technology': 0.06, 'Basic Materials': 0.06, 
        'Consumer Defensive': 0.04, 'Healthcare': 0.03, 'Communication Services': 0.02, 
        'Real Estate': 0.01, 'Utilities': 0.01
    }
}

def find_purchase_date_from_price(symbol, purchase_price, tolerance=0.05, min_days_ago=30):
    # AV makes it difficult to easily scan history for a target price date in an efficient way 
    # compared to yfinance ticker history without eating our daily 25-req allowance on TIME_SERIES_DAILY
    return None

from yfinance_weekly import get_prices_yq
import os

def get_current_prices(symbols):
    # If running in email context, prefer Yahoo Finance to save AV quota
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true":
        print("Using Yahoo Finance to fetch current prices (Email Mode)...")
        prices = get_prices_yq(symbols)
        # Fall back to AV if YF completely fails (returns 0s)
        if not any(prices.values()):
            print("YF failed, falling back to Alpha Vantage.")
            return get_current_prices_av(symbols)
        return prices
    return get_current_prices_av(symbols)

from yfinance_weekly import get_weekly_changes_yq

def get_weekly_changes(symbols):
    # For email reporting, we want to try Yahoo Finance first to save AV quota
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true":
        print("Fetching weekly changes using yfinance to save quota...")
        prices = get_weekly_changes_yq(symbols)
        if not any(prices.values()):
            return get_daily_changes_av(symbols)
        return prices
    return get_daily_changes_av(symbols)

def get_daily_changes(symbols):
    return get_daily_changes_av(symbols)

@cache_result(fx_cache)
def get_usd_to_cad_rate():
    try:
        prices = get_current_prices(['CAD=X'])
        rate = prices.get('CAD=X', 0.0)
        if rate and rate > 1.0:
            return float(rate)
        return 1.40
    except Exception:
        return 1.40

from yfinance_weekly import get_indices_changes_yq
def get_market_indices_change():
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true":
        print("Fetching market indices using yfinance...")
        return get_indices_changes_yq()
    return {'🇺🇸 S&P 500': 0.0, '🇺🇸 NASDAQ': 0.0, '🇨🇦 TSX': 0.0}

from yfinance_weekly import (
    get_technical_data_yq,
    get_latest_news_yq,
    get_dividend_calendar_yq,
    get_fundamental_data_yq,
    get_portfolio_history_yq
)

def get_technical_data(symbols):
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true": return get_technical_data_yq(symbols)
    return get_technical_data_av(symbols)

def get_latest_news(symbols):
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true": return get_latest_news_yq(symbols)
    return get_latest_news_av(symbols)

def get_dividend_calendar(symbols):
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true": return get_dividend_calendar_yq(symbols)
    return get_dividend_calendar_av(symbols)

def get_fundamental_data(symbols):
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true": return get_fundamental_data_yq(symbols)
    return get_fundamental_data_av(symbols)

def get_portfolio_history(holdings_df):
    if os.environ.get("USE_YFINANCE_FOR_EMAIL") == "true": return get_portfolio_history_yq(holdings_df)
    return get_portfolio_history_av(holdings_df)

