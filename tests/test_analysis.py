import pandas as pd
import pytest
from datetime import datetime, timedelta
from analysis import calculate_metrics

def test_calculate_metrics_cagr_simple_return():
    # Buy 1 share at 100, current is 120 (20% return). 
    # If held for less than 365, should return simple return.
    
    trade_date = datetime.now() - timedelta(days=100) # 100 days
    data = [
        {'Symbol': 'AAPL', 'Trade Date': trade_date, 'Quantity': 1, 'Purchase Price': 100, 'Current Price': 120, 'Commission': 0}
    ]
    df = pd.DataFrame(data)
    df = calculate_metrics(df, target_cagr=0.10)
    
    assert df.iloc[0]['CAGR'] == pytest.approx(0.20) # Simple 20%
    assert df.iloc[0]['Goal Diff'] == pytest.approx(0.10) # 20% - 10% = 10%

def test_calculate_metrics_cagr_annualized():
    # Buy 1 share at 100, current is 120. Held for 2 years (730 days).
    # CAGR = (120/100)^(365/730) - 1 = 1.2^0.5 - 1 = 1.0954 - 1 = 0.0954 (~9.54%)
    
    trade_date = datetime.now() - timedelta(days=730)
    data = [
        {'Symbol': 'AAPL', 'Trade Date': trade_date, 'Quantity': 1, 'Purchase Price': 100, 'Current Price': 120, 'Commission': 0}
    ]
    df = pd.DataFrame(data)
    df = calculate_metrics(df, target_cagr=0.10)
    
    expected_cagr = (120/100)**(0.5) - 1
    assert round(df.iloc[0]['CAGR'], 4) == round(expected_cagr, 4)

def test_calculate_metrics_pnl():
    trade_date = datetime.now() - timedelta(days=100)
    data = [
        {'Symbol': 'AAPL', 'Trade Date': trade_date, 'Quantity': 10, 'Purchase Price': 150, 'Current Price': 170, 'Commission': 10}
    ]
    # Cost = 10 * 150 + 10 = 1510
    # MV = 10 * 170 = 1700
    # PnL = 1700 - 1510 = 190
    
    df = pd.DataFrame(data)
    df = calculate_metrics(df)
    
    assert df.iloc[0]['Market Value'] == 1700
    assert df.iloc[0]['Cost Basis'] == 1510
    assert df.iloc[0]['P&L'] == 190
