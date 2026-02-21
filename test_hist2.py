import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import engine
from sqlmodel import Session, select
from data_loader import load_portfolio_from_db
from market_data import get_portfolio_history
from yahooquery import Ticker
from datetime import datetime, timedelta

df, _ = load_portfolio_from_db()
holdings_df = df
symbols = holdings_df['Symbol'].unique().tolist()
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
benchmarks = ['^GSPC', '^IXIC', '^GSPTSE']
fx_symbol = 'CAD=X'
all_tickers = symbols + benchmarks + [fx_symbol]
    
t = Ticker(all_tickers, asynchronous=True)
hist = t.history(start=start_date)

if isinstance(hist.index, pd.MultiIndex):
    closes = hist.reset_index().pivot(index='date', columns='symbol', values='close')
else:
    closes = hist[['close']].copy()
    closes.columns = [all_tickers[0]]
print("Raw missing values:")
print(closes.isnull().sum())
print("Last 10 dates before ffill:")
print(closes.tail(10))

closes = closes.ffill()
closes.index = pd.to_datetime(closes.index, utc=True)
closes = closes.sort_index()

pd.set_option('display.max_columns', None)
print("After ffill and sort:")
print(closes.tail(10))
