import yfinance as yf
from yahooquery import Ticker
import pandas as pd
import numpy as np

def get_yq_ticker(symbols):
    """ Helper to get robust Ticker object using curl_cffi and impersonation """
    try:
        from curl_cffi import requests
        session = requests.Session(impersonate="chrome110")
        return Ticker(symbols, session=session, timeout=10)
    except Exception as e:
        print(f"Warning: curl_cffi failed ({e}), falling back to direct Ticker")
        return Ticker(symbols, timeout=10)


def get_prices_yq(symbols):
    if not symbols: return {}

    prices = {}
    try:
        t = get_yq_ticker(symbols)
        price_data = t.price
        
        if price_data and isinstance(price_data, dict):
            for sym in symbols:
                sym_data = price_data.get(sym)
                if isinstance(sym_data, dict):
                    p = sym_data.get('regularMarketPrice')
                    if p is not None:
                        prices[sym] = float(p)
                        continue
                        
        missing_symbols = [s for s in symbols if s not in prices]
        if missing_symbols:
            try:
                data = yf.download(missing_symbols, period="1d", progress=False, threads=False)
                if not data.empty:
                    if len(missing_symbols) == 1:
                        try:
                            val = data['Close'].iloc[-1]
                            p = float(val.iloc[0]) if hasattr(val, 'iloc') and isinstance(val, pd.Series) else float(val)
                            if not np.isnan(p) and p > 0:
                                prices[missing_symbols[0]] = p
                        except: pass
                    else:
                        last_row = data['Close'].iloc[-1]
                        for sym in missing_symbols:
                            try:
                                p = float(last_row[sym])
                                if not np.isnan(p) and p > 0:
                                    prices[sym] = p
                            except: pass
            except Exception as yfe:
                pass

        for sym in symbols:
            if sym not in prices:
                prices[sym] = 0.0

        return prices

    except Exception as e:
        return {s: 0.0 for s in symbols}

def get_daily_changes_yq(symbols):
    if not symbols: return {}
    changes = {}
    try:
        t = get_yq_ticker(symbols)
        price_data = t.price
        if price_data and isinstance(price_data, dict):
            for sym in symbols:
                sym_data = price_data.get(sym)
                if isinstance(sym_data, dict):
                    # regularMarketChangePercent is usually e.g. 0.015 for 1.5%
                    c = sym_data.get('regularMarketChangePercent')
                    if c is not None:
                        # Return as decimal (0.015) not whole number (1.5)
                        changes[sym] = float(c)
                        continue
        
        missing = [s for s in symbols if s not in changes]
        if missing:
            # Fallback to period=2d to calculate manually
            for sym in missing:
                try:
                    df = yf.download(sym, period="2d", progress=False)
                    if not df.empty and len(df) >= 2:
                        p_val = df['Close'].iloc[-2]
                        c_val = df['Close'].iloc[-1]
                        
                        # Handle if yf.download returns a Series for these (multi-column)
                        prev = float(p_val.iloc[0]) if hasattr(p_val, 'iloc') and isinstance(p_val, pd.Series) else float(p_val)
                        curr = float(c_val.iloc[0]) if hasattr(c_val, 'iloc') and isinstance(c_val, pd.Series) else float(c_val)
                        
                        # Return as decimal (0.015) not whole number (1.5)
                        changes[sym] = (curr - prev) / prev
                except: pass
    except Exception: pass
    return changes

def get_weekly_changes_yq(symbols):
    if not symbols: return {}
    try:
        t = get_yq_ticker(symbols)
        # Increase period to 7d to ensure we get enough trading days even if today is NaN or it's a Monday
        hist = t.history(period="7d")
        if hist.empty: return {}
        
        is_multi = isinstance(hist.index, pd.MultiIndex)
        hist = hist.reset_index()
        if 'date' in hist.columns:
            hist['date'] = pd.to_datetime(hist['date']).dt.tz_localize(None)
        
        changes = {}
        for sym in symbols:
            try:
                if is_multi and 'symbol' in hist.columns:
                    sym_hist = hist[hist['symbol'] == sym].copy()
                else:
                    sym_hist = hist.copy()
                
                # Sort by date and DROP NaNs to avoid +nan%
                if 'date' in sym_hist.columns:
                    sym_hist = sym_hist.set_index('date').sort_index()
                
                if 'close' in sym_hist.columns:
                    sym_hist = sym_hist.dropna(subset=['close'])

                if len(sym_hist) >= 2:
                    s_val = sym_hist['close'].iloc[0]
                    e_val = sym_hist['close'].iloc[-1]
                    
                    # Handle potential MultiIndex/Series
                    start = float(s_val.iloc[0]) if hasattr(s_val, 'iloc') and isinstance(s_val, pd.Series) else float(s_val)
                    end = float(e_val.iloc[0]) if hasattr(e_val, 'iloc') and isinstance(e_val, pd.Series) else float(e_val)
                    
                    if start != 0:
                        changes[sym] = (end - start) / start
                    else:
                        changes[sym] = 0.0
                else:
                    changes[sym] = 0.0
            except:
                changes[sym] = 0.0
        return changes
    except Exception as e:
        return {}

def get_indices_changes_yq():
    indices = {'^GSPC': '🇺🇸 S&P 500', '^IXIC': '🇺🇸 NASDAQ', '^GSPTSE': '🇨🇦 TSX'}
    try:
        t = get_yq_ticker(list(indices.keys()))
        # Increase period to 7d
        hist = t.history(period="7d")
        if hist.empty: return {name: 0.0 for name in indices.values()}
        
        is_multi = isinstance(hist.index, pd.MultiIndex)
        hist = hist.reset_index()
        if 'date' in hist.columns:
            hist['date'] = pd.to_datetime(hist['date']).dt.tz_localize(None)

        changes = {}
        for symbol, name in indices.items():
            try:
                if is_multi and 'symbol' in hist.columns:
                    sym_hist = hist[hist['symbol'] == symbol].copy()
                else:
                    sym_hist = hist[hist['symbol'] == symbol].copy() if 'symbol' in hist.columns else hist.copy()
                
                if 'date' in sym_hist.columns:
                    sym_hist = sym_hist.set_index('date').sort_index()
                
                if 'close' in sym_hist.columns:
                    sym_hist = sym_hist.dropna(subset=['close'])

                if len(sym_hist) >= 2:
                    s_val = sym_hist['close'].iloc[0]
                    e_val = sym_hist['close'].iloc[-1]
                    
                    # Handle potential MultiIndex/Series
                    start = float(s_val.iloc[0]) if hasattr(s_val, 'iloc') and isinstance(s_val, pd.Series) else float(s_val)
                    end = float(e_val.iloc[0]) if hasattr(e_val, 'iloc') and isinstance(e_val, pd.Series) else float(e_val)
                    
                    if start != 0:
                        changes[name] = (end - start) / start
                    else:
                        changes[name] = 0.0
                else:
                    changes[name] = 0.0
            except:
                changes[name] = 0.0
        return changes
    except Exception as e:
        return {name: 0.0 for name in indices.values()}

from datetime import datetime, timedelta

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def get_technical_data_yq(symbols):
    if not symbols: return {}
    technical_data = {}
    try:
        t = get_yq_ticker(symbols)
        hist = t.history(period="1y")
        for sym in symbols:
            try:
                if isinstance(hist.index, pd.MultiIndex):
                    if sym not in hist.index.levels[0]:
                        technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                        continue
                    sym_hist = hist.xs(sym)
                else:
                    if len(symbols) > 1: continue
                    sym_hist = hist
                
                if sym_hist.empty or 'close' not in sym_hist.columns:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
                    
                series = sym_hist['close'].dropna()
                if len(series) < 14:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
            
                rsi = calculate_rsi(series)
                sma_50 = calculate_sma(series, 50).iloc[-1] if len(series) >= 50 else None
                sma_200 = calculate_sma(series, 200).iloc[-1] if len(series) >= 200 else None
                current_price = series.iloc[-1]
                
                signal = "Neutral"
                technical_data[sym] = {'RSI': round(rsi, 2), 'Signal': 'Neutral', 'Scorecard': 'Neutral'}
            except Exception:
                technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
    except Exception: pass
    return technical_data

def get_latest_news_yq(symbols):
    news_map = {}
    try:
        t = get_yq_ticker(symbols)
        all_news = t.news(20)
        if isinstance(all_news, list):
            for sym in symbols:
                for item in all_news:
                    if not isinstance(item, dict): continue
                    if sym in item.get('symbols', []):
                        title = item.get('title', 'No Title')
                        link = item.get('link', f"https://finance.yahoo.com/quote/{sym}")
                        if len(title) > 80: title = title[:77] + "..."
                        news_map[sym] = {'headline': f"📰 {title}", 'link': link}
                        break
    except Exception: pass
    return news_map

def get_dividend_calendar_yq(symbols):
    """
    Fetches dividend information (Rate, Yield, Freq, Months) using yfinance history.
    This is more robust for ETFs and international stocks than summaryDetail.
    """
    if not symbols: return {}
    divs = {}
    
    try:
        print(f"Fetching dividend history for {len(symbols)} symbols...")
        # Actions=True gets the Dividends column
        data = yf.download(symbols, period='1y', actions=True, progress=False, threads=True)
        
        # Handle single vs multi-symbol response
        if len(symbols) == 1:
            if not data.empty and 'Dividends' in data.columns:
                div_col = data['Dividends']
                sym = symbols[0]
                _process_div_series(sym, div_col, divs)
        else:
            if not data.empty and 'Dividends' in data.columns:
                div_df = data['Dividends']
                for sym in symbols:
                    if sym in div_df.columns:
                        _process_div_series(sym, div_df[sym], divs)
                        
        # Any missing? Try individual Tickers (sometimes safer for specific symbols)
        missing = [s for s in symbols if s not in divs]
        if missing:
            for sym in missing:
                try:
                    t = yf.Ticker(sym)
                    h = t.dividends
                    if not h.empty:
                        # Filter to last year
                        h_last_year = h[h.index > (pd.Timestamp.now(tz=h.index.tz) - pd.Timedelta(days=366))]
                        _process_div_series(sym, h_last_year, divs)
                except: pass

        # Final enrichment: If we found something, try to get trailing yield from summaryDetail
        # (Rate calculation: latest dividend * frequency or sum of last year)
        # We prefer forward rate if available, but for now sum is a good proxy
        
        return divs
        
    except Exception as e:
        print(f"Dividend fetch error: {e}")
        return {}

def _process_div_series(sym, series, results_dict):
    """ Helper to extract frequency and months from dividend series """
    valid = series[series > 0].dropna()
    
    if valid.empty:
        results_dict[sym] = {
            'Rate': 0.0,
            'Yield': 0.0,
            'Last_Ex': 'N/A',
            'Frequency': 'None',
            'Months': []
        }
        return
    
    # Frequency and Payout Months
    months = sorted(list(set(valid.index.month.tolist())))
    freq_count = len(valid)
    
    # Heuristic for frequency label
    if freq_count >= 11: freq = 'Monthly'
    elif 3 <= freq_count <= 5: freq = 'Quarterly'
    elif freq_count >= 1: freq = 'Annual'
    else: freq = 'Unknown'
    
    # Average per-payment Rate (ensures annual total is Rate * Frequency)
    rate = float(valid.mean()) if not valid.empty else 0.0
    
    results_dict[sym] = {
        'Rate': rate,
        'Yield': 0.0, # Will be calculated by UI or fetched later if really needed
        'Last_Ex': valid.index[-1].strftime('%Y-%m-%d') if not valid.empty else 'N/A',
        'Frequency': freq,
        'Months': months
    }

def get_fundamental_data_yq(symbols):
    fundamentals = {}
    try:
        t = get_yq_ticker(symbols)
        modules = 'summaryDetail assetProfile quoteType financialData'
        all_data = t.get_modules(modules)
        for sym in symbols:
            try:
                data = all_data.get(sym, {})
                if not isinstance(data, dict): continue
                
                asset = data.get('assetProfile', {})
                detail = data.get('summaryDetail', {})
                q_type = data.get('quoteType', {}).get('quoteType', 'EQUITY')
                fin = data.get('financialData', {})
                
                fundamentals[sym] = {
                    'Market Cap': detail.get('marketCap', 'N/A'),
                    'Trailing P/E': detail.get('trailingPE', 'N/A'),
                    'Forward P/E': detail.get('forwardPE', 'N/A'),
                    'PEG Ratio': 'N/A',
                    'Rev Growth': fin.get('revenueGrowth', 'N/A'),
                    'Profit Margin': fin.get('profitMargins', 'N/A'),
                    '52w High': detail.get('fiftyTwoWeekHigh', 'N/A'),
                    'Recommendation': detail.get('recommendationKey', 'N/A').replace('_', ' ').title(),
                    'Sector': asset.get('sector', 'Unknown'),
                    'Country': asset.get('country', 'Unknown'),
                    'Yield': "0.00%",
                    'Ex-Dividend': 'N/A',
                    'Next Earnings': 'N/A'
                }
            except Exception:
                fundamentals[sym] = {'Sector': 'Unknown'}
    except Exception: pass
    return fundamentals

def get_portfolio_history_yq(holdings_df):
    if holdings_df.empty: return pd.DataFrame()
    symbols = holdings_df['Symbol'].unique().tolist()
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    benchmarks = ['^GSPC', '^IXIC', '^GSPTSE']
    all_tickers = symbols + benchmarks + ['CAD=X']
    try:
        t = get_yq_ticker(all_tickers)
        hist = t.history(start=start_date)
        if hist.empty: return pd.DataFrame()

        # Normalize immediately to avoid mixed date/datetime comparison errors in pivot/sort
        hist = hist.reset_index()
        if 'date' in hist.columns:
            hist['date'] = pd.to_datetime(hist['date']).dt.tz_localize(None)

        if 'symbol' in hist.columns:
            closes = hist.pivot(index='date', columns='symbol', values='close')
        else:
            closes = hist.set_index('date')[['close']]
            closes.columns = [all_tickers[0]]
            
        closes = closes.sort_index().ffill()
        
        fx_rates = closes['CAD=X'] if 'CAD=X' in closes.columns else pd.Series(1.35, index=closes.index)
        portfolio_daily = pd.Series(0.0, index=closes.index)
        holdings_dict = holdings_df.set_index('Symbol')['Quantity'].to_dict()
        
        for sym, qty in holdings_dict.items():
            if sym in closes.columns:
                series = closes[sym]
                if not str(sym).endswith('.TO'): series = series * fx_rates
                portfolio_daily += (series * qty)
        
        result = pd.DataFrame(index=closes.index)
        result['Portfolio'] = portfolio_daily
        for bench in benchmarks:
            if bench in closes.columns: result[bench] = closes[bench]
                
        return result.dropna().reset_index()
    except Exception: return pd.DataFrame()
