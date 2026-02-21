import pandas as pd
import json
import os
from datetime import datetime
from transaction_parser import load_all_transactions, calculate_holdings

def parse_date(val):
    """Parse Trade Date (support both YYYYMMDD and YYYY/MM/DD)"""
    d_str = str(val).split('.')[0].strip()
    if not d_str or d_str == 'nan' or d_str == 'NaT':
        return pd.NaT
    try:
        if len(d_str) == 8 and d_str.isdigit():
            return pd.to_datetime(d_str, format='%Y%m%d')
        return pd.to_datetime(d_str)
    except:
        return pd.NaT

def load_portfolio_holdings(filepath):
    """
    Reads the portfolio CSV file and/or transaction history directory.
    Combines duplicate symbols and returns (DataFrame, realized_pnl_map).
    """
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    realized_pnl = {}
    lots_history = {}
    
    # 1. Parse Transaction History
    tx_dir = "transactions"
    if os.path.exists(tx_dir):
        print(f"Detected transaction history in '{tx_dir}'. Parsing for enrichment...")
        df_tx = load_all_transactions(tx_dir)
        if not df_tx.empty:
            # We want the raw lots and realized pnl
            df_h_holdings, pnl_map = calculate_holdings(df_tx)
            realized_pnl = pnl_map
            
            # Group history lots by symbol
            for _, row in df_h_holdings.iterrows():
                sym = row['Symbol']
                if sym not in lots_history: lots_history[sym] = []
                lots_history[sym].append(row)

    # 2. Load Manual Portfolio
    merged_lots = []
    try:
        if os.path.exists(filepath):
            df_manual = pd.read_csv(filepath)
            
            # Clean mental columns first
            for col in mental_cols:
                if col not in df_manual.columns: df_manual[col] = ""
                df_manual[col] = df_manual[col].astype(str).replace('nan', '')

            # Parse dates early
            df_manual['Trade Date'] = df_manual['Trade Date'].apply(parse_date)
            
            # Normalize symbols before grouping
            df_manual['Symbol'] = df_manual['Symbol'].str.strip().str.upper()
            
            # Group manual entries by symbol to compare quantities
            manual_groups = df_manual.groupby('Symbol')
            
            for sym, group in manual_groups:
                sym_upper = sym.strip().upper()
                m_qty = group['Quantity'].sum()
                h_lots = lots_history.get(sym_upper, [])
                h_qty = sum([float(l['Quantity']) for l in h_lots]) if h_lots else 0
                
                # Take first set of mental data
                mental_data = {col: str(group.iloc[0][col]) for col in mental_cols}
                
                if h_qty > 0:
                    # We have history. Use it to enrich.
                    if h_qty >= m_qty * 0.99: # Allowing a tiny tolerance for rounding
                        # History is complete (or more than manual). Use all history lots.
                        for l in h_lots:
                            l_dict = l.to_dict()
                            l_dict.update(mental_data)
                            merged_lots.append(l_dict)
                    else:
                        # History is partial. Use all history lots + remainder from manual.
                        for l in h_lots:
                            l_dict = l.to_dict()
                            l_dict.update(mental_data)
                            merged_lots.append(l_dict)
                        
                        # Add remaining quantity from manual
                        rem_qty = m_qty - h_qty
                        # Use weighted average price of manual entries for the remainder
                        avg_price = (group['Purchase Price'] * group['Quantity']).sum() / m_qty
                        merged_lots.append({
                            'Symbol': sym_upper,
                            'Trade Date': group['Trade Date'].min(),
                            'Quantity': rem_qty,
                            'Purchase Price': avg_price,
                            'Commission': 0.0,
                            'Currency': 'CAD' if sym_upper.endswith('.TO') else 'USD',
                            **mental_data
                        })
                else:
                    # No history. Use manual entries.
                    for _, row in group.iterrows():
                        l_dict = {
                            'Symbol': sym_upper,
                            'Trade Date': row['Trade Date'],
                            'Quantity': row['Quantity'],
                            'Purchase Price': row['Purchase Price'],
                            'Commission': row['Commission'],
                            'Currency': 'CAD' if sym_upper.endswith('.TO') else 'USD',
                        }
                        l_dict.update({col: row[col] for col in mental_cols})
                        merged_lots.append(l_dict)
                        
            # Skip discovery loop: Symbols in history NOT in manual are now ignored
            # to give the user full control via portfolio.csv.
            # (Previously symbols in history were added automatically)
            pass
    except Exception as e:
        print(f"Warning: Error merging lots: {e}")
        # Fallback to just history if manual fails
        for sym, h_lots in lots_history.items():
            for l in h_lots: merged_lots.append(l.to_dict())

    if not merged_lots:
        return pd.DataFrame(), {}
        
    df = pd.DataFrame(merged_lots)
    
    # 3. Apply Thesis JSON overrides (Existing logic)
    thesis_path = "thesis.json"
    # The logic continues normally below

    # Select necessary columns
    base_cols = ['Symbol', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date']
    
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
    available_cols = aggregated.columns.tolist()
    desired_cols = ['Symbol', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols
    cols = [c for c in desired_cols if c in available_cols]
    aggregated = aggregated[cols]

    return aggregated, realized_pnl
