import os
import sys
import pandas as pd
import json
from datetime import datetime
from sqlmodel import Session, select

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, create_db_and_tables
from backend.models import Holding, Transaction
from transaction_parser import load_all_transactions

CSV_PATH = "portfolio.csv"
THESIS_PATH = "thesis.json"
TX_DIR = "transactions"

def migrate():
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Load thesis.json
        thesis_data = {}
        if os.path.exists(THESIS_PATH):
            with open(THESIS_PATH, 'r') as f:
                thesis_data = json.load(f)
        
        # 2. Load portfolio.csv
        df_manual = pd.DataFrame()
        if os.path.exists(CSV_PATH):
            df_manual = pd.read_csv(CSV_PATH)
            
        # 3. Process Holdings
        symbols = set()
        if not df_manual.empty:
            symbols.update(df_manual['Symbol'].unique())
        
        print(f"Migrating {len(symbols)} symbols...")
        
        for symbol in symbols:
            # Check if exists
            existing = session.exec(select(Holding).where(Holding.symbol == symbol)).first()
            if existing: continue
            
            h = Holding(symbol=symbol)
            
            # Add thesis info
            t_info = thesis_data.get(symbol, {})
            h.thesis = t_info.get("Thesis")
            h.conviction = t_info.get("Conviction")
            h.timeframe = t_info.get("Timeframe")
            h.kill_switch = t_info.get("Kill Switch")
            
            # Add manual position info if present
            if not df_manual.empty and symbol in df_manual['Symbol'].values:
                row = df_manual[df_manual['Symbol'] == symbol].iloc[0]
                h.quantity = float(row.get('Quantity', 0)) if pd.notnull(row.get('Quantity')) else None
                h.purchase_price = float(row.get('Purchase Price', 0)) if pd.notnull(row.get('Purchase Price')) else None
                h.commission = float(row.get('Commission', 0)) if pd.notnull(row.get('Commission')) else None
                h.comment = row.get('Comment')
                
                trade_date = row.get('Trade Date')
                if pd.notnull(trade_date):
                    try:
                        h.trade_date = pd.to_datetime(trade_date)
                    except:
                        pass
            
            session.add(h)
        
        session.commit()
        
        # 4. Load Transactions
        print("Loading transactions from CSVs...")
        df_txs = load_all_transactions(TX_DIR)
        print(f"Found {len(df_txs)} transactions.")
        
        def clean_val(val, default=None):
            if pd.isna(val): return default
            return float(val)

        for _, row in df_txs.iterrows():
            # Find holding
            symbol = row['Symbol']
            h = session.exec(select(Holding).where(Holding.symbol == symbol)).first()
            
            tx = Transaction(
                holding_id=h.id if h else None,
                symbol=symbol,
                date=pd.to_datetime(row['Date']),
                type=row['Action'],
                quantity=clean_val(row.get('Quantity'), 0.0),
                price=clean_val(row.get('Price'), 0.0),
                commission=clean_val(row.get('Commission'), 0.0),
                amount=clean_val(row.get('Amount'), 0.0),
                currency=row.get('Currency', 'CAD'),
                description=row.get('Description'),
                source=row.get('Source', 'Unknown')
            )
            session.add(tx)
            
        session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
