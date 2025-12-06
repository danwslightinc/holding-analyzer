import pandas as pd
from datetime import datetime

def load_portfolio_holdings(filepath):
    """
    Reads the portfolio CSV file and returns a DataFrame with cleaned columns.
    Expected columns: Symbol, Purchase Price, Quantity, Commission, Trade Date
    """
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return pd.DataFrame()

    # Select necessary columns
    required_cols = ['Symbol', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date']
    
    # Check if all columns exist
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"Error: Missing columns in CSV: {missing}")
        return pd.DataFrame()

    df = df[required_cols].copy()

    # Clean data types
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    df['Purchase Price'] = pd.to_numeric(df['Purchase Price'], errors='coerce').fillna(0.0)
    df['Commission'] = pd.to_numeric(df['Commission'], errors='coerce').fillna(0.0)

    # Parse Trade Date (format 20251205 -> YYYYMMDD based on sample)
    # Sample: 20251205, 20251125
    df['Trade Date'] = pd.to_datetime(df['Trade Date'], format='%Y%m%d', errors='coerce')

    # Remove rows with invalid dates or 0 quantity
    df = df.dropna(subset=['Trade Date'])
    df = df[df['Quantity'] > 0]

    return df
