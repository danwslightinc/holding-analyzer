import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

# Import the module under test. 
# We need to make sure backend path mapping works, 
# but tests are at the same level as app right now
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.api import get_closed_trades

@patch('backend.api.get_current_prices')
@patch('backend.api.get_processed_transactions')
@patch('backend.api.Session')
def test_get_closed_trades_account_segregation(mock_session, mock_get_tx, mock_prices):
    # Mock prices
    mock_prices.return_value = {'TEST': 30.0}
    # Create a dummy dataframe representing a scenario where:
    # 1. We buy 100 shares in Account A for $10
    # 2. We buy 100 shares in Account B for $20
    # 3. We sell 50 shares in Account B for $25
    # The cost basis for the sale should be based on Account B's $20 cost, not Account A's $10 cost.
    
    df_data = pd.DataFrame([
        {
            'Symbol': 'TEST', 'Broker': 'Bank1', 'Account_Type': 'TFSA',
            'Action': 'BUY', 'Date': pd.to_datetime('2023-01-01'), 'Currency': 'CAD',
            'Quantity': 100, 'Price': 10, 'Commission': 0, 'Amount': -1000,
            'Portfolio_Category': 'Retirement'
        },
        {
            'Symbol': 'TEST', 'Broker': 'Bank2', 'Account_Type': 'RRSP',
            'Action': 'BUY', 'Date': pd.to_datetime('2023-02-01'), 'Currency': 'CAD',
            'Quantity': 100, 'Price': 20, 'Commission': 0, 'Amount': -2000,
            'Portfolio_Category': 'Retirement'
        },
        {
            'Symbol': 'TEST', 'Broker': 'Bank2', 'Account_Type': 'RRSP',
            'Action': 'SELL', 'Date': pd.to_datetime('2023-03-01'), 'Currency': 'CAD',
            'Quantity': 50, 'Price': 25, 'Commission': 0, 'Amount': 1250,
            'Portfolio_Category': 'Retirement'
        }
    ])
    
    mock_get_tx.return_value = df_data
    
    all_trades = get_closed_trades()
    trades = [t for t in all_trades if t['sellDate'] != 'OPEN']
    
    assert len(trades) == 1
    trade = trades[0]
    
    assert trade['symbol'] == 'TEST'
    assert trade['broker'] == 'Bank2'
    assert trade['account_type'] == 'RRSP'
    assert trade['quantity'] == 50.0
    assert trade['costBasis'] == 1000.0
    assert trade['proceeds'] == 1250.0
    assert trade['pnl'] == 250.0

@patch('backend.api.get_current_prices')
@patch('backend.api.get_processed_transactions')
@patch('backend.api.Session')
def test_get_closed_trades_symbol_exclusion(mock_session, mock_get_tx, mock_prices):
    # Mock prices
    mock_prices.return_value = {'AAPL': 200.0, 'RBF526': 20.0}
    # Test that symbols like RBF526 and DLR do not calculate PnL
    df_data = pd.DataFrame([
        {
            'Symbol': 'RBF526', 'Broker': 'Bank1', 'Account_Type': 'TFSA',
            'Action': 'BUY', 'Date': pd.to_datetime('2023-01-01'), 'Currency': 'CAD',
            'Quantity': 100, 'Price': 10, 'Commission': 0, 'Amount': -1000,
            'Portfolio_Category': 'Retirement'
        },
        {
            'Symbol': 'RBF526', 'Broker': 'Bank1', 'Account_Type': 'TFSA',
            'Action': 'SELL', 'Date': pd.to_datetime('2023-02-01'), 'Currency': 'CAD',
            'Quantity': 100, 'Price': 15, 'Commission': 0, 'Amount': 1500,
            'Portfolio_Category': 'Retirement'
        },
        {
            'Symbol': 'AAPL', 'Broker': 'Bank1', 'Account_Type': 'TFSA',
            'Action': 'BUY', 'Date': pd.to_datetime('2023-01-01'), 'Currency': 'USD',
            'Quantity': 10, 'Price': 100, 'Commission': 0, 'Amount': -1000,
            'Portfolio_Category': 'Retirement'
        },
        {
            'Symbol': 'AAPL', 'Broker': 'Bank1', 'Account_Type': 'TFSA',
            'Action': 'SELL', 'Date': pd.to_datetime('2023-02-01'), 'Currency': 'USD',
            'Quantity': 10, 'Price': 150, 'Commission': 0, 'Amount': 1500,
            'Portfolio_Category': 'Retirement'
        }
    ])
    
    mock_get_tx.return_value = df_data
    
    all_trades = get_closed_trades()
    trades = [t for t in all_trades if t['sellDate'] != 'OPEN']
    
    # RBF526 should be completely skipped. Only AAPL should show up.
    assert len(trades) == 1
    assert trades[0]['symbol'] == 'AAPL'
    assert trades[0]['pnl'] == 500.0
