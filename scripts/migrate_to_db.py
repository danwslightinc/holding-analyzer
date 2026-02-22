import os
import sys
import pandas as pd
import json
from datetime import datetime
from sqlmodel import Session, select

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, create_db_and_tables
from backend.models import Holding, Transaction, InvestmentThesis
from transaction_parser import load_all_transactions

CSV_PATH = "portfolio.csv"
THESIS_PATH = "thesis.json"
TX_DIR = "transactions"

def migrate():
    create_db_and_tables()
    
    with Session(engine) as session:
        # 0. Wipe existing database tables before migrating
        print("Wiping existing database tables...")
        from sqlmodel import delete
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        session.exec(delete(InvestmentThesis))
        session.commit()
        
        # 1. Load thesis.json and migrate to InvestmentThesis table
        print("Migrating theses from thesis.json...")
        thesis_data = {}
        if os.path.exists(THESIS_PATH):
            with open(THESIS_PATH, 'r') as f:
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
        
        # 2. Load portfolio.csv
        df_manual = pd.DataFrame()
        if os.path.exists(CSV_PATH):
            df_manual = pd.read_csv(CSV_PATH)
            
        # 3. Process Holdings
        if not df_manual.empty:
            # Group by Symbol and Comment to handle different accounts (e.g. CIBC TFSA vs RBC RRSP)
            groups = df_manual.groupby(['Symbol', 'Comment'], dropna=False)
            print(f"Migrating {len(groups)} position/account combinations...")
            
            for (symbol, comment), rows in groups:
                if pd.isna(symbol): continue
                symbol = str(symbol).strip()
                comment_str = str(comment).strip() if pd.notna(comment) else ""
                
                h = Holding(symbol=symbol)
                
                # Thesis info is now handled by the InvestmentThesis table
                
                # Aggregate quantity for THIS specific account/symbol combination
                valid_qty_rows = rows.dropna(subset=['Quantity'])
                if not valid_qty_rows.empty:
                    valid_qty_rows['Quantity'] = pd.to_numeric(valid_qty_rows['Quantity'], errors='coerce')
                    valid_qty_rows = valid_qty_rows.dropna(subset=['Quantity'])
                    
                    if not valid_qty_rows.empty:
                        h.quantity = float(valid_qty_rows['Quantity'].sum())
                        
                        # Calculate weighted average purchase price for this account
                        price_qty_rows = valid_qty_rows.dropna(subset=['Purchase Price'])
                        price_qty_rows['Purchase Price'] = pd.to_numeric(price_qty_rows['Purchase Price'], errors='coerce')
                        price_qty_rows = price_qty_rows.dropna(subset=['Purchase Price'])
                        
                        if not price_qty_rows.empty and price_qty_rows['Quantity'].sum() > 0:
                            total_cost = (price_qty_rows['Purchase Price'] * price_qty_rows['Quantity']).sum()
                            h.purchase_price = float(total_cost / price_qty_rows['Quantity'].sum())
                        else:
                            h.purchase_price = None

                        if 'Commission' in valid_qty_rows:
                            comm_col = pd.to_numeric(valid_qty_rows['Commission'], errors='coerce').dropna()
                            h.commission = float(comm_col.sum()) if not comm_col.empty else 0.0
                        else:
                            h.commission = 0.0
                
                # Set account details
                if comment_str:
                    h.comment = comment_str
                    parts = comment_str.split()
                    if len(parts) >= 2:
                        h.broker = parts[0]
                        h.account_type = parts[1]
                
                # Get the latest trade date for this account
                if 'Trade Date' in rows:
                    valid_dates = rows['Trade Date'].dropna()
                    if not valid_dates.empty:
                        try:
                            parsed_dates = pd.to_datetime(valid_dates, errors='coerce').dropna()
                            if not parsed_dates.empty:
                                h.trade_date = parsed_dates.max()
                        except:
                            pass
                
                session.add(h)
        
        session.commit()
        
        # 4. Load Transactions from portfolio.csv
        print("Loading transactions from portfolio.csv...")
        
        def clean_val(val, default=None):
            if pd.isna(val): return default
            return float(val)

        if not df_manual.empty:
            for _, row in df_manual.iterrows():
                symbol = str(row.get('Symbol', '')).strip()
                qty_val = row.get('Quantity')
                if pd.isna(qty_val) or symbol == '': 
                    continue
                
                comment = str(row.get('Comment', '')).strip()
                h = session.exec(select(Holding).where(Holding.symbol == symbol).where(Holding.comment == comment)).first()
                if not h:
                    continue
                
                t_date = row.get('Trade Date')
                try:
                    # Clean the date, try YYYYMMDD first
                    if pd.notna(t_date) and str(t_date).replace('.0', '').isdigit():
                        date_val = pd.to_datetime(str(int(float(t_date))), format='%Y%m%d')
                    else:
                        date_val = pd.to_datetime(t_date, errors='coerce')
                    if pd.isna(date_val):
                        date_val = pd.Timestamp.now()
                except:
                    date_val = pd.Timestamp.now()
                
                tx_type = str(row.get('Transaction Type'))
                if tx_type == 'nan' or tx_type.strip() == '':
                    tx_type = 'Buy'
                
                qty = clean_val(qty_val, 0.0)
                price = clean_val(row.get('Purchase Price'), 0.0)
                comm = clean_val(row.get('Commission'), 0.0)
                
                b_val, a_val = None, None
                if comment:
                    parts = comment.split()
                    if len(parts) >= 2:
                        b_val = parts[0]
                        a_val = parts[1]
                
                tx = Transaction(
                    holding_id=h.id,
                    symbol=symbol,
                    date=date_val,
                    type=tx_type,
                    quantity=qty,
                    price=price,
                    commission=comm,
                    amount=(qty * price) + comm,
                    currency='CAD' if symbol.endswith('.TO') else 'USD',
                    description=comment,
                    broker=b_val,
                    account_type=a_val,
                    source='Manual'
                )
                session.add(tx)
            
        session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
