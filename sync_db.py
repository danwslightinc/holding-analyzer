import os
import pandas as pd
from sqlmodel import Session, select, delete
from backend.database import engine, create_db_and_tables
from backend.models import Holding, Transaction, InvestmentThesis
from data_loader import _sync_from_legacy_files

def full_sync():
    CSV_PATH = "portfolio.csv"
    RESP_CSV_PATH = "portfolio_resp.csv"
    THESIS_PATH = "thesis.json"
    DB_PATH = "./portfolio.db"
    
    print("🚀 Starting Database Sync (Source of Truth: portfolio.csv & portfolio_resp.csv)...")
    
    # Force schema refresh
    if os.path.exists(DB_PATH):
        print("Refreshing database schema...")
        os.remove(DB_PATH)
        
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Clear existing data
        print("Cleaning database...")
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        session.commit()
        
        # 2. Import Manual Ledger (portfolio.csv) -> Retirement
        if os.path.exists(CSV_PATH):
            print(f"Importing Retirement from {CSV_PATH}...")
            _sync_from_legacy_files(session, CSV_PATH, THESIS_PATH, portfolio_category="Retirement")
        
        # 3. Import RESP Ledger (portfolio_rersp.csv) -> RESP
        if os.path.exists(RESP_CSV_PATH):
            print(f"Importing RESP from {RESP_CSV_PATH}...")
            _sync_from_legacy_files(session, RESP_CSV_PATH, THESIS_PATH, portfolio_category="RESP")
            
        session.commit()
        
    print("\n✅ Sync complete. Retirement and RESP data loaded.")

if __name__ == "__main__":
    full_sync()
