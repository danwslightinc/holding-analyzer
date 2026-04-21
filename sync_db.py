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
    
    print("🚀 Starting FULL Database Sync (CSV + Broker History)...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Clear existing data
        print("Cleaning database...")
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        session.commit()
        
        # 2. Import Manual Ledger (portfolio.csv)
        print(f"Importing active positions from {CSV_PATH}...")
        _sync_from_legacy_files(session, CSV_PATH, THESIS_PATH)
        
        # 3. Import Broker History from transactions/ folder
        if os.path.exists(TRANS_DIR):
            print("Scanning for broker history...")
            for filename in os.listdir(TRANS_DIR):
                if not filename.endswith('.csv'): continue
                if any(x in filename.upper() for x in ["HOLDING", "ACCOUNT", "POSITION"]): continue
                
                path = os.path.join(TRANS_DIR, filename)
                fname_upper = filename.upper()
                broker = "CIBC" if "CIBC" in fname_upper else "RBC" if "RBC" in fname_upper else "TD" if "TD" in fname_upper else "Unknown"
                
                df = pd.DataFrame()
                if broker == "CIBC": df = parse_cibc(path)
                elif broker == "RBC": df = parse_rbc(path)
                elif broker == "TD": df = parse_td(path)
                
                if not df.empty:
                    print(f"  - Importing {len(df)} transactions from {filename}")
                    for _, row in df.iterrows():
                        sym = clean_symbol(str(row['Symbol']), broker=broker)
                        qty = float(row['Quantity'])
                        tx_date = pd.to_datetime(row['Date'])
                        tx_type = row['Action'].upper()

                        # De-duplication
                        dup_q = select(Transaction).where(Transaction.symbol == sym, Transaction.quantity == qty)
                        existing = session.exec(dup_q).all()
                        if any(str(e.type).upper() == tx_type and abs((e.date - tx_date).days) <= 3 for e in existing):
                            continue

                        h_q = select(Holding).where(Holding.symbol == sym, Holding.broker == broker)
                        h = session.exec(h_q).first()
                        if not h:
                            h = Holding(symbol=sym, broker=broker, quantity=0.0)
                            session.add(h)
                            session.commit()
                            session.refresh(h)
                        
                        tx = Transaction(
                            holding_id=h.id, symbol=sym, date=tx_date, type=tx_type,
                            quantity=qty, price=float(row['Price']),
                            commission=float(row.get('Commission', 0)),
                            amount=float(row['Amount']),
                            currency=row.get('Currency', 'USD' if not sym.endswith('.TO') else 'CAD'),
                            description=row.get('Description', ''),
                            broker=broker, source=filename
                        )
                        session.add(tx)
            session.commit()
            
            # 4. FINAL RECONCILIATION
            print("Reconciling quantities...")
            all_holdings = session.exec(select(Holding)).all()
            for h in all_holdings:
                txs = session.exec(select(Transaction).where(Transaction.holding_id == h.id)).all()
                qty = 0.0
                for tx in txs:
                    t_type = str(tx.type).upper()
                    if t_type in ['BUY', 'DRIP', 'ADD', 'TRANSFER IN', 'TRANSF IN']: qty += tx.quantity
                    elif t_type in ['SELL', 'REDUCE', 'TRANSFER OUT', 'TRANSF OUT']: qty -= tx.quantity
                h.quantity = qty
                session.add(h)
            session.commit()
            
    print("\n✅ Sync complete.")

if __name__ == "__main__":
    full_sync()
