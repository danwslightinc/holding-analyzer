import pandas as pd
import json
import os
import pytest
from data_loader import load_portfolio_from_csv

def test_load_portfolio_from_csv_no_file(mocker):
    mocker.patch("os.path.exists", return_value=False)
    df, pnl = load_portfolio_from_csv()
    assert df.empty
    assert not pnl

def test_load_portfolio_from_csv_with_data(mocker, tmp_path):
    # Mock portfolio.csv content
    csv_content = (
        "Symbol,Trade Date,Purchase Price,Quantity,Commission,Comment\n"
        "AAPL,20230101,150,10,5,RBC RRSP\n"
        "MSFT,20230101,300,5,0,CIBC TFSA\n"
    )
    p = tmp_path / "portfolio.csv"
    p.write_text(csv_content)
    
    # Mock thesis.json content
    thesis_data = {
        "AAPL": {"Thesis": "Good stock", "Conviction": "High"}
    }
    t = tmp_path / "thesis.json"
    t.write_text(json.dumps(thesis_data))
    
    # Mock CWD to tmp_path or mock paths
    mocker.patch("os.path.exists", side_effect=lambda x: True if "portfolio.csv" in x or "thesis.json" in x else False)
    mocker.patch("data_loader.pd.read_csv", return_value=pd.read_csv(p))
    
    # Mocking open for json.load
    mock_open = mocker.mock_open(read_data=json.dumps(thesis_data))
    mocker.patch("builtins.open", mock_open)

    df, pnl = load_portfolio_from_csv()
    
    assert len(df) == 2
    assert "AAPL" in df['Symbol'].values
    assert df[df['Symbol'] == 'AAPL'].iloc[0]['Broker'] == "RBC"
    assert df[df['Symbol'] == 'AAPL'].iloc[0]['Thesis'] == "Good stock"
