import os
import time
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from backend.database import engine
from backend.models import MarketDataCache, UserSettings, Holding
from sqlmodel import Session, select
import urllib.parse

ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
BASE_URL = "https://www.alphavantage.co/query"


# Max time to keep cache (24 hours)
CACHE_TTL = timedelta(hours=24)

def get_session():
    return Session(engine)

def get_api_key(db_session):
    # Check UserSettings first
    setting = db_session.exec(select(UserSettings).where(UserSettings.key == "ALPHA_VANTAGE_API_KEY")).first()
    if setting and setting.value and setting.value.strip() != "":
        return setting.value.strip()
    return ALPHA_VANTAGE_API_KEY

def fetch_av_data(function, symbol, **kwargs):
    """
    Fetch data from Alpha Vantage with database caching and fallback handling
    """
    # Alpha Vantage uses .TRT for Toronto index
    av_symbol = symbol
    if av_symbol.endswith(".TO"):
        av_symbol = av_symbol.replace(".TO", ".TRT")
    elif av_symbol == "CAD=X":
        # we will handle currency exchange differently
        pass
        
    with get_session() as db_session:
        # Check cache
        try:
            cache_hit = db_session.exec(
                select(MarketDataCache)
                .where((MarketDataCache.endpoint == function) & (MarketDataCache.symbol == symbol))
            ).first()
        except Exception as e:
            db_session.rollback()
            if "no such table" in str(e).lower():
                from backend.database import create_db_and_tables
                create_db_and_tables()
                cache_hit = None
            else:
                print(f"Database error on cache lookup: {e}")
                cache_hit = None
        
        api_key_to_use = get_api_key(db_session)
        
        if cache_hit:
            # Check if still valid (less than 24h old)
            if datetime.utcnow() - cache_hit.updated_at < CACHE_TTL:
                print(f"CACHE HIT [Alpha Vantage]: {function} for {symbol}")
                return json.loads(cache_hit.data)
            
            # If expired but we don't have a real API key, just keep using the expired cache!
            if api_key_to_use == 'demo':
                print(f"CACHE HIT (Expired) [Alpha Vantage]: {function} for {symbol} (No API Key Provided)")
                return json.loads(cache_hit.data)

        # If we have no cache at all and no real API key, return empty
        if api_key_to_use == 'demo':
            print(f"⚠️ Skipped Fetching {function} for {symbol} (No Alpha Vantage API Key)")
            return {}

        print(f"FETCHING [Alpha Vantage]: {function} for {symbol} (Using API Key: {'***' if api_key_to_use != 'demo' else 'demo'})")
        
        params = {
            "function": function,
            "apikey": api_key_to_use,
            **kwargs
        }
        
        if function == "CURRENCY_EXCHANGE_RATE":
            params["from_currency"] = "USD"
            params["to_currency"] = "CAD"
        elif function == "NEWS_SENTIMENT":
            params["tickers"] = av_symbol
        else:
            params["symbol"] = av_symbol
            
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            data = resp.json()
            
            # API Limit or Demo Key message
            if "Information" in data or "Note" in data:
                print(f"⚠️ Alpha Vantage System Message for {symbol}: {data.get('Information', data.get('Note'))}")
                # Return old cache if it exists, even if expired
                if cache_hit:
                    return json.loads(cache_hit.data)
                return {}
            
            # Note API Key warning message
            if "Error Message" in data:
                print(f"⚠️ Alpha Vantage Error for {symbol}: {data['Error Message']}")
                if cache_hit:
                    return json.loads(cache_hit.data)
                return {}

            # Cache the successful response
            if data:
                if cache_hit:
                    cache_hit.data = json.dumps(data)
                    cache_hit.updated_at = datetime.utcnow()
                else:
                    new_cache = MarketDataCache(
                        endpoint=function,
                        symbol=symbol,
                        data=json.dumps(data)
                    )
                    db_session.add(new_cache)
                db_session.commit()
                
            # Stagger slightly to not blast 5 req/min tier
            time.sleep(1)
                
            return data
            
        except Exception as e:
            print(f"⚠️ Request failed for {symbol}: {e}")
            if cache_hit:
                return json.loads(cache_hit.data)
            return {}

# -----------------
# DATA ABSTRACTIONS
# -----------------

def get_current_prices_av(symbols):
    prices = {}
    with get_session() as db_session:
        for sym in symbols:
            # 1. Try fetching from Alpha Vantage (which has internal DB cache check)
            data = fetch_av_data("GLOBAL_QUOTE", sym)
            
            try:
                if sym == 'CAD=X':
                    # Currency handles slightly differently
                    rate_data = fetch_av_data("CURRENCY_EXCHANGE_RATE", sym)
                    if 'Realtime Currency Exchange Rate' in rate_data:
                        prices[sym] = float(rate_data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
                        continue
                
                if data and 'Global Quote' in data and '05. price' in data['Global Quote']:
                    prices[sym] = float(data['Global Quote']['05. price'])
                    continue
            except Exception:
                pass
                
            # 2. If API fails, fetch_av_data already tries to return DB MarketDataCache.
            # If we still don't have a price, fall back to the Holding table's purchase price.
            try:
                holding = db_session.exec(
                    select(Holding).where(Holding.symbol == sym)
                ).first()
                if holding and holding.purchase_price:
                    print(f"FALLBACK [Holding Table]: Using purchase price for {sym}")
                    prices[sym] = float(holding.purchase_price)
                else:
                    prices[sym] = 0.0
            except Exception as e:
                print(f"Error during fallback lookup for {sym}: {e}")
                prices[sym] = 0.0
                
    return prices

def get_daily_changes_av(symbols):
    changes = {}
    for sym in symbols:
        if sym == 'CAD=X':
            changes[sym] = 0.0
            continue
        data = fetch_av_data("GLOBAL_QUOTE", sym)
        try:
            changes[sym] = float(data['Global Quote']['10. change percent'].replace('%', ''))
        except Exception:
            changes[sym] = 0.0
    return changes

def get_technical_data_av(symbols):
    technicals = {}
    for sym in symbols:
        if sym == 'CAD=X': continue
        technicals[sym] = {'RSI': 'N/A', 'Signal': 'N/A', 'Scorecard': 'Neutral'}
        
        ts_data = fetch_av_data("TIME_SERIES_DAILY", sym, outputsize="compact")
        try:
            time_series = ts_data.get("Time Series (Daily)", {})
            if not time_series: continue
            
            # Calculate simple technicals natively from price history to save API calls
            dates = sorted(list(time_series.keys()))
            if len(dates) < 50:
                continue
                
            closes = pd.Series([float(time_series[d]['4. close']) for d in dates], index=pd.to_datetime(dates)).sort_index()
            
            # SMA
            sma50 = closes.rolling(50).mean()
            sma200 = closes.rolling(200).mean() if len(closes) >= 200 else None
            
            current = closes.iloc[-1]
            s50 = sma50.iloc[-1]
            
            signal = "Neutral"
            if s50:
                if current > s50: signal = "Above SMA50"
                else: signal = "Below SMA50"
            if sma200 is not None:
                s200 = sma200.iloc[-1]
                if s50 > s200 and current > s50: signal = "📈 Strong Uptrend"
                elif s50 < s200 and current < s50: signal = "📉 Downtrend"

            # RSI 14
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            technicals[sym] = {
                'RSI': round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else "N/A",
                'Signal': signal,
                'Scorecard': 'Neutral'
            }
        except Exception:
            pass
    return technicals

def get_latest_news_av(symbols):
    news = {}
    for sym in symbols:
        data = fetch_av_data("NEWS_SENTIMENT", sym, limit=5)
        try:
            feed = data.get("feed", [])
            if feed:
                top = feed[0]
                headline = top.get('title', 'No Title')
                link = top.get('url', '#')
                if len(headline) > 80: headline = headline[:77] + "..."
                news[sym] = {'headline': f"📰 {headline}", 'link': link}
        except Exception:
            pass
    return news

def get_fundamental_data_av(symbols):
    fundamentals = {}
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
    for sym in symbols:
        if sym in ['CAD=X', 'CASH.TO', 'ETH-USD', 'BTC-USD']:
            fundamentals[sym] = {'Sector': 'Other'}
            continue
            
        # If it's a known ETF or custom mapping, skip hitting OVERVIEW since AV doesn't support ETFs
        if sym in custom_sectors:
            fundamentals[sym] = {'Sector': custom_sectors[sym]}
            continue
            
        data = fetch_av_data("OVERVIEW", sym)
        try:
            if not data or not data.get("Symbol"):
                fundamentals[sym] = {'Sector': 'Unknown'}
                continue
                
            fundamentals[sym] = {
                'Market Cap': data.get('MarketCapitalization', 'N/A'),
                'Trailing P/E': data.get('PERatio', 'N/A'),
                'Forward P/E': data.get('ForwardPE', 'N/A'),
                'PEG Ratio': data.get('PEGRatio', 'N/A'),
                'Rev Growth': data.get('QuarterlyRevenueGrowthYOY', 'N/A'),
                'Profit Margin': data.get('ProfitMargin', 'N/A'),
                '52w High': data.get('52WeekHigh', 'N/A'),
                'Recommendation': 'N/A', # Not provided natively by AV
                'Sector': data.get('Sector', 'Unknown'),
                'Country': data.get('Country', 'Unknown'),
                'Yield': f"{float(data.get('DividendYield', 0)) * 100:.2f}%" if data.get('DividendYield') and data.get('DividendYield') != "None" else "0.00%",
                'Ex-Dividend': data.get('ExDividendDate', 'N/A'),
                'Next Earnings': 'N/A'
            }
        except Exception as e:
            fundamentals[sym] = {'Sector': 'Unknown'}
    return fundamentals

def get_dividend_calendar_av(symbols):
    divs = {}
    
    # Custom ETF skip block to save bandwidth
    custom_sectors = ['VOO', 'XQQ.TO', 'XEI.TO', 'XIU.TO', 'XEF.TO', 'XEC.TO', 'SLV', 'GLD', 'BTC-USD']
    for sym in symbols:
        if sym in custom_sectors or '.TO' in sym: continue
        
        data = fetch_av_data("OVERVIEW", sym)
        try:
            y = data.get('DividendYield')
            if y and y != "None":
                rate = float(data.get('DividendPerShare', 0))
                divs[sym] = {
                    'Frequency': 'Unknown',
                    'Rate': rate,
                    'Months': []
                }
        except: pass
    return divs

def get_portfolio_history_av(holdings_df):
    if holdings_df.empty: return pd.DataFrame()
    symbols = holdings_df['Symbol'].unique().tolist()
    
    closes_dict = {}
    common_dates = None
    
    for sym in symbols:
        ts_data = fetch_av_data("TIME_SERIES_DAILY", sym, outputsize="full")
        try:
            time_series = ts_data.get("Time Series (Daily)", {})
            if time_series:
                dates = sorted(list(time_series.keys()))
                s = pd.Series([float(time_series[d]['4. close']) for d in dates], index=pd.to_datetime(dates)).sort_index()
                closes_dict[sym] = s
                
                # establish a baseline common index
                if common_dates is None:
                    common_dates = s.index
                else:
                    common_dates = common_dates.union(s.index)
        except Exception:
            pass

    if not closes_dict: return pd.DataFrame()
    
    closes = pd.DataFrame(closes_dict, index=common_dates).ffill()
    # Assume static fallback for FX if API limit hit
    fx_rates = pd.Series(1.35, index=closes.index)
    
    portfolio_daily = pd.Series(0.0, index=closes.index)
    holdings_dict = holdings_df.set_index('Symbol')['Quantity'].to_dict()
    
    for sym, qty in holdings_dict.items():
        if sym in closes.columns:
            series = closes[sym].dropna()
            # Align to index
            aligned_series = pd.Series(series, index=closes.index).ffill()
            if not str(sym).endswith('.TO'):
                aligned_series = aligned_series * fx_rates
            portfolio_daily += (aligned_series * qty).fillna(0)
            
    result = pd.DataFrame(index=closes.index)
    result['Portfolio'] = portfolio_daily
    # Benchmarks typically need explicit calls. Let's omit benchmarks to save 3 API calls per refresh.
    
    # filter for past 10 years only
    start_date = datetime.now() - timedelta(days=365*10)
    result = result[result.index >= pd.Timestamp(start_date)]
    
    return result.dropna().reset_index()

def get_av_call_count():
    """
    Returns the number of unique symbols updated in the cache today.
    A proxy for API calls if cache was empty or expired.
    """
    from sqlalchemy import func
    with get_session() as db_session:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = db_session.exec(
            select(func.count(MarketDataCache.symbol))
            .where(MarketDataCache.updated_at >= today_start)
        ).first()
        return count or 0
