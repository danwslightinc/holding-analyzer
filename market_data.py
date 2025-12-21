import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

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
    Fetches real-time prices for a list of symbols using yfinance.
    Returns a dictionary {symbol: price}.
    """
    if not symbols:
        return {}

    # yfinance allows fetching multiple tickers at once
    # e.g. "AAPL MSFT GOOG"
    tickers_str = " ".join(symbols)
    
    print(f"Fetching prices for: {tickers_str}...")
    
    try:
        data = yf.download(tickers_str, period="5d", progress=False, auto_adjust=False)
        
        prices = {}
        
        if len(symbols) == 1:
             # Single symbol case
             # data['Close'] is a Series or DataFrame depending on yfinance version
             closes = data['Close']
             if isinstance(closes, pd.DataFrame):
                 val = closes.ffill().iloc[-1].iloc[0] # Take first col
             else:
                 val = closes.ffill().iloc[-1]
             prices[symbols[0]] = float(val)
        else:
            # Multiple symbols
            # data['Close'] is DataFrame with Tickers as columns
            closes = data['Close'].ffill().iloc[-1]
            for sym in symbols:
                if sym in closes:
                    prices[sym] = float(closes[sym])
                else:
                    print(f"Warning: No price found for {sym}")
                    prices[sym] = 0.0

        return prices

    except Exception as e:
        print(f"Error fetching prices: {e}")
        return {}

def get_weekly_changes(symbols):
    """
    Fetches 5-day history and calculates % change.
    Returns dict: {Symbol: percent_change_float}
    """
    if not symbols: return {}
    
    tickers_str = " ".join(symbols)
    try:
        data = yf.download(tickers_str, period="5d", progress=False, auto_adjust=False)
        closes = data['Close']
        
        changes = {}
        
        if len(symbols) == 1:
            # Series case
            if len(closes) >= 2:
                start = float(closes.iloc[0])
                end = float(closes.iloc[-1])
                changes[symbols[0]] = (end - start) / start
        else:
            # DataFrame case
            closes = closes.ffill() # Fill missing
            for sym in symbols:
                if sym in closes:
                    series = closes[sym].dropna()
                    if len(series) >= 2:
                        start = float(series.iloc[0])
                        end = float(series.iloc[-1])
                        changes[sym] = (end - start) / start
                    else:
                        changes[sym] = 0.0
        return changes
                        
    except Exception as e:
        print(f"Error fetching weekly changes: {e}")
        return {}

def get_usd_to_cad_rate():
    """
    Fetches the current USD to CAD exchange rate.
    Uses 'CAD=X' from Yahoo Finance.
    """
    try:
        data = yf.download("CAD=X", period="1d", progress=False, auto_adjust=False)
        if not data.empty:
            closing_data = data['Close'].iloc[-1]
            # Handle case where result is a Series (future yfinance/pandas behavior)
            if hasattr(closing_data, 'iloc'):
                return float(closing_data.iloc[0])
            return float(closing_data)
        return 1.40 # Fallback estimate if API fails
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return 1.40

def get_market_indices_change():
    """
    Fetches 5-day % change for S&P 500, NASDAQ, and TSX.
    Returns dict: {Index Name: percent_change_float}
    """
    indices = {
        '^GSPC': '🇺🇸 S&P 500',
        '^IXIC': '🇺🇸 NASDAQ',
        '^GSPTSE': '🇨🇦 TSX'
    }
    
    tickers_str = " ".join(indices.keys())
    try:
        data = yf.download(tickers_str, period="5d", progress=False, auto_adjust=False)
        closes = data['Close']
        
        changes = {}
        closes = closes.ffill()
        
        for symbol, name in indices.items():
            if symbol in closes:
                series = closes[symbol].dropna()
                if len(series) >= 2:
                    start = float(series.iloc[0])
                    end = float(series.iloc[-1])
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

def get_technical_data(symbols):
    """
    Fetches 3-month history and calculates RSI.
    Returns dict: {Symbol: {'RSI': float_val}}
    """
    if not symbols: return {}

    technical_data = {}
    print(f"Fetching technical data (RSI) for {len(symbols)} symbols...")
    
    # We need enough days for 14-day rolling window
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    tickers_str = " ".join(symbols)
    
    try:
        data = yf.download(tickers_str, start=start_date, progress=False, auto_adjust=False)
        closes = data['Close']
        
        if len(symbols) == 1:
            # Single symbol
            # closes is typically a Series or single-col DF
            if isinstance(closes, pd.DataFrame):
                 series = closes.iloc[:, 0]
            else:
                 series = closes
            
            rsi = calculate_rsi(series)
            technical_data[symbols[0]] = {'RSI': rsi}
            
        else:
            # Multi symbol
            # closes is a DF with tickers as columns
            for sym in symbols:
                if sym in closes:
                    series = closes[sym].dropna()
                    if len(series) > 14:
                        rsi = calculate_rsi(series)
                        technical_data[sym] = {'RSI': rsi}
                    else:
                         technical_data[sym] = {'RSI': 'N/A'}
    except Exception as e:
        print(f"Error calculating technicals: {e}")
        
    return technical_data

def get_latest_news(symbols):
    """
    Fetches the latest news headline for each symbol.
    Returns dict: {Symbol: 'News: Headline'}
    """
    if not symbols: return {}

    print(f"Fetching latest news for {len(symbols)} symbols...")
    news_map = {}
    
    def fetch_news(sym):
        try:
            # yfinance news
            items = yf.Ticker(sym).news
            if items and isinstance(items, list) and len(items) > 0:
                # Get most recent
                top_story = items[0]
                content = top_story.get('content', top_story)
                title = content.get('title', 'No Title')
                
                # Extract Link
                link = content.get('link')
                if not link:
                    click = content.get('clickThroughUrl')
                    if click: link = click.get('url')
                if not link:
                    canon = content.get('canonicalUrl')
                    if canon: link = canon.get('url')
                
                if not link:
                    link = f"https://finance.yahoo.com/quote/{sym}"
                
                # Truncate title if too long (max 80 chars)
                if len(title) > 80:
                    title = title[:77] + "..."
                    
                return sym, {'headline': f"📰 {title}", 'link': link}
        except Exception:
            pass
        return sym, None

    # Use ThreadPool to fetch parallelly (I/O bound)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_sym = {executor.submit(fetch_news, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(future_to_sym):
            sym, headline = future.result()
            if headline:
                news_map[sym] = headline
                
    return news_map

def get_fundamental_data(symbols):
    """
    Fetches fundamental data for a list of symbols.
    Returns a dict: {Symbol: { 'pe_ratio': val, 'revenue_growth': val, ... } }
    """
    if not symbols: return {}
    
    fundamentals = {}
    print(f"Fetching fundamentals for {len(symbols)} symbols...")
    
    # Custom mappings for ETFs/Crypto that don't have standard sectors
    custom_sectors = {
        'VOO': 'US Broad Market',
        'XQQ.TO': 'US Technology',
        'XEI.TO': 'Canadian Dividends',
        'XIU.TO': 'Canadian Broad Market',
        'XEF.TO': 'International Developed',
        'XEC.TO': 'Emerging Markets',
        'SLV': 'Commodities',
        'BTC-USD': 'Crypto',
        'ETH-USD': 'Crypto',
        'CAD=X': 'Currency',
        'CASH.TO': 'Cash & Equivalents'
    }

    for sym in symbols:
        try:
            # Skip CAD=X if not needed, or classify it
            if '=' in sym and sym not in custom_sectors:
                continue
                
            ticker = yf.Ticker(sym)
            info = ticker.info
            
            # Determine Sector
            sector = info.get('sector', 'N/A')
            quote_type = info.get('quoteType', 'N/A')
            
            # Use custom mapping if available, otherwise fallback to Yahoo data
            if sym in custom_sectors:
                normalized_sector = custom_sectors[sym]
            elif quote_type == 'ETF':
                # Try to use category, or fallback to 'Other ETF'
                cat = info.get('category', 'N/A')
                normalized_sector = cat if cat != 'N/A' else 'Other ETF'
            elif quote_type == 'CRYPTOCURRENCY':
                normalized_sector = 'Crypto'
            else:
                # Use standard sector for equities
                normalized_sector = sector
                
            # Extract Catalyst Data
            # 1. Dividend Yield
            div_yield = info.get('dividendYield', 0)
            yield_str = f"{div_yield:.2f}%" if div_yield else "0.00%"
            
            # 2. Ex-Dividend Date
            ex_div = info.get('exDividendDate', 'N/A')
            if isinstance(ex_div, (int, float)):
                ex_div = datetime.fromtimestamp(ex_div).strftime('%Y-%m-%d')
            
            # 3. Next Earnings (Only for equities)
            # 3. Next Earnings (Only for equities)
            next_earnings = 'N/A'
            try:
                if quote_type == 'EQUITY': 
                    dates = []
                    now = datetime.now()
                    
                    # approach 1: calendar property
                    cal = ticker.calendar
                    if cal is not None:
                        if isinstance(cal, dict) and 'Earnings Date' in cal:
                            dates = cal['Earnings Date']
                        elif hasattr(cal, 'get'):
                            dates = cal.get('Earnings Date', [])
                    
                    # approach 2: get_earnings_dates() dataframe
                    if not dates:
                        edt = ticker.get_earnings_dates(limit=6)
                        if edt is not None and not edt.empty:
                            dates = edt.index.tolist()
                            
                    # Clean and Filter
                    valid_dates = []
                    now_date = datetime.now().date()
                    
                    for d in dates:
                        # Handle Timestamp (pandas) -> datetime
                        if hasattr(d, 'to_pydatetime'):
                            d = d.to_pydatetime()
                        
                        # Convert datetime -> date
                        current_date = d
                        if isinstance(d, datetime):
                            current_date = d.date()
                        
                        # Check strictly future
                        if current_date > now_date:
                            valid_dates.append(current_date)
                            
                    if valid_dates:
                        next_earnings = min(valid_dates).strftime('%Y-%m-%d')
            except Exception:
                pass

            # Extract PEG (Official or Fallback)
            peg = info.get('pegRatio') or info.get('trailingPegRatio')
            
            # Fallback: Calculate Synthetic PEG if missing (common for TSX stocks)
            if peg is None and quote_type == 'EQUITY':
                try:
                    # Fetch growth estimates (Next Year)
                    estimates = ticker.growth_estimates
                    if estimates is not None and not estimates.empty:
                        # Prioritize +1y (Next Year) or +5y (LTG)
                        # Index is typically: 0q, +1q, 0y, +1y, +5y, LTG
                        growth_rate = None
                        
                        if '+1y' in estimates.index:
                            growth_rate = estimates.loc['+1y', 'stockTrend']
                        elif 'LTG' in estimates.index:
                            growth_rate = estimates.loc['LTG', 'stockTrend']
                            
                        # If we found a valid positive growth rate
                        if growth_rate and growth_rate > 0:
                            pe_val = info.get('forwardPE') or info.get('trailingPE')
                            if pe_val:
                                peg = pe_val / (growth_rate * 100)
                except Exception:
                    pass # Fail silently and keep it None/N/A

            # Extract key metrics
            f_data = {
                'Market Cap': info.get('marketCap', 'N/A'),
                'Trailing P/E': info.get('trailingPE', 'N/A'),
                'Forward P/E': info.get('forwardPE', 'N/A'),
                'PEG Ratio': peg if peg is not None else 'N/A',
                'Rev Growth': info.get('revenueGrowth', 'N/A'), # yoy
                'Profit Margin': info.get('profitMargins', 'N/A'),
                '52w High': info.get('fiftyTwoWeekHigh', 'N/A'),
                'Recommendation': info.get('recommendationKey', 'N/A').replace('_', ' ').title(),
                'Sector': normalized_sector,
                'Yield': yield_str,
                'Ex-Dividend': str(ex_div),
                'Next Earnings': str(next_earnings)
            }
            fundamentals[sym] = f_data
            
        except Exception as e:
            print(f"Error fetching fundamentals for {sym}: {e}")
            fundamentals[sym] = {'Error': str(e), 'Sector': 'Unknown'}
            
    return fundamentals
