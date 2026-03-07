import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
from backend.cache import cache_result, prices_cache, fundamentals_cache, technicals_cache, news_cache, dividend_cache, fx_cache, history_cache

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
    """
    Finds the most recent date when a stock was at or below the purchase price.
    Prefers dates that are at least min_days_ago in the past to avoid unrealistic short-term gains.
    
    Args:
        symbol: Stock ticker symbol
        purchase_price: The price paid for the stock
        tolerance: Price tolerance (5% by default) to account for price fluctuations
        min_days_ago: Minimum days ago to consider (default 30 days)
    
    Returns:
        datetime object of estimated purchase date, or None if not found
    """
    try:
        # Skip special symbols that don't have meaningful historical data
        if symbol in ['CAD=X', 'CASH.TO']:
            return None
            
        # Fetch maximum available historical data (typically 20-30 years for most stocks)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max")
        
        if hist.empty:
            print(f"  ⚠️  No historical data for {symbol}, using CSV date")
            return None
        
        # Calculate price range with tolerance
        # We look for when the stock was at or below purchase price (plus tolerance)
        max_price = purchase_price * (1 + tolerance)
        
        # Calculate cutoff date (must be at least min_days_ago in the past)
        cutoff_date = datetime.now() - timedelta(days=min_days_ago)
        
        # Filter for dates where Close price was <= max_price AND before cutoff
        matching_dates = hist[hist['Close'] <= max_price]
        
        # Convert index to naive datetimes for comparison
        matching_dates_naive = matching_dates.copy()
        matching_dates_naive.index = matching_dates_naive.index.tz_localize(None) if matching_dates_naive.index.tz else matching_dates_naive.index
        
        # Filter to only dates before cutoff
        old_matches = matching_dates_naive[matching_dates_naive.index < cutoff_date]
        
        if not old_matches.empty:
            # Prefer the most recent date that's still older than min_days_ago
            purchase_date = old_matches.index[-1]
        elif not matching_dates.empty:
            # If no old matches, but there are recent matches, use CSV date instead
            # This avoids unrealistic short-term CAGRs
            print(f"  ⚠️  {symbol} only at ${purchase_price:.2f} in last {min_days_ago} days, using CSV date")
            return None
        else:
            # Stock never traded at or below this price in available history
            print(f"  ⚠️  {symbol} never at ${purchase_price:.2f} in available history, using CSV date")
            return None
        
        # Convert to naive datetime
        if hasattr(purchase_date, 'to_pydatetime'):
            purchase_date = purchase_date.to_pydatetime()
        if hasattr(purchase_date, 'replace'):
            purchase_date = purchase_date.replace(tzinfo=None)
        
        # Sanity check: date shouldn't be in the future
        if purchase_date > datetime.now():
            print(f"  ⚠️  {symbol} calculated date is in future, using CSV date")
            return None
            
        return purchase_date
        
    except Exception as e:
        print(f"  ⚠️  Error finding purchase date for {symbol}: {e}")
        return None

@cache_result(prices_cache)
def get_current_prices(symbols):
    """
    Fetches real-time prices for a list of symbols using yfinance.
    Returns a dictionary {symbol: price}.
    """
    if not symbols:
        return {}

    print(f"Fetching prices for: {' '.join(symbols)}...")
    prices = {}
    
    try:
        data = yf.download(symbols, period="1d", progress=False)
        
        # Depending on yfinance version and single/multi symbol, data['Close'] could be a Series or DataFrame
        if len(symbols) == 1:
            try:
                closes = data['Close'].iloc[-1]
                # If only 1 symbol, it might just return the scalar
                p = float(closes.iloc[0]) if isinstance(closes, pd.Series) else float(closes)
                prices[symbols[0]] = p if not np.isnan(p) else 0.0
            except Exception as e:
                print(f"Failed extracting single symbol {symbols[0]}: {e}")
                prices[symbols[0]] = 0.0
        else:
            try:
                last_row = data['Close'].iloc[-1]
                for sym in symbols:
                    try:
                        p = float(last_row[sym])
                        prices[sym] = p if not np.isnan(p) else 0.0
                    except Exception as inner_e:
                        print(f"Failed to extract price for {sym}: {inner_e}")
                        prices[sym] = 0.0
            except Exception as e:
                print(f"Failed extracting multi-symbol row: {e}")
                for sym in symbols: prices[sym] = 0.0
                
        return prices

    except Exception as e:
        print(f"Error fetching prices via yfinance: {e}")
        return {}

def get_weekly_changes(symbols):
    """
    Fetches 5-day history and calculates % change using yfinance.
    Returns dict: {Symbol: percent_change_float}
    """
    if not symbols: return {}
    
    try:
        data = yf.download(symbols, period="5d", progress=False)
        if hasattr(data.columns, "levels") and "Close" in data.columns.levels[0]:
            closes = data['Close']
        else:
            closes = data.get('Close', pd.DataFrame())
        
        changes = {}
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    series = closes.dropna()
                else:
                    series = closes[sym].dropna()
                if len(series) >= 2:
                    start = float(series.iloc[0])
                    end = float(series.iloc[-1])
                    changes[sym] = (end - start) / start
                else:
                    changes[sym] = 0.0
            except:
                changes[sym] = 0.0
        return changes
    except Exception as e:
        print(f"Error fetching weekly changes: {e}")
        return {}

def get_daily_changes(symbols):
    """
    Fetches daily % change using yfinance.
    Returns dict: {Symbol: percent_change_float}
    """
    if not symbols: return {}
    try:
        data = yf.download(symbols, period="2d", progress=False)
        closes = data['Close']
        changes = {}
        for sym in symbols:
            try:
                series = closes.dropna() if len(symbols) == 1 else closes[sym].dropna()
                if len(series) >= 2:
                    current = float(series.iloc[-1])
                    prev = float(series.iloc[-2])
                    changes[sym] = ((current - prev) / prev) * 100
                else:
                    changes[sym] = 0.0
            except:
                changes[sym] = 0.0
        return changes
    except Exception as e:
        print(f"Error fetching daily changes: {e}")
        return {}

@cache_result(fx_cache)
def get_usd_to_cad_rate():
    """
    Fetches the current USD to CAD exchange rate using yfinance (Yahoo Finance).
    Uses 'CAD=X'.
    """
    try:
        data = yf.download("CAD=X", period="1d", progress=False)
        closes = data['Close']
        if not closes.empty:
            # Depending on yfinance version, 'Close' may be a Series or DataFrame
            if isinstance(closes, pd.DataFrame):
                rate = float(closes.iloc[-1, 0])
            else:
                rate = float(closes.iloc[-1])
                
            if rate and not np.isnan(rate) and rate > 0:
                return rate
        return 1.40 
    except Exception as e:
        print(f"Error fetching exchange rate from yfinance: {e}")
        return 1.40

def get_market_indices_change():
    """
    Fetches 5-day % change for S&P 500, NASDAQ, and TSX using yfinance.
    Returns dict: {Index Name: percent_change_float}
    """
    indices = {
        '^GSPC': '🇺🇸 S&P 500',
        '^IXIC': '🇺🇸 NASDAQ',
        '^GSPTSE': '🇨🇦 TSX'
    }
    
    try:
        data = yf.download(list(indices.keys()), period="5d", progress=False)
        closes = data['Close']
        changes = {}
        for symbol, name in indices.items():
            try:
                series = closes[symbol].dropna() if len(indices) > 1 else closes.dropna()
                if len(series) >= 2:
                    start = float(series.iloc[0])
                    end = float(series.iloc[-1])
                    changes[name] = (end - start) / start
                else:
                    changes[name] = 0.0
            except:
                changes[name] = 0.0
        return changes
    except Exception as e:
        print(f"Error fetching indices: {e}")
        return {}

def calculate_rsi(series, period=14):
    """
    Calculates the RSI of a price series.
    Returns the latest RSI value (float).
    """
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
    """
    Fetches 1-year history and calculates RSI and Moving Averages using yfinance.
    Returns dict: {Symbol: {'RSI': float, 'Signal': str, 'Scorecard': str}}
    """
    if not symbols: return {}

    technical_data = {}
    print(f"Fetching technical data (RSI & Patterns) for {len(symbols)} symbols...")
    
    try:
        data = yf.download(symbols, period="1y", progress=False)
        closes = data['Close']
        opens = data['Open']
        highs = data['High']
        lows = data['Low']
        
        for sym in symbols:
            try:
                sym_close = closes[sym].dropna() if len(symbols) > 1 else closes.dropna()
                sym_open = opens[sym].dropna() if len(symbols) > 1 else opens.dropna()
                sym_high = highs[sym].dropna() if len(symbols) > 1 else highs.dropna()
                sym_low = lows[sym].dropna() if len(symbols) > 1 else lows.dropna()
                
                if sym_close.empty or len(sym_close) < 14:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
            
                series = sym_close
                
                # RSI
                rsi = calculate_rsi(series)
                
                # Moving Averages
                sma_50 = calculate_sma(series, 50).iloc[-1] if len(series) >= 50 else None
                sma_200 = calculate_sma(series, 200).iloc[-1] if len(series) >= 200 else None
                current_price = series.iloc[-1]
                
                # Pattern Detection
                signal = "Neutral"
                
                if sma_50 and sma_200:
                    sma_50_vec = calculate_sma(series, 50)
                    sma_200_vec = calculate_sma(series, 200)
                    sma_50_prev = sma_50_vec.iloc[-5] if len(sma_50_vec) >= 5 else sma_50_vec.iloc[0]
                    sma_200_prev = sma_200_vec.iloc[-5] if len(sma_200_vec) >= 5 else sma_200_vec.iloc[0]
                    
                    if sma_50_prev < sma_200_prev and sma_50 > sma_200:
                        signal = "🌟 Golden Cross"
                    elif sma_50_prev > sma_200_prev and sma_50 < sma_200:
                        signal = "💀 Death Cross"
                    elif current_price > sma_50 > sma_200:
                        signal = "📈 Strong Uptrend"
                    elif current_price < sma_50 < sma_200:
                        signal = "📉 Downtrend"
                    elif current_price > sma_200 and current_price < sma_50:
                        signal = "⚠️ Below SMA50"
                    elif current_price < sma_200 and current_price > sma_50:
                        signal = "🔄 Recovery?"
                elif sma_50:
                    signal = "Above SMA50" if current_price > sma_50 else "Below SMA50"
                         
                # MACD
                fast = series.ewm(span=12, adjust=False).mean()
                slow = series.ewm(span=26, adjust=False).mean()
                macd = fast - slow
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                macd_sig = "Neutral"
                if len(macd) >= 2:
                    if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2]:
                        macd_sig = "🚀 MACD Buy"
                    elif macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2]:
                        macd_sig = "🔻 MACD Sell"
                    
                # Bollinger Bands
                sma_20 = calculate_sma(series, 20)
                std_20 = series.rolling(window=20).std()
                upper_bb = sma_20 + (std_20 * 2)
                lower_bb = sma_20 - (std_20 * 2)
                
                bb_sig = "Neutral"
                if len(upper_bb) > 0:
                    if current_price > upper_bb.iloc[-1]:
                        bb_sig = "Upper Band Breakout"
                    elif current_price < lower_bb.iloc[-1]:
                        bb_sig = "Lower Band Breakout"
                    elif (upper_bb.iloc[-1] - lower_bb.iloc[-1]) / sma_20.iloc[-1] < 0.05:
                        bb_sig = "Squeeze"

                # Candlestick Patterns
                candle_sig = ""
                if not sym_open.empty and not sym_high.empty and not sym_low.empty:
                    c, o, h, l = float(sym_close.iloc[-1]), float(sym_open.iloc[-1]), float(sym_high.iloc[-1]), float(sym_low.iloc[-1])
                    body = abs(c - o)
                    upper_wick = h - max(c, o)
                    lower_wick = min(c, o) - l
                    if lower_wick > 2 * body and upper_wick < body: candle_sig = "🔨 Hammer"
                    elif upper_wick > 2 * body and lower_wick < body: candle_sig = "🌠 Shooting Star"
                    elif body < (h - l) * 0.1: candle_sig = "Doji"
                
                components = [s for s in [macd_sig, bb_sig, candle_sig] if s != "Neutral" and s != ""]
                scorecard = " | ".join(components) if components else "Neutral"
                
                technical_data[sym] = {'RSI': rsi, 'Signal': signal, 'Scorecard': scorecard}
            
            except Exception as e:
                print(f"Error processing technicals for {sym}: {e}")
                technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
    except Exception as e:
        print(f"Error calculating technicals: {e}")
    return technical_data


@cache_result(news_cache)
def get_latest_news(symbols):
    """
    Fetches the latest news headline for each symbol using yfinance.
    Returns dict: {Symbol: {'headline': str, 'link': str}}
    """
    if not symbols: return {}

    print(f"Fetching latest news for {len(symbols)} symbols...")
    news_map = {}
    
    # ONLY fetch for the first 3 symbols to avoid hanging for a long time
    # yfinance news API requires 1 call per ticker
    limit = 3
    for sym in symbols[:limit]:
        try:
            yt = yf.Ticker(sym)
            y_news = yt.news
            if y_news and isinstance(y_news, list):
                top = y_news[0]
                # Structure varies: sometimes it's nested in 'content'
                content = top.get('content', top)
                title = content.get('title', 'No Title')
                link = content.get('link', f"https://finance.yahoo.com/quote/{sym}")
                if len(title) > 80:
                    title = title[:77] + "..."
                news_map[sym] = {'headline': f"📰 {title}", 'link': link}
        except Exception:
            pass

    return news_map

@cache_result(dividend_cache)
def get_dividend_calendar(symbols):
    """
    Fetches dividend history to project future income using yfinance.
    Returns dict: {Symbol: {'Frequency': 'Monthly', 'Rate': 0.50, 'Months': [1,2,3...]}}
    """
    if not symbols: return {}

    print(f"Fetching dividend calendar for {len(symbols)} symbols...")
    div_calendar = {}
    
    try:
        for sym in symbols:
            try:
                yt = yf.Ticker(sym)
                # Fetch dividends
                divs = yt.dividends
                
                if divs is None or divs.empty: continue
                
                # Filter for last 1 year
                start_date = pd.Timestamp(datetime.now() - timedelta(days=366)).tz_localize(divs.index.tz)
                sym_divs = divs[divs.index >= start_date]
                
                if sym_divs.empty: continue
                
                # Process Dividends
                count = len(sym_divs)
                freq = "None"
                if count >= 10: freq = "Monthly"
                elif count >= 3: freq = "Quarterly"
                elif count >= 2: freq = "Semi-Annual"
                elif count >= 1: freq = "Annual"
                
                months = list(set([d.month for d in sym_divs.index]))
                rate = float(sym_divs.iloc[-1])
                
                div_calendar[sym] = {
                    'Frequency': freq,
                    'Rate': rate,
                    'Months': sorted(months)
                }
            except Exception:
                pass
    except Exception as e:
        print(f"Error fetching dividends via yfinance: {e}")
        
    return div_calendar

@cache_result(fundamentals_cache)
def get_fundamental_data(symbols):
    """
    Fetches fundamental data for a list of symbols using yfinance.
    """
    if not symbols: return {}
    
    fundamentals = {}
    print(f"Fetching fundamentals for {len(symbols)} symbols via yfinance...")
    
    custom_sectors = {
        'VOO': 'US Broad Market', 'XQQ.TO': 'US Technology', 'XEI.TO': 'Canadian Dividends',
        'XIU.TO': 'Canadian Broad Market', 'XEF.TO': 'International Developed', 'XEC.TO': 'Emerging Markets',
        'SLV': 'Commodities', 'GLD': 'Commodities', 'BTC-USD': 'Crypto', 'ETH-USD': 'Crypto',
        'CAD=X': 'Currency', 'CASH.TO': 'Cash & Equivalents', 'NVDA': 'Technology',
        'MSFT': 'Technology', 'CRM': 'Technology', 'COST': 'Consumer Defensive',
        'V': 'Financial Services', 'UNH': 'Healthcare', 'TD.TO': 'Financial Services',
        'CM.TO': 'Financial Services', 'AC.TO': 'Industrials', 'WCP.TO': 'Energy', 'VDY.TO': 'Canadian Dividends',
        'AVUV': 'US Small Cap Value', 'JPST': 'Short-Term Fixed Income',
        'QQQ': 'US Technology',
        'XQQ': 'US Technology',
        'SMH': 'US Semiconductors',
    }

    try:
        for sym in symbols:
            try:
                yt = yf.Ticker(sym)
                info = yt.info
                if not isinstance(info, dict): continue
                
                q_type = info.get('quoteType', 'EQUITY')
                
                # Sector
                sector = info.get('sector') or 'N/A'
                if sym in custom_sectors:
                    normalized_sector = custom_sectors[sym]
                elif q_type == 'ETF':
                    normalized_sector = info.get('category', 'Other ETF')
                elif q_type == 'CRYPTOCURRENCY':
                    normalized_sector = 'Crypto'
                else:
                    normalized_sector = sector
                
                # Yield
                div_yield = info.get('dividendYield', 0)
                yield_str = f"{div_yield*100:.2f}%" if div_yield else "0.00%"
                
                ex_div = info.get('exDividendDate', 'N/A')
                
                calendar = yt.calendar
                next_earnings = 'N/A'
                if isinstance(calendar, dict) and 'Earnings Date' in calendar:
                    dates = calendar['Earnings Date']
                    if len(dates) > 0:
                        next_earnings = dates[0]
                elif isinstance(calendar, pd.DataFrame) and not calendar.empty:
                    if 'Earnings Date' in calendar.columns:
                        d = calendar['Earnings Date'].iloc[0]
                        next_earnings = d.strftime("%Y-%m-%d") if pd.notna(d) else 'N/A'

                peg = info.get('pegRatio', 'N/A')
                
                f_data = {
                    'Market Cap': info.get('marketCap', 'N/A'),
                    'Trailing P/E': info.get('trailingPE', 'N/A'),
                    'Forward P/E': info.get('forwardPE', 'N/A'),
                    'PEG Ratio': peg,
                    'Rev Growth': info.get('revenueGrowth', 'N/A'),
                    'Profit Margin': info.get('profitMargins', 'N/A'),
                    '52w High': info.get('fiftyTwoWeekHigh', 'N/A'),
                    'Recommendation': info.get('recommendationKey', 'N/A').replace('_', ' ').title() if info.get('recommendationKey') else 'N/A',
                    'Sector': normalized_sector,
                    'Country': info.get('country', 'Unknown'),
                    'Yield': yield_str,
                    'Ex-Dividend': str(ex_div),
                    'Next Earnings': str(next_earnings)
                }
                fundamentals[sym] = f_data
            except Exception as e:
                print(f"Error processing {sym}: {e}")
                fundamentals[sym] = {'Sector': 'Unknown'}
    except Exception as e:
        print(f"Error fetching fundamentals via yfinance: {e}")
        
    return fundamentals
            
@cache_result(history_cache)
def get_portfolio_history(holdings_df):
    """
    Simulates historical portfolio performance by backtesting current holdings using yfinance.
    """
    if holdings_df.empty: return pd.DataFrame()

    symbols = holdings_df['Symbol'].unique().tolist()
    
    # Needs 10 years of data
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    
    # Benchmarks and FX
    benchmarks = ['^GSPC', '^IXIC', '^GSPTSE']
    fx_symbol = 'CAD=X'
    all_tickers = symbols + benchmarks + [fx_symbol]
    
    print(f"Fetching 10Y history for performance analysis via yfinance...")
    try:
        data = yf.download(all_tickers, start=start_date, progress=False)
        if data.empty: return pd.DataFrame()

        if hasattr(data.columns, "levels") and "Close" in data.columns.levels[0]:
            closes = data['Close']
        else:
            closes = pd.DataFrame(data['Close']) if 'Close' in data else data
            
        # Ensure chronological order and properly handle timezones before filling missing values
        closes.index = pd.to_datetime(closes.index, utc=True)
        closes = closes.sort_index()

        closes = closes.ffill()
        
        # FX Rates
        if fx_symbol in closes.columns:
            fx_rates = closes[fx_symbol]
        else:
            fx_rates = pd.Series(1.35, index=closes.index)

        # Calculate Daily Portfolio Value
        portfolio_daily = pd.Series(0.0, index=closes.index)
        holdings_dict = holdings_df.set_index('Symbol')['Quantity'].to_dict()
        
        for sym, qty in holdings_dict.items():
            if sym in closes.columns:
                series = closes[sym]
                if not str(sym).endswith('.TO'):
                    series = series * fx_rates
                portfolio_daily += (series * qty)
        
        # Construct Result
        result = pd.DataFrame(index=closes.index)
        result['Portfolio'] = portfolio_daily
        for bench in benchmarks:
            if bench in closes.columns:
                result[bench] = closes[bench]
                
        result = result.dropna().reset_index()
        
        # Remove Date col name if exists
        if 'Date' in result.columns:
            result.rename(columns={'Date': 'date'}, inplace=True)
        
        return result

    except Exception as e:
        print(f"History Fetch Error via yfinance: {e}")
        return pd.DataFrame()

