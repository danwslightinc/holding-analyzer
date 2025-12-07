import yfinance as yf

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
        data = yf.download(tickers_str, period="5d", progress=False)
        
        # 'data' is a DataFrame. We need the latest 'Close' price.
        # If single symbol, structure is different than multiple.
        # Actually yf.download returns a MultiIndex columns if multiple symbols.
        
        prices = {}
        
        # Handle case where only 1 symbol is requested
        if len(symbols) == 1:
            symbol = symbols[0]
            # yfinance returns different shape if 1 symbol. 
            # Columns are just Open, High, Low, Close...
            # But wait, yf.download in recent versions might still be complex.
            # Safest is to use Ticker if just one, but download is faster for batch.
            
            # Let's try to access the last row's 'Close'
            # Check if 'Close' is in columns
            if 'Close' in data.columns:
                 # It's a Series if single symbol, or DF if multi.
                 # Actually, usually for single symbol it returns a DF with Index Date.
                 current_price = data['Close'].iloc[-1]
                 # If it's a scalar it's float, if Series (multi-index?)
                 # Let's handle the complexity by checking type or just using Ticker for simplicity for now?
                 # Batch download is nicer. 
                 
                 # .iloc[-1] gives the last row (latest date).
                 # If MultiIndex columns (Price, Ticker), we iterate.
                 pass
        
        # Let's use Tickers module for easier dict access if download is tricky with shapes
        # But download is faster.
        # Alternative: data['Close'] returns a DF with columns as Tickers.
        
        if len(symbols) == 1:
             # Single symbol case
             # data['Close'] is a Series or DataFrame depending on yfinance version
             # If Series, ffill().iloc[-1] works
             # If DataFrame (it shouldn't be for 1 ticker usually?), check columns
             closes = data['Close']
             if isinstance(closes, pd.DataFrame):
                 # This happens if multi-level index or something weird
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
        data = yf.download(tickers_str, period="5d", progress=False)
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
        data = yf.download("CAD=X", period="1d", progress=False)
        if not data.empty:
            return float(data['Close'].iloc[-1])
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
        data = yf.download(tickers_str, period="5d", progress=False)
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
