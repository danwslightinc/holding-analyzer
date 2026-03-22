import os
import pandas as pd
from sqlmodel import Session, select, delete
from backend.database import engine, create_db_and_tables
from backend.models import Holding, Transaction, InvestmentThesis
from data_loader import _sync_from_legacy_files
from transaction_parser import parse_cibc, parse_rbc, parse_td, clean_symbol

def full_sync():
    CSV_PATH = "portfolio.csv"
    THESIS_PATH = "thesis.json"
    TRANS_DIR = "transactions"
    
    print("🚀 Starting FULL Database Sync (Holdings + Historical Transactions)...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Clear existing portfolio/transaction data ONLY
        print("Emptying transaction and holding tables (preserving Thesis and Settings)...")
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        # session.exec(delete(InvestmentThesis)) # NEVER DELETE THIS
        session.commit()
        
        # 2. Import Manual/Legacy State from portfolio.csv
        print(f"Importing active positions from {CSV_PATH}...")
        _sync_from_legacy_files(session, CSV_PATH, THESIS_PATH)
        
        # 3. Import Broker History from transactions/ folder
        if os.path.exists(TRANS_DIR):
            print(f"Scanning {TRANS_DIR} for historical transactions...")
            for filename in os.listdir(TRANS_DIR):
                path = os.path.join(TRANS_DIR, filename)
                if not filename.endswith('.csv'): continue
                
                df = pd.DataFrame()
                broker = "Unknown"
                
                if "CIBC" in filename.upper():
                    df = parse_cibc(path)
                    broker = "CIBC"
                elif "RBC" in filename.upper():
                    df = parse_rbc(path)
                    broker = "RBC"
                elif "TD" in filename.upper():
                    df = parse_td(path)
                    broker = "TD"
                
                if not df.empty:
                    print(f"  - Importing {len(df)} transactions from {filename} ({broker})")
                    for _, row in df.iterrows():
                        sym = str(row['Symbol'])
                        # Clean/Normalize symbol
                        clean_sym = clean_symbol(sym, broker=broker)
                        
                        # Find matching holding or create one
                        h_q = select(Holding).where(Holding.symbol == clean_sym, Holding.broker == broker)
                        h = session.exec(h_q).first()
                        if not h:
                            h = Holding(symbol=clean_sym, broker=broker, quantity=0.0)
                            session.add(h)
                            session.commit()
                            session.refresh(h)
                        
                        tx = Transaction(
                            holding_id=h.id,
                            symbol=clean_sym,
                            date=row['Date'],
                            type=row['Action'],
                            quantity=float(row['Quantity']),
                            price=float(row['Price']),
                            commission=float(row.get('Commission', 0)),
                            amount=float(row['Amount']),
                            currency=row.get('Currency', 'USD' if not clean_sym.endswith('.TO') else 'CAD'),
                            description=row.get('Description', ''),
                            broker=broker,
                            source=filename
                        )
                        session.add(tx)
            session.commit()
            
    print("\n✅ Sync complete! Both active holdings and historical realized P&L are restored.")

if __name__ == "__main__":
    full_sync()
