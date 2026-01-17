import pandas as pd
import json
import os
from datetime import datetime

def load_portfolio_holdings(filepath):
    """
    Reads the portfolio CSV file and returns a DataFrame with cleaned columns.
    Combines duplicate symbols by calculating weighted average purchase price.
    Merges persistent Quant-Mental data from 'thesis.json'.
    """
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return pd.DataFrame()

    # Select necessary columns
    base_cols = ['Symbol', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date']
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    
    # Check if base columns exist
    missing = [c for c in base_cols if c not in df.columns]
    if missing:
        print(f"Error: Missing columns in CSV: {missing}")
        return pd.DataFrame()

    # Add mental columns if missing
    for col in mental_cols:
        if col not in df.columns:
            df[col] = ""

    # Clean data types
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    df['Purchase Price'] = pd.to_numeric(df['Purchase Price'], errors='coerce').fillna(0.0)
    df['Commission'] = pd.to_numeric(df['Commission'], errors='coerce').fillna(0.0)
    
    # Handle Transaction Type (Buy/Sell)
    # If "Sell", treat quantity as negative for aggregation
    if 'Transaction Type' in df.columns:
        df['Quantity'] = df.apply(
            lambda x: -abs(x['Quantity']) if str(x['Transaction Type']).strip().lower() == 'sell' else abs(x['Quantity']),
            axis=1
        )
    
    # Ensure mental columns are strings
    for col in mental_cols:
        df[col] = df[col].astype(str).replace('nan', '')

    # --- MERGE THESIS DATA (Persistent Storage) ---
    thesis_path = "thesis.json"
    if os.path.exists(thesis_path):
        try:
            with open(thesis_path, "r") as f:
                metadata = json.load(f)
            
            # Apply metadata to dataframe (JSON overrides CSV if present)
            for col in mental_cols:
                # Create mapper: {Symbol: Value}
                mapper = {sym: data.get(col, None) for sym, data in metadata.items()}
                # Remove None entries to allow CSV fallback
                mapper = {k: v for k, v in mapper.items() if v is not None}
                
                if mapper:
                    # distinct logic: map returns NaN for missing keys.
                    # combine_first: if series is null, take from other.
                    # We want JSON to take precedence.
                    json_series = df['Symbol'].map(mapper)
                    df[col] = json_series.combine_first(df[col]).fillna('')
                    
        except Exception as e:
            # Fallback: Try `ast.literal_eval` to support python-dict style (single quotes)
            # This is helpful if the user pasted a Python dict into the secret
            try:
                import ast
                with open(thesis_path, "r") as f:
                    content = f.read()
                metadata = ast.literal_eval(content)
                
                # Apply metadata (duplicate logic, could be refactored)
                for col in mental_cols:
                    mapper = {sym: data.get(col, None) for sym, data in metadata.items()}
                    mapper = {k: v for k, v in mapper.items() if v is not None}
                    if mapper:
                        json_series = df['Symbol'].map(mapper)
                        df[col] = json_series.combine_first(df[col]).fillna('')
                        
                print("Warning: thesis.json loaded via ast.literal_eval (invalid JSON but valid Python dict)")
                
            except Exception as e2:
                print(f"Warning: Failed to load thesis.json: {e}. Fallback also failed: {e2}")

    # Parse Trade Date (support both YYYYMMDD and YYYY/MM/DD)
    def parse_date(val):
        d_str = str(val).split('.')[0].strip()
        if not d_str or d_str == 'nan':
            return pd.NaT
        try:
            if len(d_str) == 8 and d_str.isdigit():
                return pd.to_datetime(d_str, format='%Y%m%d')
            return pd.to_datetime(d_str)
        except:
            return pd.NaT

    df['Trade Date'] = df['Trade Date'].apply(parse_date)

    # Remove rows with invalid dates
    df = df.dropna(subset=['Trade Date'])

    # Combine duplicate symbols with weighted average cost
    # Calculate cost basis for each row first
    df['Cost Basis'] = (df['Purchase Price'] * df['Quantity']) + df['Commission']
    
    # Group by symbol and aggregate
    agg_rules = {
        'Quantity': 'sum',  # Total shares
        'Cost Basis': 'sum',  # Total cost
        'Commission': 'sum',  # Total commissions
        'Trade Date': 'min',  # Earliest purchase date for CAGR calculation
    }
    # Add rules for mental columns
    for col in mental_cols:
        agg_rules[col] = 'first' # Take the first non-empty value if possible

    aggregated = df.groupby('Symbol').agg(agg_rules).reset_index()
    
    # Remove assets with 0 net quantity (closed positions)
    aggregated = aggregated[aggregated['Quantity'] > 0]
    
    # Calculate weighted average purchase price
    # Weighted Avg Price = (Total Cost - Total Commission) / Total Quantity
    aggregated['Purchase Price'] = (aggregated['Cost Basis'] - aggregated['Commission']) / aggregated['Quantity']
    
    # Drop the temporary Cost Basis column
    aggregated = aggregated.drop('Cost Basis', axis=1)
    
    # Reorder columns to match expected format
    aggregated = aggregated[['Symbol', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols]

    return aggregated
