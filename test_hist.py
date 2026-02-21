import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import engine
from sqlmodel import Session, select
from data_loader import load_portfolio_from_db
from market_data import get_portfolio_history

df, _ = load_portfolio_from_db()
hist = get_portfolio_history(df)
print(hist.tail(10))
