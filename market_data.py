import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import concurrent.futures
from backend.cache import cache_result, prices_cache, fundamentals_cache, technicals_cache, news_cache, dividend_cache, fx_cache, history_cache

_yf_session = None
def get_yf_session():
    global _yf_session
    if _yf_session is None:
        try:
            from curl_cffi import requests
            _yf_session = requests.Session(impersonate="chrome110")
        except ImportError:
            import requests
            _yf_session = requests.Session()
            _yf_session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'})
    return _yf_session


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
    try:
        if symbol in ['CAD=X', 'CASH.TO']:
            return None
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max")
        if hist.empty:
            return None
        max_price = purchase_price * (1 + tolerance)
        cutoff_date = datetime.now() - timedelta(days=min_days_ago)
        matching_dates = hist[hist['Close'] <= max_price]
        matching_dates_naive = matching_dates.copy()
        matching_dates_naive.index = matching_dates_naive.index.tz_localize(None) if matching_dates_naive.index.tz else matching_dates_naive.index
        old_matches = matching_dates_naive[matching_dates_naive.index < cutoff_date]
        if not old_matches.empty:
            purchase_date = old_matches.index[-1]
        elif not matching_dates.empty:
            return None
        else:
            return None
        if hasattr(purchase_date, 'to_pydatetime'):
            purchase_date = purchase_date.to_pydatetime()
        if hasattr(purchase_date, 'replace'):
            purchase_date = purchase_date.replace(tzinfo=None)
        if purchase_date > datetime.now():
            return None
        return purchase_date
    except Exception as e:
        return None

@cache_result(prices_cache)
def get_current_prices(symbols):
    if not symbols: return {}
    print(f"Fetching prices for: {' '.join(symbols)} via yfinance...")
    prices = {}
    try:
        data = yf.download(symbols, period="1d", progress=False, threads=True)
        if not data.empty:
            if len(symbols) == 1:
                val = data['Close'].iloc[-1]
                p = float(val.iloc[0]) if hasattr(val, 'iloc') and isinstance(val, pd.Series) else float(val)
                if not np.isnan(p) and p > 0:
                    prices[symbols[0]] = p
            else:
                last_row = data['Close'].iloc[-1]
                for sym in symbols:
                    try:
                        p = float(last_row[sym])
                        if not np.isnan(p) and p > 0: prices[sym] = p
                    except: pass
        for sym in symbols:
            if sym not in prices:
                prices[sym] = 0.0
        return prices
    except Exception as e:
        print(f"Error in get_current_prices: {e}")
        return {s: 0.0 for s in symbols}

def get_weekly_changes(symbols):
    if not symbols: return {}
    try:
        data = yf.download(symbols, period="5d", progress=False)
        changes = {}
        if data.empty: return {s: 0.0 for s in symbols}
        close_data = data['Close']
        if len(symbols) == 1:
            sym = symbols[0]
            if len(close_data) >= 2:
                start = float(close_data.iloc[0])
                end = float(close_data.iloc[-1])
                changes[sym] = (end - start) / start if start > 0 else 0.0
            else:
                changes[sym] = 0.0
        else:
            for sym in symbols:
                try:
                    sym_col = close_data[sym].dropna()
                    if len(sym_col) >= 2:
                        start = float(sym_col.iloc[0])
                        end = float(sym_col.iloc[-1])
                        changes[sym] = (end - start) / start if start > 0 else 0.0
                    else:
                        changes[sym] = 0.0
                except:
                    changes[sym] = 0.0
        return changes
    except Exception:
        return {s: 0.0 for s in symbols}

def get_daily_changes(symbols):
    if not symbols: return {}
    try:
        data = yf.download(symbols, period="2d", progress=False)
        changes = {}
        if data.empty: return {s: 0.0 for s in symbols}
        close_data = data['Close']
        if len(symbols) == 1:
            sym = symbols[0]
            if len(close_data) >= 2:
                start = float(close_data.iloc[-2])
                end = float(close_data.iloc[-1])
                changes[sym] = ((end - start) / start) * 100 if start > 0 else 0.0
            else:
                changes[sym] = 0.0
        else:
            for sym in symbols:
                try:
                    sym_col = close_data[sym].dropna()
                    if len(sym_col) >= 2:
                        start = float(sym_col.iloc[-2])
                        end = float(sym_col.iloc[-1])
                        changes[sym] = ((end - start) / start) * 100 if start > 0 else 0.0
                    else:
                        changes[sym] = 0.0
                except:
                    changes[sym] = 0.0
        return changes
    except Exception:
        return {s: 0.0 for s in symbols}

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
    indices = {'^GSPC': '🇺🇸 S&P 500', '^IXIC': '🇺🇸 NASDAQ', '^GSPTSE': '🇨🇦 TSX'}
    try:
        data = yf.download(list(indices.keys()), period="5d", progress=False)
        changes = {}
        if not data.empty:
            close_data = data['Close']
            for symbol, name in indices.items():
                try:
                    sym_col = close_data[symbol].dropna()
                    if len(sym_col) >= 2:
                        start = float(sym_col.iloc[0])
                        end = float(sym_col.iloc[-1])
                        changes[name] = (end - start) / start if start > 0 else 0.0
                    else:
                        changes[name] = 0.0
                except: changes[name] = 0.0
        return changes
    except Exception:
        return {}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

@cache_result(technicals_cache)
def get_technical_data(symbols):
    if not symbols: return {}
    technical_data = {}
    try:
        data = yf.download(symbols, period="1y", progress=False)
        if data.empty: return {s: {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''} for s in symbols}
        
        is_multi = len(symbols) > 1
        for sym in symbols:
            try:
                sym_hist = pd.DataFrame()
                if is_multi:
                    sym_hist['close'] = data['Close'][sym]
                    sym_hist['open'] = data['Open'][sym]
                    sym_hist['high'] = data['High'][sym]
                    sym_hist['low'] = data['Low'][sym]
                else:
                    sym_hist['close'] = data['Close']
                    sym_hist['open'] = data['Open']
                    sym_hist['high'] = data['High']
                    sym_hist['low'] = data['Low']
                    
                sym_hist = sym_hist.dropna()
                
                if sym_hist.empty or len(sym_hist) < 14:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
                    
                series = sym_hist['close']
                rsi = calculate_rsi(series)
                
                sma_50 = calculate_sma(series, 50).iloc[-1] if len(series) >= 50 else None
                sma_200 = calculate_sma(series, 200).iloc[-1] if len(series) >= 200 else None
                current_price = series.iloc[-1]
                
                signal = "Neutral"
                if sma_50 and sma_200:
                    sma_50_vec = calculate_sma(series, 50)
                    sma_200_vec = calculate_sma(series, 200)
                    sma_50_prev = sma_50_vec.iloc[-5] if len(sma_50_vec) >= 5 else sma_50_vec.iloc[0]
                    sma_200_prev = sma_200_vec.iloc[-5] if len(sma_200_vec) >= 5 else sma_200_vec.iloc[0]
                    
                    if sma_50_prev < sma_200_prev and sma_50 > sma_200: signal = "🌟 Golden Cross"
                    elif sma_50_prev > sma_200_prev and sma_50 < sma_200: signal = "💀 Death Cross"
                    elif current_price > sma_50 > sma_200: signal = "📈 Strong Uptrend"
                    elif current_price < sma_50 < sma_200: signal = "📉 Downtrend"
                    elif current_price > sma_200 and current_price < sma_50: signal = "⚠️ Below SMA50"
                    elif current_price < sma_200 and current_price > sma_50: signal = "🔄 Recovery?"
                elif sma_50:
                    signal = "Above SMA50" if current_price > sma_50 else "Below SMA50"
                         
                fast = series.ewm(span=12, adjust=False).mean()
                slow = series.ewm(span=26, adjust=False).mean()
                macd = fast - slow
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                macd_sig = "Neutral"
                if len(macd) >= 2:
                    if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2]: macd_sig = "🚀 MACD Buy"
                    elif macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2]: macd_sig = "🔻 MACD Sell"
                    
                sma_20 = calculate_sma(series, 20)
                std_20 = series.rolling(window=20).std()
                upper_bb = sma_20 + (std_20 * 2)
                lower_bb = sma_20 - (std_20 * 2)
                
                bb_sig = "Neutral"
                if len(upper_bb) > 0:
                    if current_price > upper_bb.iloc[-1]: bb_sig = "Upper Band Breakout"
                    elif current_price < lower_bb.iloc[-1]: bb_sig = "Lower Band Breakout"
                    elif (upper_bb.iloc[-1] - lower_bb.iloc[-1]) / sma_20.iloc[-1] < 0.05: bb_sig = "Squeeze"

                candle_sig = ""
                latest = sym_hist.iloc[-1]
                o, h, l, c = latest['open'], latest['high'], latest['low'], latest['close']
                body = abs(c - o)
                upper_wick = h - max(c, o)
                lower_wick = min(c, o) - l
                if lower_wick > 2 * body and upper_wick < body: candle_sig = "🔨 Hammer"
                elif upper_wick > 2 * body and lower_wick < body: candle_sig = "🌠 Shooting Star"
                elif body < (h - l) * 0.1: candle_sig = "Doji"
                
                components = [s for s in [macd_sig, bb_sig, candle_sig] if s != "Neutral" and s != ""]
                scorecard = " | ".join(components) if components else "Neutral"
                
                technical_data[sym] = {'RSI': rsi, 'Signal': signal, 'Scorecard': scorecard}
            except Exception:
                technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
    except Exception: pass
    return technical_data

def fetch_symbol_news(sym):
    try:
        yt = yf.Ticker(sym)
        y_news = yt.news
        if y_news and isinstance(y_news, list):
            top = y_news[0]
            content = top.get('content', top)
            title = content.get('title', 'No Title')
            link = content.get('link', f"https://finance.yahoo.com/quote/{sym}")
            if len(title) > 80: title = title[:77] + "..."
            return sym, {'headline': f"📰 {title}", 'link': link}
    except Exception: pass
    return sym, None

@cache_result(news_cache)
def get_latest_news(symbols):
    if not symbols: return {}
    news_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_symbol_news, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            sym, res = future.result()
            if res: news_map[sym] = res
    return news_map

def fetch_symbol_dividends(sym):
    try:
        yt = yf.Ticker(sym)
        divs = yt.dividends
        if not divs.empty:
            divs = divs[divs.index >= pd.to_datetime(datetime.now() - pd.Timedelta(days=366), utc=True)]
            if not divs.empty:
                count = len(divs)
                freq = "None"
                if count >= 10: freq = "Monthly"
                elif count >= 3: freq = "Quarterly"
                elif count >= 2: freq = "Semi-Annual"
                elif count >= 1: freq = "Annual"
                months = list(set([d.month for d in divs.index]))
                rate = float(divs.iloc[-1])
                return sym, {'Frequency': freq, 'Rate': rate, 'Months': sorted(months)}
    except Exception: pass
    return sym, None

@cache_result(dividend_cache)
def get_dividend_calendar(symbols):
    if not symbols: return {}
    div_calendar = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_symbol_dividends, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            sym, res = future.result()
            if res: div_calendar[sym] = res
    return div_calendar

def fetch_symbol_fundamentals(sym):
    custom_sectors = {
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
    try:
        yt = yf.Ticker(sym)
        info = yt.info
        q_type = info.get('quoteType', 'EQUITY')
        sector = info.get('sector') or 'N/A'
        if sym in custom_sectors: normalized_sector = custom_sectors[sym]
        elif q_type == 'ETF': normalized_sector = info.get('category', 'Other ETF')
        elif q_type == 'CRYPTOCURRENCY': normalized_sector = 'Crypto'
        else: normalized_sector = sector
        
        div_yield = info.get('dividendYield', 0)
        yield_str = f"{div_yield:.2f}%" if div_yield else "0.00%"
        ex_div = info.get('exDividendDate', 'N/A')
        if ex_div != 'N/A':
            try: ex_div = datetime.fromtimestamp(ex_div).strftime('%Y-%m-%d')
            except: pass
            
        f_data = {
            'Market Cap': info.get('marketCap', 'N/A'),
            'Trailing P/E': info.get('trailingPE', 'N/A'),
            'Forward P/E': info.get('forwardPE', 'N/A'),
            'PEG Ratio': info.get('pegRatio', 'N/A'),
            'Rev Growth': info.get('revenueGrowth', 'N/A'),
            'Profit Margin': info.get('profitMargins', 'N/A'),
            '52w High': info.get('fiftyTwoWeekHigh', 'N/A'),
            'Recommendation': info.get('recommendationKey', 'N/A').replace('_', ' ').title() if info.get('recommendationKey') else 'N/A',
            'Sector': normalized_sector,
            'Country': info.get('country', 'Unknown'),
            'Yield': yield_str,
            'Ex-Dividend': str(ex_div),
            'Next Earnings': 'N/A' # Next Earnings usually requires calendar event fetching which is often empty in standard yfinance info
        }
        return sym, f_data
    except Exception:
        return sym, {'Sector': 'Unknown'}

@cache_result(fundamentals_cache)
def get_fundamental_data(symbols):
    if not symbols: return {}
    fundamentals = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_symbol_fundamentals, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            sym, res = future.result()
            if res: fundamentals[sym] = res
    return fundamentals

@cache_result(history_cache)
def get_portfolio_history(holdings_df):
    if holdings_df.empty: return pd.DataFrame()
    symbols = holdings_df['Symbol'].unique().tolist()
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    benchmarks = ['^GSPC', '^IXIC', '^GSPTSE']
    fx_symbol = 'CAD=X'
    all_tickers = symbols + benchmarks + [fx_symbol]
    
    try:
        data = yf.download(all_tickers, start=start_date, progress=False, threads=True)
        if data.empty: return pd.DataFrame()
        closes = data['Close']
        closes.index = pd.to_datetime(closes.index, utc=True)
        closes = closes.sort_index().ffill()
        
        fx_rates = closes[fx_symbol] if fx_symbol in closes.columns else pd.Series(1.35, index=closes.index)
        portfolio_daily = pd.Series(0.0, index=closes.index)
        holdings_dict = holdings_df.set_index('Symbol')['Quantity'].to_dict()
        
        for sym, qty in holdings_dict.items():
            if sym in closes.columns:
                series = closes[sym].dropna()
                # Instead of dropping NA and shifting array, align series to the common index
                # Series will automatically align on index when multiplied and added
                # But to avoid missing prices, ffill was used above globally on closes
                series = closes[sym]
                if not str(sym).endswith('.TO'): series = series * fx_rates
                portfolio_daily += (series * qty).fillna(0)
                
        result = pd.DataFrame(index=closes.index)
        result['Portfolio'] = portfolio_daily
        for bench in benchmarks:
            if bench in closes.columns: result[bench] = closes[bench]
                
        return result.dropna().reset_index()
    except Exception:
        return pd.DataFrame()
