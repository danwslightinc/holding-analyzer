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
    
    print("Fetching fresh ticker performance data from Yahoo Finance...")
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
    
    for symbol in symbols:
        try:
            results[symbol] = {}
            ticker = yf.Ticker(symbol)
            
            # Get max 1 year of data to cover all timeframes
            hist = ticker.history(period='1y')
            
            if hist.empty:
                continue
                
            current_price = hist['Close'].iloc[-1]
            
            for tf in timeframes:
                days = timeframe_map.get(tf, 30)
                
                # Get price from N days ago
                target_date = now - timedelta(days=days)
                
                # Make target_date timezone-aware to match hist.index
                if hasattr(hist.index, 'tz') and hist.index.tz is not None:
                    import pytz
                    target_date = pytz.UTC.localize(target_date.replace(tzinfo=None))
                
                # Find closest available date
                hist_filtered = hist[hist.index >= target_date]
                
                if len(hist_filtered) > 0:
                    start_price = hist_filtered['Close'].iloc[0]
                    change_value = current_price - start_price
                    change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                    
                    results[symbol][tf] = {
                        'change_pct': round(change_pct, 2),
                        'change_value': round(change_value, 2),
                        'current_price': round(current_price, 2),
                        'start_price': round(start_price, 2)
                    }
                else:
                    # Not enough data for this timeframe
                    results[symbol][tf] = {
                        'change_pct': 0,
                        'change_value': 0,
                        'current_price': round(current_price, 2),
                        'start_price': round(current_price, 2)
                    }
                    
        except Exception as e:
            print(f"Error fetching performance for {symbol}: {e}")
            results[symbol] = {}
    
    # Update cache
    _performance_cache['data'] = results
    _performance_cache['timestamp'] = time.time()
    print(f"Cached ticker performance data for {len(results)} symbols")
            
    return results
