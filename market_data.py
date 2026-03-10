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

def get_current_prices(symbols):
    return get_current_prices_av(symbols)

def get_weekly_changes(symbols):
    # We fallback to daily for AV because weekly requires a different API hit 
    # doing TIME_SERIES_WEEKLY for 15+ symbols would destroy our free tier allowance.
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

def get_market_indices_change():
    # AV does not support index lookups like ^GSPC natively on the free tier properly
    # We will return static 0 or simple bypass to avoid eating 3 extra API requests per day
    return {'🇺🇸 S&P 500': 0.0, '🇺🇸 NASDAQ': 0.0, '🇨🇦 TSX': 0.0}

def get_technical_data(symbols):
    return get_technical_data_av(symbols)

def get_latest_news(symbols):
    return get_latest_news_av(symbols)

def get_dividend_calendar(symbols):
    return get_dividend_calendar_av(symbols)

def get_fundamental_data(symbols):
    return get_fundamental_data_av(symbols)

def get_portfolio_history(holdings_df):
    return get_portfolio_history_av(holdings_df)

