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
    # Prefer Yahoo Finance to save AV quota (25 req/day limit is very strict)
    print("Fetching current prices using Yahoo Finance...")
    prices = get_prices_yq(symbols)
    
    # Identify symbols that YF failed to get (returned 0.0)
    failed_symbols = [s for s, p in prices.items() if p == 0.0]
    if failed_symbols:
        print(f"YF failed for {len(failed_symbols)} symbols, falling back to Alpha Vantage for these: {failed_symbols}")
        av_prices = get_current_prices_av(failed_symbols)
        prices.update(av_prices)
    
    return prices

from yfinance_weekly import (
    get_prices_yq,
    get_weekly_changes_yq,
    get_daily_changes_yq,
    get_indices_changes_yq,
    get_technical_data_yq,
    get_latest_news_yq,
    get_dividend_calendar_yq,
    get_fundamental_data_yq,
    get_portfolio_history_yq
)
import os

def get_weekly_changes(symbols):
    # Prefer Yahoo Finance
    print("Fetching weekly changes using yfinance to save quota...")
    changes = get_weekly_changes_yq(symbols)
    
    # Robust check if we got any valid non-zero changes
    def has_valid_changes(c_dict):
        for v in c_dict.values():
            try:
                # Handle if v is a Series/array
                val = float(v.iloc[0]) if hasattr(v, 'iloc') and isinstance(v, pd.Series) else float(v)
                if val != 0.0: return True
            except: continue
        return False

    if not has_valid_changes(changes):
        return get_daily_changes_av(symbols)
    return changes

def get_daily_changes(symbols):
    # Daily changes for dashboard - try YF first
    print("Fetching daily changes using yfinance...")
    changes = get_daily_changes_yq(symbols)
    
    # Identify failures
    def is_failed(sym):
        if sym not in changes: return True
        val = changes[sym]
        # Handle if val is a Series/array
        if hasattr(val, 'iloc') or isinstance(val, (list, np.ndarray)):
            try:
                # Use .any() or just check the first element
                val = float(val.iloc[0]) if hasattr(val, 'iloc') else float(val[0])
            except:
                return True
        return float(val) == 0.0

    failed = [s for s in symbols if is_failed(s)]
    if failed:
        print(f"YF failed for daily changes of {len(failed)} symbols, falling back to AV.")
        av_changes = get_daily_changes_av(failed)
        changes.update(av_changes)
        
    return changes

@cache_result(fx_cache)
def get_usd_to_cad_rate():
    try:
        # Use YF for exchange rate as it's very reliable and saves 1 AV call
        prices = get_prices_yq(['CAD=X'])
        rate = prices.get('CAD=X', 0.0)
        if rate and rate > 1.0:
            return float(rate)
        # Fallback to AV
        av_prices = get_current_prices_av(['CAD=X'])
        rate = av_prices.get('CAD=X', 0.0)
        if rate and rate > 1.0:
            return float(rate)
        return 1.40
    except Exception:
        return 1.40

def get_market_indices_change():
    print("Fetching market indices using yfinance...")
    return get_indices_changes_yq()

def get_technical_data(symbols):
    print("Fetching technical data using yfinance...")
    data = get_technical_data_yq(symbols)
    # Technical data is optional-ish, if YF fails we can try AV for a few
    return data

def get_latest_news(symbols):
    print("Fetching latest news using yfinance...")
    return get_latest_news_yq(symbols)

def get_dividend_calendar(symbols):
    print("Fetching dividend calendar using yfinance...")
    data = get_dividend_calendar_yq(symbols)
    # Fallback to AV if empty (AV provides OVERVIEW for US stocks)
    missing = [s for s in symbols if s not in data]
    if missing:
        print(f"Dividends missing for {len(missing)} symbols, trying Alpha Vantage fallback.")
        av_data = get_dividend_calendar_av(missing)
        data.update(av_data)
    return data

CUSTOM_SECTOR_MAPPINGS = {
    'VOO': 'US Broad Market', 'XQQ.TO': 'US Technology', 'XEI.TO': 'Canadian Dividends',
    'XIU.TO': 'Canadian Broad Market', 'XEF.TO': 'International Developed', 'XEC.TO': 'Emerging Markets',
    'SLV': 'Commodities', 'GLD': 'Commodities', 'BTC-USD': 'Crypto', 'ETH-USD': 'Crypto',
    'CAD=X': 'Currency', 'CASH.TO': 'Cash & Equivalents', 'NVDA': 'Technology',
    'MSFT': 'Technology', 'CRM': 'Technology', 'COST': 'Consumer Defensive',
    'V': 'Financial Services', 'UNH': 'Healthcare', 'TD.TO': 'Financial Services',
    'CM.TO': 'Financial Services', 'AC.TO': 'Industrials', 'WCP.TO': 'Energy', 'VDY.TO': 'Canadian Dividends',
    'AVUV': 'US Small Cap Value', 'JPST': 'Short-Term Fixed Income',
    'QQQ': 'US Technology', 'XQQ': 'US Technology', 'SMH': 'US Semiconductors'
}

def get_fundamental_data(symbols):
    print("Fetching fundamental data...")
    results = {}
    remaining_symbols = []
    
    # Check custom mappings first (saves API calls)
    for sym in symbols:
        if sym in CUSTOM_SECTOR_MAPPINGS:
            results[sym] = {'Sector': CUSTOM_SECTOR_MAPPINGS[sym]}
        else:
            remaining_symbols.append(sym)
            
    if not remaining_symbols:
        return results
        
    # Try YF for the rest
    print(f"Fetching fundamental data using yfinance for {len(remaining_symbols)} symbols...")
    yf_data = get_fundamental_data_yq(remaining_symbols)
    results.update(yf_data)
    
    # Check for missing sectors in YF results
    missing = [s for s in remaining_symbols if results.get(s, {}).get('Sector') == 'Unknown']
    if missing:
        print(f"Fundamentals missing for {len(missing)} symbols, trying Alpha Vantage fallback.")
        av_data = get_fundamental_data_av(missing)
        results.update(av_data)
        
    return results

def get_portfolio_history(holdings_df):
    print("Fetching portfolio history using yfinance (much faster/unlimited)...")
    return get_portfolio_history_yq(holdings_df)

