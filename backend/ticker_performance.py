from yfinance_weekly import get_yq_ticker
from datetime import datetime, timedelta
import pandas as pd
import time
import numpy as np

_performance_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 86400  # Cache for 24 hours
}

def get_ticker_performance(symbols, timeframes=['1d', '1w', '1m', '3m', '6m', 'YTD', '1y']):
    current_time = time.time()
    if _performance_cache['data'] is not None and (current_time - _performance_cache['timestamp']) < _performance_cache['ttl']:
        # Filter for requested symbols if cache has more
        return {s: _performance_cache['data'][s] for s in symbols if s in _performance_cache['data']}
        
    print(f"Fetching Yahoo Finance performance data for {len(symbols)} symbols...")
    results = {}
    
    now = datetime.now()
    timeframe_map = {
        '1d': 1, '1w': 7, '1m': 30, '3m': 90, '6m': 180, '1y': 365,
        'YTD': (now - datetime(now.year, 1, 1)).days
    }
    
    try:
        t = get_yq_ticker(symbols)
        # Fetch 2 years to be safe for 1y calculations
        hist = t.history(period="2y")
        if hist.empty: return {}

        # Normalize the DataFrame: Handle MultiIndex by resetting and converting to unified datetime
        is_multi = isinstance(hist.index, pd.MultiIndex)
        hist = hist.reset_index()
        
        if 'date' in hist.columns:
            hist['date'] = pd.to_datetime(hist['date']).dt.tz_localize(None)
        
        for symbol in symbols:
            results[symbol] = {}
            try:
                if is_multi and 'symbol' in hist.columns:
                    sym_hist = hist[hist['symbol'] == symbol].copy()
                else:
                    sym_hist = hist.copy()
                
                if sym_hist.empty or 'close' not in sym_hist.columns:
                    continue
                    
                # Use 'date' as index and ensure it's sorted
                sym_hist = sym_hist.set_index('date').sort_index()
                sym_hist = sym_hist['close'].dropna()
                
                if sym_hist.empty:
                    continue
                
                current_price = float(sym_hist.iloc[-1])
                
                for tf in timeframes:
                    if tf == '1d' and len(sym_hist) > 1:
                        start_price = float(sym_hist.iloc[-2])
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
                    # Create a naive Timestamp for comparison
                    target_ts = pd.Timestamp(target_date).replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Find closest date
                    hist_filtered = sym_hist[sym_hist.index >= target_ts]
                    
                    if not hist_filtered.empty:
                        start_price = float(hist_filtered.iloc[0])
                        change_value = current_price - start_price
                        change_pct = (change_value / start_price) * 100 if start_price > 0 else 0
                        
                        results[symbol][tf] = {
                            'change_pct': round(change_pct, 2),
                            'change_value': round(change_value, 2),
                            'current_price': round(current_price, 2),
                            'start_price': round(start_price, 2)
                        }
                    else:
                        results[symbol][tf] = {'change_pct': 0, 'change_value': 0, 'current_price': round(current_price, 2), 'start_price': round(current_price, 2)}
            except Exception as e:
                print(f"Error processing YF performance for {symbol}: {e}")
                
    except Exception as e:
        print(f"Failed to fetch YF performance: {e}")
            
    _performance_cache['data'] = results
    _performance_cache['timestamp'] = time.time()
    
    return results
