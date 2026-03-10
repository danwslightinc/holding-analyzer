"""
Get per-ticker performance over various timeframes using Yahoo Finance
"""
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from functools import lru_cache
import time

# Simple cache with timestamp
_performance_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 300  # Cache for 5 minutes
}

def get_ticker_performance(symbols, timeframes=['1d', '1w', '1m', '3m', '6m', 'YTD', '1y']):
    """
    Get performance data for each ticker over multiple timeframes
    Uses in-memory caching to avoid repeated Yahoo Finance calls
    
    Args:
        symbols: List of ticker symbols
        timeframes: List of timeframe strings
        
    Returns:
        Dict with structure: {symbol: {timeframe: {change_pct, change_value, current_price}}}
    """
    # Check cache
    current_time = time.time()
    if _performance_cache['data'] is not None and (current_time - _performance_cache['timestamp']) < _performance_cache['ttl']:
        print("Using cached ticker performance data")
        return _performance_cache['data']
    
    print(f"Fetching fresh ticker performance data from Yahoo Finance for {len(symbols)} symbols...")
    results = {}
    
    # Map timeframes to days
    now = datetime.now()
    timeframe_map = {
        '1d': 1,
        '1w': 7,
        '1m': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365,
        'YTD': (now - datetime(now.year, 1, 1)).days
    }
    
    try:
        from market_data import get_yf_session
        session = get_yf_session()
        
        # Fetch 1 year of data for all tickers at once using yfinance
        all_hist = yf.download(symbols, period='1y', progress=False, threads=True)
        
        if all_hist.empty:
            print("No history data returned from Yahoo Finance")
            return {}

        close_data = all_hist['Close']

        for symbol in symbols:
            try:
                # Handle single vs multi symbol downloaded data
                if len(symbols) == 1:
                    hist = close_data.dropna()
                else:
                    if symbol not in close_data.columns:
                        results[symbol] = {}
                        continue
                    hist = close_data[symbol].dropna()
                
                if hist.empty:
                    results[symbol] = {}
                    continue
                    
                current_price = hist.iloc[-1]
                
                # Make sure the index is explicitly DateTimeIndex and UTC to avoid mixed timezone errors
                if not isinstance(hist.index, pd.DatetimeIndex):
                    hist.index = pd.to_datetime(hist.index, utc=True)
                elif hist.index.tz is None:
                    hist.index = hist.index.tz_localize('UTC')
                else:
                    hist.index = hist.index.tz_convert('UTC')
                
                results[symbol] = {}
                for tf in timeframes:
                    if tf == '1d' and len(hist) > 1:
                        start_price = hist.iloc[-2]
                        change_value = current_price - start_price
                        change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                        results[symbol][tf] = {
                            'change_pct': round(change_pct, 2),
                            'change_value': round(change_value, 2),
                            'current_price': round(float(current_price), 2),
                            'start_price': round(float(start_price), 2)
                        }
                        continue

                    days = timeframe_map.get(tf, 30)
                    target_date = now - timedelta(days=days)
                    
                    target_ts = pd.Timestamp(target_date).tz_localize('UTC')
                    
                    hist_filtered = hist[hist.index >= target_ts]
                    
                    if not hist_filtered.empty:
                        start_price = hist_filtered.iloc[0]
                        change_value = current_price - start_price
                        change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                        
                        results[symbol][tf] = {
                            'change_pct': round(change_pct, 2),
                            'change_value': round(change_value, 2),
                            'current_price': round(float(current_price), 2),
                            'start_price': round(float(start_price), 2)
                        }
                    else:
                        results[symbol][tf] = {
                            'change_pct': 0, 'change_value': 0,
                            'current_price': round(float(current_price), 2),
                            'start_price': round(float(current_price), 2)
                        }
            except Exception as e:
                print(f"Error processing performance for {symbol}: {e}")
                results[symbol] = {}
                
    except Exception as e:
        print(f"Error fetching batch performance: {e}")
        return {}
    
    # Update cache
    _performance_cache['data'] = results
    _performance_cache['timestamp'] = time.time()
    print(f"Cached ticker performance data for {len(results)} symbols")
            
    return results
