import pandas as pd
import json
import os
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select
from transaction_parser import calculate_holdings

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

def get_processed_transactions(session):
    """Fetch and deduplicate transactions from DB."""
    transactions = session.exec(select(Transaction)).all()
    if not transactions:
        return pd.DataFrame()
        
    data = []
    for tx in transactions:
        data.append({
            'id': tx.id,
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
            'Portfolio_Category': tx.portfolio_category,
            'Source': tx.source
        })
    
    df_tx = pd.DataFrame(data)
    
    # Normalize 'Unknown' account types
    if not df_tx.empty:
        known_accounts = df_tx[df_tx['Account_Type'] != 'Unknown'].groupby(['Symbol', 'Broker'])['Account_Type'].unique().to_dict()
        def normalize_account(row):
            if row['Account_Type'] == 'Unknown':
                pref = known_accounts.get((row['Symbol'], row['Broker']))
                if pref is not None and len(pref) == 1:
                    return pref[0]
            return row['Account_Type']
        df_tx['Account_Type'] = df_tx.apply(normalize_account, axis=1)
        
        # Deduplicate
        df_tx['match_date'] = pd.to_datetime(df_tx['Date']).dt.date
        df_tx = df_tx.sort_values(['Symbol', 'match_date', 'Source'], ascending=[True, True, False])
        df_tx = df_tx.drop_duplicates(subset=['Symbol', 'match_date', 'Quantity', 'Action'], keep='first')
        df_tx = df_tx.drop(columns=['match_date'])
        
    return df_tx

@cache_result(portfolio_cache)
def load_portfolio_from_db(category: Optional[str] = None):
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    
    # User requirement: If any of portfolio.csv and portfolio_resp.csv is missing, show 0 for all data
    if not os.path.exists("portfolio.csv") or not os.path.exists("portfolio_resp.csv"):
        return pd.DataFrame(), {}

    create_db_and_tables()
    
    CSV_PATH = "portfolio.csv"
    THESIS_PATH = "thesis.json"
    
    with Session(engine) as session:
        # Check if database is empty
        holdings_count = session.exec(select(Holding)).first()
        if not holdings_count and (os.path.exists(CSV_PATH) or os.path.exists(THESIS_PATH)):
            _sync_from_legacy_files(session, CSV_PATH, THESIS_PATH)
            
        holdings_query = select(Holding)
        if category and category.upper() != 'ALL':
            holdings_query = holdings_query.where(Holding.portfolio_category == category)
        holdings = session.exec(holdings_query).all()
        
        df_tx = get_processed_transactions(session)
        if category and category.upper() != 'ALL':
            df_tx = df_tx[df_tx['Portfolio_Category'].str.upper() == category.upper()]
            
        if df_tx.empty and not holdings:
            return pd.DataFrame(), {}
            
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
        # We use the Holding table as the primary source of truth for current positions and quantities.
        # We use Transaction calculated holdings to enrich them with FIFO cost basis when possible.
        rows = []
        
        # Create a lookup for transaction-calculated info
        # Key: (Symbol, Broker) -> list of holding dicts
        tx_map = {}
        for _, r in df_h_holdings.iterrows():
            key = (r['Symbol'], r['Broker'])
            if key not in tx_map: tx_map[key] = []
            tx_map[key].append(r.to_dict())
            
        for h in holdings:
            if not h.quantity or h.quantity <= 0:
                continue
                
            sym = h.symbol
            broker = h.broker
            
            # Find best match in transaction data
            match = None
            tx_options = tx_map.get((sym, broker), [])
            if not tx_options:
                # Fallback to symbol-only match if broker doesn't match
                all_tx_options = [opt for opts in tx_map.values() for opt in opts if opt['Symbol'] == sym]
                tx_options = all_tx_options
                
            if tx_options:
                # If multiple accounts for the same symbol/broker, we might have a mismatch.
                # Try to match account_type if available.
                account_match = [opt for opt in tx_options if opt.get('Account_Type') == h.account_type]
                if account_match:
                    match = account_match[0]
                else:
                    # Just take the first one or aggregate?
                    # For cost basis, taking the first one (FIFO) is usually a good proxy if only one exists.
                    match = tx_options[0]
            
            d = {
                'Symbol': sym,
                'Portfolio_Category': h.portfolio_category or 'Retirement',
                'Broker': broker,
                'Account_Type': h.account_type or (match['Account_Type'] if match else 'Unknown'),
                'Quantity': h.quantity,
                # Prioritize manally entered purchase price from the Holding table
                'Purchase Price': h.purchase_price if (h.purchase_price is not None and h.purchase_price > 0.001) else (match['Purchase Price'] if match else 0.0),
                'Commission': h.commission if (h.commission is not None and h.commission > 0) else (match['Commission'] if match else 0.0),
                'Trade Date': h.trade_date if h.trade_date is not None else (match['Trade Date'] if match else None),
            }
            
            # Attach thesis data
            d.update(mental_map.get(sym, {
                'Thesis': "", 'Catalyst': "", 'Kill Switch': "", 
                'Conviction': "", 'Timeframe': ""
            }))
            rows.append(d)

        if not rows:
            return pd.DataFrame(), realized_pnl

        df = pd.DataFrame(rows)
        # Standardize columns
        desired_cols = ['Symbol', 'Portfolio_Category', 'Broker', 'Account_Type', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols
        cols = [c for c in desired_cols if c in df.columns]
        return df[cols], realized_pnl

def load_portfolio_from_csv():
    """Fallback source specifically for GitHub Actions or legacy local testing."""
    CSV_PATHS = {
        "Retirement": "portfolio.csv",
        "RESP": "portfolio_resp.csv"
    }
    THESIS_PATH = "thesis.json"
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    
    all_txs = []
    
    for category, path in CSV_PATHS.items():
        if not os.path.exists(path):
            continue
            
        try:
            df_csv = pd.read_csv(path)
            if df_csv.empty: continue
            
            # Standardize column names
            def split_comment(comment):
                if pd.isna(comment): return "Manual", "Unknown"
                parts = str(comment).strip().split(' ')
                if len(parts) >= 2: return parts[0], parts[1]
                return parts[0], "Unknown"
                
            if 'Comment' in df_csv.columns:
                df_csv[['Broker', 'Account_Type']] = df_csv['Comment'].apply(lambda x: pd.Series(split_comment(x)))
            
            if 'Transaction Type' in df_csv.columns:
                df_csv['Action'] = df_csv['Transaction Type'].fillna('BUY').apply(lambda x: TYPE_NORMALIZE.get(x, 'BUY'))
            else:
                df_csv['Action'] = 'BUY'
                
            if 'Date' in df_csv.columns: df_csv = df_csv.drop(columns=['Date'])
            
            col_map = {'Trade Date': 'Date', 'Purchase Price': 'Price'}
            df_tx = df_csv.rename(columns=col_map)
            def detect_currency(sym):
                if not sym: return 'USD'
                s = str(sym).upper()
                if s.endswith('-U.TO') or s.endswith('-U'): return 'USD'
                return 'CAD' if s.endswith('.TO') else 'USD'
                
            df_tx['Currency'] = df_tx['Symbol'].apply(detect_currency)
            df_tx['Date'] = df_tx['Date'].apply(parse_date)
            df_tx = df_tx.dropna(subset=['Date'])
            df_tx['Portfolio_Category'] = category
            
            if 'Amount' not in df_tx.columns:
                df_tx['Amount'] = (df_tx['Quantity'] * df_tx['Price']) + df_tx['Commission'].fillna(0)
            
            all_txs.append(df_tx)
        except Exception as e:
            print(f"Error loading {path}: {e}")

    if not all_txs:
        return pd.DataFrame(), {}
        
    df_tx_combined = pd.concat(all_txs)
    
    # Calculate Holdings
    df_holdings, realized_pnl = calculate_holdings(df_tx_combined)
    
    # Assign Portfolio_Category to holdings (heuristic: match by symbol/broker)
    # Since calculate_holdings aggregates, we need to map category back
    cat_map = {}
    for _, tx in df_tx_combined.iterrows():
        cat_map[(tx['Symbol'], tx['Broker'], tx['Account_Type'])] = tx['Portfolio_Category']
    
    def get_cat(row):
        return cat_map.get((row['Symbol'], row['Broker'], row['Account_Type']), "Retirement")
    
    df_holdings['Portfolio_Category'] = df_holdings.apply(get_cat, axis=1)
    
    # Enrich with Thesis Data
    # ... (rest of function unchanged)
    mental_map = {}
    if os.path.exists(THESIS_PATH):
        try:
            with open(THESIS_PATH, "r") as f:
                thesis_data = json.load(f)
            mental_map = {sym: {
                'Thesis': d.get('Thesis', ''),
                'Catalyst': '',
                'Kill Switch': d.get('Kill Switch', ''),
                'Conviction': d.get('Conviction', ''),
                'Timeframe': d.get('Timeframe', '')
            } for sym, d in thesis_data.items()}
        except:
            pass
            
    rows = []
    for _, r in df_holdings.iterrows():
        sym = r['Symbol']
        d = r.to_dict()
        d.update(mental_map.get(sym, {
            'Thesis': "", 'Catalyst': "", 'Kill Switch': "", 
            'Conviction': "", 'Timeframe': ""
        }))
        rows.append(d)
        
    if not rows:
        return pd.DataFrame(), realized_pnl
    
    res_df = pd.DataFrame(rows)
    desired_cols = ['Symbol', 'Broker', 'Account_Type', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols
    return res_df[[c for c in desired_cols if c in res_df.columns]], realized_pnl

def _sync_from_legacy_files(session, csv_path, thesis_path, portfolio_category="Retirement"):
    """Helper to migrate data from portfolio.csv and thesis.json into DB"""
    if os.path.exists(thesis_path):
        try:
            with open(thesis_path, "r") as f:
                thesis_data = json.load(f)
            for symbol, data in thesis_data.items():
                if not symbol: continue
                # Check if symbol already exists
                existing = session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == symbol)).first()
                if existing:
                    existing.thesis = data.get("Thesis")
                    existing.conviction = data.get("Conviction")
                    existing.timeframe = data.get("Timeframe")
                    existing.kill_switch = data.get("Kill Switch")
                    session.add(existing)
                else:
                    it = InvestmentThesis(
                        symbol=symbol,
                        thesis=data.get("Thesis"),
                        conviction=data.get("Conviction"),
                        timeframe=data.get("Timeframe"),
                        kill_switch=data.get("Kill Switch")
                    )
                    session.add(it)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error syncing thesis.json: {e}")

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            if df.empty: return
            
            from transaction_parser import clean_symbol
            df['Symbol'] = df.apply(lambda r: clean_symbol(r['Symbol'], broker=r.get('Broker')), axis=1)
            
            # Sort by date to process in order
            if 'Trade Date' in df.columns:
                df['Parsed_Date'] = df['Trade Date'].apply(parse_date)
                df = df.sort_values('Parsed_Date')
            
            for _, row in df.iterrows():
                symbol = str(row['Symbol']).strip()
                if not symbol or pd.isna(symbol): continue
                
                comment = str(row.get('Comment', '')).strip() if pd.notna(row.get('Comment')) else ""
                broker, account_type = "Manual", "Manual"
                if comment:
                    parts = comment.split()
                    if len(parts) >= 2:
                        broker, account_type = parts[0], parts[1]
                
                # Find or create holding
                h_q = select(Holding).where(
                    Holding.symbol == symbol,
                    Holding.broker == broker,
                    Holding.account_type == account_type,
                    Holding.portfolio_category == portfolio_category
                )
                h = session.exec(h_q).first()
                if not h:
                    h = Holding(symbol=symbol, broker=broker, account_type=account_type, quantity=0.0, portfolio_category=portfolio_category)
                    session.add(h)
                    session.commit()
                    session.refresh(h)
                
                # Process transaction
                raw_type = row.get('Transaction Type')
                tx_type = str(raw_type).strip().upper() if pd.notna(raw_type) and str(raw_type).strip() else 'BUY'
                
                qty = float(row.get('Quantity', 0.0))
                if pd.isna(qty): qty = 0.0
                
                price = float(row.get('Purchase Price', 0.0))
                if pd.isna(price): price = 0.0
                
                comm = float(row.get('Commission', 0.0))
                if pd.isna(comm): comm = 0.0
                
                if tx_type == 'SELL':
                    h.quantity -= qty
                    amt = (qty * price) - comm
                else:
                    h.quantity += qty
                    amt = (qty * price) + comm
                
                if pd.isna(amt): amt = 0.0
                
                # Update holding avg price (simplistic weighted avg for BUYs)
                if tx_type != 'SELL' and h.quantity > 0:
                    # This is an approximation for legacy sync
                    old_qty = h.quantity - qty
                    if old_qty > 0:
                        h.purchase_price = ((h.purchase_price * old_qty) + (price * qty)) / h.quantity
                    else:
                        h.purchase_price = price
                
                h.trade_date = row.get('Parsed_Date') if 'Parsed_Date' in df.columns else h.trade_date
                if pd.isna(h.trade_date): h.trade_date = None
                
                t_date = row.get('Parsed_Date') if 'Parsed_Date' in df.columns else pd.Timestamp.now()
                if pd.isna(t_date): t_date = pd.Timestamp.now()

                tx = Transaction(
                    holding_id=h.id,
                    symbol=symbol,
                    portfolio_category=portfolio_category,
                    date=t_date,
                    type=tx_type,
                    quantity=qty,
                    price=price,
                    commission=comm,
                    amount=amt,
                    currency='USD' if (symbol.endswith('-U.TO') or symbol.endswith('-U')) else ('CAD' if symbol.endswith('.TO') else 'USD'),
                    description=comment or f"Legacy {tx_type}",
                    broker=broker,
                    account_type=account_type,
                    source='Manual'
                )
                session.add(h)
                session.add(tx)
            
            session.commit()
            print("Legacy sync complete.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error syncing portfolio.csv: {e}")
            session.rollback()

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

    return pd.NaT
