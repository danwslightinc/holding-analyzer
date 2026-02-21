import yfinance as yf
from yahooquery import Ticker
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time

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

def get_current_prices(symbols):
    """
    Fetches real-time prices for a list of symbols using yahooquery.
    Returns a dictionary {symbol: price}.
    """
    if not symbols:
        return {}

    print(f"Fetching prices for: {' '.join(symbols)}...")
    
    try:
        t = Ticker(symbols)
        # Use price module for quote data
        price_data = t.price
        prices = {}
        
        for sym in symbols:
            s_data = price_data.get(sym, {})
            if isinstance(s_data, dict):
                p = s_data.get('regularMarketPrice', 0.0)
                prices[sym] = float(p)
            else:
                # Handle error cases or missing data
                prices[sym] = 0.0
                
        return prices

    except Exception as e:
        print(f"Error fetching prices via yahooquery: {e}")
        return {}

def get_weekly_changes(symbols):
    """
    Fetches 5-day history and calculates % change using yahooquery.
    Returns dict: {Symbol: percent_change_float}
    """
    if not symbols: return {}
    
    try:
        t = Ticker(symbols)
        # Fetch 5 days of history
        hist = t.history(period="5d")
        
        changes = {}
        
        for sym in symbols:
            if sym in hist.index.levels[0] if isinstance(hist.index, pd.MultiIndex) else sym in hist.index:
                sym_hist = hist.xs(sym) if isinstance(hist.index, pd.MultiIndex) else hist
                if len(sym_hist) >= 2:
                    start = float(sym_hist['close'].iloc[0])
                    end = float(sym_hist['close'].iloc[-1])
                    changes[sym] = (end - start) / start
                else:
                    changes[sym] = 0.0
            else:
                changes[sym] = 0.0
        return changes
                        
    except Exception as e:
        print(f"Error fetching weekly changes: {e}")
        return {}

def get_usd_to_cad_rate():
    """
    Fetches the current USD to CAD exchange rate using yahooquery.
    Uses 'CAD=X'.
    """
    try:
        t = Ticker("CAD=X")
        rate = t.price.get('CAD=X', {}).get('regularMarketPrice')
        if rate:
            return float(rate)
        return 1.40 
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return 1.40

def get_market_indices_change():
    """
    Fetches 5-day % change for S&P 500, NASDAQ, and TSX using yahooquery.
    Returns dict: {Index Name: percent_change_float}
    """
    indices = {
        '^GSPC': '🇺🇸 S&P 500',
        '^IXIC': '🇺🇸 NASDAQ',
        '^GSPTSE': '🇨🇦 TSX'
    }
    
    try:
        t = Ticker(list(indices.keys()))
        hist = t.history(period="5d")
        
        changes = {}
        for symbol, name in indices.items():
            if symbol in hist.index.levels[0]:
                sym_hist = hist.xs(symbol)
                if len(sym_hist) >= 2:
                    start = float(sym_hist['close'].iloc[0])
                    end = float(sym_hist['close'].iloc[-1])
                    changes[name] = (end - start) / start
                else:
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

def get_technical_data(symbols):
    """
    Fetches 1-year history and calculates RSI and Moving Averages using yahooquery.
    Returns dict: {Symbol: {'RSI': float, 'Signal': str, 'Scorecard': str}}
    """
    if not symbols: return {}

    technical_data = {}
    print(f"Fetching technical data (RSI & Patterns) for {len(symbols)} symbols...")
    
    try:
        t = Ticker(symbols, asynchronous=True)
        # Fetch enough history for SMA 200
        hist = t.history(period="1y")
        
        for sym in symbols:
            try:
                # Handle MultiIndex or SingleIndex
                if isinstance(hist.index, pd.MultiIndex):
                    if sym not in hist.index.levels[0]:
                        technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                        continue
                    sym_hist = hist.xs(sym)
                else:
                    if len(symbols) > 1: # Unexpected but handle
                        continue
                    sym_hist = hist
                
                if sym_hist.empty or 'close' not in sym_hist.columns:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
                    
                series = sym_hist['close'].dropna()
                
                if len(series) < 14:
                    technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
                    continue
            
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
                if 'open' in sym_hist.columns and 'high' in sym_hist.columns and 'low' in sym_hist.columns:
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
            
            except Exception as e:
                print(f"Error processing technicals for {sym}: {e}")
                technical_data[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': ''}
    except Exception as e:
        print(f"Error calculating technicals: {e}")
    return technical_data


def get_latest_news(symbols):
    """
    Fetches the latest news headline for each symbol using yahooquery.
    Returns dict: {Symbol: {'headline': str, 'link': str}}
    """
    if not symbols: return {}

    print(f"Fetching latest news for {len(symbols)} symbols...")
    news_map = {}
    
    try:
        t = Ticker(symbols)
        all_news = t.news(20) # Get a batch of news
        
        # Check if all_news is a valid list of dictionaries
        if isinstance(all_news, list):
            for sym in symbols:
                for item in all_news:
                    if not isinstance(item, dict):
                        continue
                        
                    item_syms = item.get('symbols', [])
                    if sym in item_syms:
                        title = item.get('title', 'No Title')
                        link = item.get('link', f"https://finance.yahoo.com/quote/{sym}")
                        if len(title) > 80:
                            title = title[:77] + "..."
                        news_map[sym] = {'headline': f"📰 {title}", 'link': link}
                        break
        
        # Fallback for missing symbols: try yfinance for news (often bypasses crumb issues)
        remaining = [s for s in symbols if s not in news_map]
        if remaining:
            print(f"Using yfinance fallback for news for {len(remaining)} symbols...")
            for sym in remaining:
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

    except Exception as e:
        print(f"Error fetching news: {e}")
        
    return news_map

def get_dividend_calendar(symbols):
    """
    Fetches dividend history to project future income using yahooquery.
    Returns dict: {Symbol: {'Frequency': 'Monthly', 'Rate': 0.50, 'Months': [1,2,3...]}}
    """
    if not symbols: return {}

    print(f"Fetching dividend calendar for {len(symbols)} symbols...")
    div_calendar = {}
    
    try:
        t = Ticker(symbols, asynchronous=True)
        # Fetch 1 year of dividends
        all_divs = t.dividend_history(start=(datetime.now() - timedelta(days=366)).strftime('%Y-%m-%d'))
        
        for sym in symbols:
            try:
                if all_divs.empty: continue
                
                # Filter for this symbol
                if isinstance(all_divs.index, pd.MultiIndex):
                    if sym not in all_divs.index.levels[0]: continue
                    sym_divs = all_divs.xs(sym)
                else:
                    sym_divs = all_divs
                
                if sym_divs.empty: continue
                
                # Process Dividends
                count = len(sym_divs)
                freq = "None"
                if count >= 10: freq = "Monthly"
                elif count >= 3: freq = "Quarterly"
                elif count >= 2: freq = "Semi-Annual"
                elif count >= 1: freq = "Annual"
                
                months = list(set([d.month for d in sym_divs.index]))
                rate = float(sym_divs['dividends'].iloc[-1])
                
                div_calendar[sym] = {
                    'Frequency': freq,
                    'Rate': rate,
                    'Months': sorted(months)
                }
            except Exception:
                pass
    except Exception as e:
        print(f"Error fetching dividends via yahooquery: {e}")
        
    return div_calendar

def get_fundamental_data(symbols):
    """
    Fetches fundamental data for a list of symbols using yahooquery.
    """
    if not symbols: return {}
    
    fundamentals = {}
    print(f"Fetching fundamentals for {len(symbols)} symbols via yahooquery...")
    
    custom_sectors = {
        'VOO': 'US Broad Market', 'XQQ.TO': 'US Technology', 'XEI.TO': 'Canadian Dividends',
        'XIU.TO': 'Canadian Broad Market', 'XEF.TO': 'International Developed', 'XEC.TO': 'Emerging Markets',
        'SLV': 'Commodities', 'GLD': 'Commodities', 'BTC-USD': 'Crypto', 'ETH-USD': 'Crypto',
        'CAD=X': 'Currency', 'CASH.TO': 'Cash & Equivalents', 'NVDA': 'Technology',
        'MSFT': 'Technology', 'CRM': 'Technology', 'COST': 'Consumer Defensive',
        'V': 'Financial Services', 'UNH': 'Healthcare', 'TD.TO': 'Financial Services',
        'CM.TO': 'Financial Services', 'AC.TO': 'Industrials',        'WCP.TO': 'Energy', 'VDY.TO': 'Canadian Dividends',
        'AVUV': 'US Small Cap Value', 'JPST': 'Short-Term Fixed Income'
    }

    try:
        t = Ticker(symbols, asynchronous=True)
        # Fetch multiple modules at once
        modules = 'summaryDetail assetProfile quoteType defaultKeyStatistics calendarEvents financialData'
        all_data = t.get_modules(modules)
        
        for sym in symbols:
            try:
                data = all_data.get(sym, {})
                if not isinstance(data, dict): continue
                
                asset = data.get('assetProfile', {})
                stats = data.get('defaultKeyStatistics', {})
                detail = data.get('summaryDetail', {})
                cal = data.get('calendarEvents', {})
                q_type = data.get('quoteType', {}).get('quoteType', 'EQUITY')
                fin = data.get('financialData', {})
                
                # Sector
                sector = asset.get('sector') or 'N/A'
                if sym in custom_sectors:
                    normalized_sector = custom_sectors[sym]
                elif q_type == 'ETF':
                    normalized_sector = asset.get('category', 'Other ETF')
                elif q_type == 'CRYPTOCURRENCY':
                    normalized_sector = 'Crypto'
                else:
                    normalized_sector = sector
                
                # Yield
                div_yield = detail.get('dividendYield', 0)
                yield_str = f"{div_yield*100:.2f}%" if div_yield else "0.00%"
                
                # Ex-Div
                ex_div = detail.get('exDividendDate', 'N/A')
                
                # Next Earnings
                next_earnings = 'N/A'
                if isinstance(cal, dict):
                    earnings_dates = cal.get('earnings', {}).get('earningsDate', [])
                    if earnings_dates:
                        try:
                            next_earnings = earnings_dates[0]
                        except Exception: pass

                # PEG
                peg = stats.get('pegRatio', 'N/A')
                
                f_data = {
                    'Market Cap': detail.get('marketCap', 'N/A'),
                    'Trailing P/E': detail.get('trailingPE', 'N/A'),
                    'Forward P/E': detail.get('forwardPE', 'N/A'),
                    'PEG Ratio': peg,
                    'Rev Growth': fin.get('revenueGrowth', 'N/A'),
                    'Profit Margin': fin.get('profitMargins', 'N/A'),
                    '52w High': detail.get('fiftyTwoWeekHigh', 'N/A'),
                    'Recommendation': detail.get('recommendationKey', 'N/A').replace('_', ' ').title(),
                    'Sector': normalized_sector,
                    'Country': asset.get('country', 'Unknown'),
                    'Yield': yield_str,
                    'Ex-Dividend': str(ex_div),
                    'Next Earnings': str(next_earnings)
                }
                fundamentals[sym] = f_data
            except Exception as e:
                print(f"Error processing {sym}: {e}")
                fundamentals[sym] = {'Sector': 'Unknown'}
    except Exception as e:
        print(f"Error fetching fundamentals via yahooquery: {e}")
        
    return fundamentals
            
def get_portfolio_history(holdings_df):
    """
    Simulates historical portfolio performance by backtesting current holdings using yahooquery.
    """
    if holdings_df.empty: return pd.DataFrame()

    symbols = holdings_df['Symbol'].unique().tolist()
    
    # Needs 10 years of data
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    
    # Benchmarks and FX
    benchmarks = ['^GSPC', '^IXIC', '^GSPTSE']
    fx_symbol = 'CAD=X'
    all_tickers = symbols + benchmarks + [fx_symbol]
    
    print(f"Fetching 10Y history for performance analysis via yahooquery...")
    try:
        t = Ticker(all_tickers, asynchronous=True)
        # Fetch 10 years of history
        hist = t.history(start=start_date)
        
        if hist.empty: return pd.DataFrame()

        # Pivot the MultiIndex long format to wide format (date x symbol)
        # yahooquery returns columns like 'close', 'adjclose', etc.
        # Handling for both cases of history returning Dataframe with symbol index or just Symbol column
        if isinstance(hist.index, pd.MultiIndex):
            closes = hist.reset_index().pivot(index='date', columns='symbol', values='close')
        else:
            # Handle single symbol if asynchronous=True still gave a non-multiindex
            closes = hist[['close']].copy()
            closes.columns = [all_tickers[0]]
            
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
        return result

    except Exception as e:
        print(f"History Fetch Error via yahooquery: {e}")
        return pd.DataFrame()

