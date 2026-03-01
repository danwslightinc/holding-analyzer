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
        from yahooquery import Ticker
        t = Ticker(symbols, asynchronous=True)
        # Fetch 1 year of data for all tickers at once
        all_hist = t.history(period='1y')
        
        if all_hist.empty:
            print("No history data returned from Yahoo Finance")
            return {}

        for symbol in symbols:
            try:
                # Handle MultiIndex or single index correctly
                if isinstance(all_hist.index, pd.MultiIndex):
                    if symbol not in all_hist.index.levels[0]:
                        results[symbol] = {}
                        continue
                    hist = all_hist.xs(symbol)
                else:
                    if len(symbols) > 1: continue
                    hist = all_hist
                
                if hist.empty:
                    results[symbol] = {}
                    continue
                    
                current_price = hist['close'].iloc[-1]
                
                results[symbol] = {}
                for tf in timeframes:
                    if tf == '1d' and len(hist) > 1:
                        start_price = hist['close'].iloc[-2]
                        change_value = current_price - start_price
                        change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                        results[symbol][tf] = {
                            'change_pct': round(change_pct, 2),
                            'change_value': round(change_value, 2),
                            'current_price': round(current_price, 2),
                            'start_price': round(start_price, 2)
                        }
                        continue

                    days = timeframe_map.get(tf, 30)
                    target_date = now - timedelta(days=days)
                    
                    # Convert to pd.Timestamp for comparison with index
                    if not isinstance(hist.index, pd.DatetimeIndex):
                        hist.index = pd.to_datetime(hist.index)
                        
                    target_ts = pd.Timestamp(target_date)
                    if getattr(hist.index, 'tz', None) is not None:
                        target_ts = target_ts.tz_localize(hist.index.tz)
                    
                    hist_filtered = hist[hist.index >= target_ts]
                    
                    if not hist_filtered.empty:
                        start_price = hist_filtered['close'].iloc[0]
                        change_value = current_price - start_price
                        change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                        
                        results[symbol][tf] = {
                            'change_pct': round(change_pct, 2),
                            'change_value': round(change_value, 2),
                            'current_price': round(current_price, 2),
                            'start_price': round(start_price, 2)
                        }
                    else:
                        results[symbol][tf] = {
                            'change_pct': 0, 'change_value': 0,
                            'current_price': round(current_price, 2),
                            'start_price': round(current_price, 2)
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
