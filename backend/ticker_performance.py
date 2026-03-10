from backend.alpha_vantage import fetch_av_data
from datetime import datetime, timedelta
import pandas as pd
import time

_performance_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 86400  # AV approach caches for 24 hours globally
}

def get_ticker_performance(symbols, timeframes=['1d', '1w', '1m', '3m', '6m', 'YTD', '1y']):
    current_time = time.time()
    if _performance_cache['data'] is not None and (current_time - _performance_cache['timestamp']) < _performance_cache['ttl']:
        return _performance_cache['data']
        
    print(f"Fetching Alpha Vantage performance data for {len(symbols)} symbols...")
    results = {}
    
    now = datetime.now()
    timeframe_map = {
        '1d': 1, '1w': 7, '1m': 30, '3m': 90, '6m': 180, '1y': 365,
        'YTD': (now - datetime(now.year, 1, 1)).days
    }
    
    for symbol in symbols:
        results[symbol] = {}
        ts_data = fetch_av_data("TIME_SERIES_DAILY", symbol, outputsize="full")
        
        try:
            time_series = ts_data.get("Time Series (Daily)", {})
            if not time_series:
                continue
                
            dates = sorted(list(time_series.keys()))
            hist = pd.Series([float(time_series[d]['4. close']) for d in dates], index=pd.to_datetime(dates)).sort_index()
            # Force to UTC for timezone checks
            hist.index = pd.to_datetime(hist.index, utc=True)
            
            if hist.empty:
                continue
                
            current_price = hist.iloc[-1]
            
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
            print(f"Error processing AV performance for {symbol}: {e}")
            pass
            
    _performance_cache['data'] = results
    _performance_cache['timestamp'] = time.time()
    
    return results
