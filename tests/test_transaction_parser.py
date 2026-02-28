import pandas as pd
import pytest
from transaction_parser import calculate_holdings, clean_symbol

def test_clean_symbol():
    assert clean_symbol("AAPL") == "AAPL"
    assert clean_symbol("vfv.to", broker="CIBC") == "VFV.TO"
    assert clean_symbol("MSFT US Equity") == "MSFT"
    assert clean_symbol("Bitcoin", description="Bitcoin (BTC)") == "BTC-USD"
    assert clean_symbol("BTC", description="BTC-USD") == "BTC-USD"

def test_calculate_holdings_simple_buy():
    data = [
        {'Symbol': 'AAPL', 'Date': '2023-01-01', 'Action': 'BUY', 'Quantity': 10, 'Price': 150, 'Commission': 5, 'Currency': 'USD', 'Amount': 1505}
    ]
    df_tx = pd.DataFrame(data)
    df_h, realized = calculate_holdings(df_tx)
    
    assert len(df_h) == 1
    assert df_h.iloc[0]['Symbol'] == 'AAPL'
    assert df_h.iloc[0]['Quantity'] == 10
    assert df_h.iloc[0]['Purchase Price'] == 150.5
    assert not realized

def test_calculate_holdings_fifo_sell():
    data = [
        {'Symbol': 'AAPL', 'Date': '2023-01-01', 'Action': 'BUY', 'Quantity': 10, 'Price': 100, 'Commission': 0, 'Currency': 'USD', 'Amount': 1000},
        {'Symbol': 'AAPL', 'Date': '2023-02-01', 'Action': 'BUY', 'Quantity': 10, 'Price': 200, 'Commission': 0, 'Currency': 'USD', 'Amount': 2000},
        {'Symbol': 'AAPL', 'Date': '2023-03-01', 'Action': 'SELL', 'Quantity': 15, 'Price': 250, 'Commission': 0, 'Currency': 'USD', 'Amount': 3750},
    ]
    # FIFO: Sells first 10 @ 100, next 5 @ 200.
    # Total cost for 15 shares = (10 * 100) + (5 * 200) = 1000 + 1000 = 2000.
    # Total proceeds = 3750.
    # Realized PnL = 3750 - 2000 = 1750.
    # Remaining: 5 shares at 200.
    
    df_tx = pd.DataFrame(data)
    df_h, realized = calculate_holdings(df_tx)
    
    assert len(df_h) == 1
    assert df_h.iloc[0]['Quantity'] == 5
    assert df_h.iloc[0]['Purchase Price'] == 200.0
    
    key = ('AAPL', None, None)
    assert realized[key]['USD'] == 1750.0

def test_calculate_holdings_empty():
    df_h, realized = calculate_holdings(pd.DataFrame())
    assert df_h.empty
    assert not realized
