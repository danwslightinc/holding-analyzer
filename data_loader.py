import pandas as pd
import json
import os
from datetime import datetime
from sqlmodel import Session, select
from transaction_parser import load_all_transactions, calculate_holdings

# Import DB internal modules with absolute or relative paths depending on how it's called
try:
    from backend.database import engine, create_db_and_tables
    from backend.models import Holding, Transaction, InvestmentThesis
    from backend.cache import cache_result, portfolio_cache
except ImportError:
    # Fallback for scripts running from root
    from .backend.database import engine, create_db_and_tables
    from .backend.models import Holding, Transaction, InvestmentThesis
    from .backend.cache import cache_result, portfolio_cache

@cache_result(portfolio_cache)
def load_portfolio_from_db():
    """
    Loads portfolio data from the SQL database and returns it in a format 
    compatible with the existing analysis logic.
    """
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    
    # Ensure tables exist
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Fetch Holdings
        holdings = session.exec(select(Holding)).all()
        
        # 2. Fetch all transactions for P&L calculation
        # We can reuse calculate_holdings but we need to convert DB objects to DF
        transactions = session.exec(select(Transaction)).all()
        
        if not transactions:
            return pd.DataFrame(), {}
            
        # Normalize type strings to the canonical action values expected by calculate_holdings
        TYPE_NORMALIZE = {
            'Buy': 'BUY',
            'BUY': 'BUY',
            'Sell': 'SELL',
            'SELL': 'SELL',
            'DRIP': 'BUY',       # Dividend Reinvestment → treated as a BUY
            'Dividend': 'DIV',
            'DIV': 'DIV',
            'Transf In': 'BUY',
            'Transfer In': 'BUY',
        }

        data = []
        for tx in transactions:
            data.append({
                'Symbol': tx.symbol,
                'Date': tx.date,
                'Action': TYPE_NORMALIZE.get(tx.type, tx.type.upper()),
                'Quantity': tx.quantity,
                'Price': tx.price,
                'Commission': tx.commission,
                'Amount': tx.amount,
                'Currency': tx.currency,
                'Description': tx.description,
                'Broker': tx.broker,
                'Account_Type': tx.account_type,
                'Source': tx.source
            })
        
        df_tx = pd.DataFrame(data)
        df_h_holdings, realized_pnl = calculate_holdings(df_tx)
        
        # 3. Enrich with Mental Data from InvestmentThesis table
        theses = session.exec(select(InvestmentThesis)).all()
        
        # Create map of symbol -> mental data
        mental_map = {t.symbol: {
            'Thesis': t.thesis or "",
            'Catalyst': "", # Placeholder, potentially add field in future
            'Kill Switch': t.kill_switch or "",
            'Conviction': t.conviction or "",
            'Timeframe': t.timeframe or ""
        } for t in theses}
        
        # Special case: Catalyst might be news-fetched, but we check if it's in the DB
        # Actually, if Catalyst isn't in the Holding model, we'll let the API handle it as before.
        
        # 4. Combine and Enrich
        # We start with the calculated holdings from transactions
        rows = []
        processed_keys = set()
        
        # Create a map for quick lookup of manual holdings
        manual_holdings_map = { (h.symbol, h.broker, h.account_type): h for h in holdings }

        for _, r in df_h_holdings.iterrows():
            sym = r['Symbol']
            broker = r.get('Broker')
            account = r.get('Account_Type')
            key = (sym, broker, account)
            
            d = r.to_dict()
            
            # OVERRIDE with manual entry if exists for this specific account
            if key in manual_holdings_map:
                h = manual_holdings_map[key]
                if h.quantity is not None:
                    d['Quantity'] = float(h.quantity)
                if h.purchase_price is not None:
                    d['Purchase Price'] = float(h.purchase_price)
                if h.trade_date:
                    d['Trade Date'] = h.trade_date
                if h.commission is not None:
                    d['Commission'] = float(h.commission)

            # Attach thesis data if it exists
            d.update(mental_map.get(sym, {
                'Thesis': "", 'Catalyst': "", 'Kill Switch': "", 
                'Conviction': "", 'Timeframe': ""
            }))
            rows.append(d)
            processed_keys.add(key)
            
        # Add manual entries from Holding table that weren't in transactions
        for key, h in manual_holdings_map.items():
            if key in processed_keys:
                continue
            
            if h.quantity and h.quantity > 0:
                d = {
                    'Symbol': h.symbol,
                    'Broker': h.broker,
                    'Account_Type': h.account_type,
                    'Purchase Price': h.purchase_price,
                    'Quantity': h.quantity,
                    'Commission': h.commission or 0.0,
                    'Trade Date': h.trade_date,
                }
                # Attach thesis data
                d.update(mental_map.get(h.symbol, {
                    'Thesis': "", 'Catalyst': "", 'Kill Switch': "", 
                    'Conviction': "", 'Timeframe': ""
                }))
                rows.append(d)
                processed_keys.add(key)

        if not rows:
            return pd.DataFrame(), realized_pnl

        df = pd.DataFrame(rows)
        # Standardize columns
        desired_cols = ['Symbol', 'Broker', 'Account_Type', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols
        cols = [c for c in desired_cols if c in df.columns]
        return df[cols], realized_pnl

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
