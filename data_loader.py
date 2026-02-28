import pandas as pd
import json
import os
from datetime import datetime
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
def load_portfolio_from_db():
    mental_cols = ['Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'Timeframe']
    create_db_and_tables()
    
    CSV_PATH = "portfolio.csv"
    THESIS_PATH = "thesis.json"
    
    with Session(engine) as session:
        # Check if database is empty - if so, try to sync from legacy files (useful for CI)
        holdings_count = session.exec(select(Holding)).first()
        if not holdings_count and (os.path.exists(CSV_PATH) or os.path.exists(THESIS_PATH)):
            print("Database empty. Syncing from legacy files...")
            _sync_from_legacy_files(session, CSV_PATH, THESIS_PATH)
            
        holdings = session.exec(select(Holding)).all()
        df_tx = get_processed_transactions(session)
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
                'Broker': broker,
                'Account_Type': h.account_type or (match['Account_Type'] if match else 'Unknown'),
                'Quantity': h.quantity,
                'Purchase Price': match['Purchase Price'] if match else h.purchase_price,
                'Commission': match['Commission'] if match else (h.commission or 0.0),
                'Trade Date': match['Trade Date'] if match else h.trade_date,
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
        desired_cols = ['Symbol', 'Broker', 'Account_Type', 'Purchase Price', 'Quantity', 'Commission', 'Trade Date'] + mental_cols
        cols = [c for c in desired_cols if c in df.columns]
        return df[cols], realized_pnl

def _sync_from_legacy_files(session, csv_path, thesis_path):
    """Helper to migrate data from portfolio.csv and thesis.json into DB"""
    if os.path.exists(thesis_path):
        try:
            with open(thesis_path, "r") as f:
                thesis_data = json.load(f)
            for symbol, data in thesis_data.items():
                if not symbol: continue
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
            print(f"Error syncing thesis.json: {e}")

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            if df.empty: return
            
            # Map holdings and transactions from CSV
            groups = df.groupby(['Symbol', 'Comment'], dropna=False)
            for (symbol, comment), rows in groups:
                if pd.isna(symbol): continue
                symbol = str(symbol).strip()
                comment_str = str(comment).strip() if pd.notna(comment) else ""
                
                h = Holding(symbol=symbol)
                # Parse manual quantity and cost
                vqr = rows.dropna(subset=['Quantity'])
                if not vqr.empty:
                    vqr['Quantity'] = pd.to_numeric(vqr['Quantity'], errors='coerce')
                    vqr = vqr.dropna(subset=['Quantity'])
                    if not vqr.empty:
                        h.quantity = float(vqr['Quantity'].sum())
                        pqr = vqr.dropna(subset=['Purchase Price'])
                        pqr['Purchase Price'] = pd.to_numeric(pqr['Purchase Price'], errors='coerce')
                        pqr = pqr.dropna(subset=['Purchase Price'])
                        if not pqr.empty and pqr['Quantity'].sum() > 0:
                            total_cost = (pqr['Purchase Price'] * pqr['Quantity']).sum()
                            h.purchase_price = float(total_cost / pqr['Quantity'].sum())
                        
                        if 'Commission' in vqr:
                            comm_col = pd.to_numeric(vqr['Commission'], errors='coerce').dropna()
                            h.commission = float(comm_col.sum()) if not comm_col.empty else 0.0

                if comment_str:
                    h.comment = comment_str
                    parts = comment_str.split()
                    if len(parts) >= 2:
                        h.broker, h.account_type = parts[0], parts[1]
                
                if 'Trade Date' in rows:
                    vd = rows['Trade Date'].dropna()
                    if not vd.empty:
                        parsed = pd.to_datetime(vd, errors='coerce').dropna()
                        if not parsed.empty: h.trade_date = parsed.max()
                
                session.add(h)
                session.commit() # Need holding ID for transactions
                session.refresh(h)

                # Add individual transactions for FIFO tracking
                for _, row in rows.iterrows():
                    qty_val = row.get('Quantity')
                    if pd.isna(qty_val): continue
                    
                    try:
                        t_date = row.get('Trade Date')
                        if pd.notna(t_date) and str(t_date).replace('.0', '').isdigit():
                            d_val = pd.to_datetime(str(int(float(t_date))), format='%Y%m%d')
                        else:
                            d_val = pd.to_datetime(t_date, errors='coerce')
                    except: d_val = pd.Timestamp.now()
                    
                    tx = Transaction(
                        holding_id=h.id,
                        symbol=symbol,
                        date=d_val if pd.notna(d_val) else pd.Timestamp.now(),
                        type=str(row.get('Transaction Type', 'Buy')) or 'Buy',
                        quantity=float(qty_val),
                        price=float(row.get('Purchase Price', 0.0)) or 0.0,
                        commission=float(row.get('Commission', 0.0)) or 0.0,
                        amount=(float(qty_val) * float(row.get('Purchase Price', 0.0) or 0)) + float(row.get('Commission', 0.0) or 0),
                        currency='CAD' if symbol.endswith('.TO') else 'USD',
                        description=comment_str,
                        broker=h.broker,
                        account_type=h.account_type,
                        source='Manual'
                    )
                    session.add(tx)
            session.commit()
            print("Legacy sync complete.")
        except Exception as e:
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
