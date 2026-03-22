import os
import pandas as pd
import json
from sqlmodel import Session, select, delete
from backend.database import engine, create_db_and_tables
from backend.models import Holding, Transaction, InvestmentThesis
from transaction_parser import parse_cibc, parse_rbc, parse_td, clean_symbol

def restore_everything():
    print("🚀 Emergency Database Restoration Started...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Clear only Holdings and Transactions (Preserve Thesis/Settings)
        print("Cleaning up old holdings and transactions...")
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        session.commit()
        
        # 2. Restore Holdings from portfolio.csv
        print("Restoring active positions from portfolio.csv...")
        df_p = pd.read_csv("portfolio.csv")
        
        # Helper to extract broker/account from comment
        def get_broker_info(comment):
            if pd.isna(comment): return "Manual", "Unknown"
            parts = str(comment).strip().split()
            if len(parts) >= 2: return parts[0], parts[1]
            return parts[0], "Unknown"

        # Group by Symbol and Comment to aggregate positions
        df_p['Symbol'] = df_p['Symbol'].apply(lambda s: clean_symbol(str(s)))
        groups = df_p.groupby(['Symbol', 'Comment'], dropna=False)
        
        for (symbol, comment), rows in groups:
            broker, account_type = get_broker_info(comment)
            qty = float(pd.to_numeric(rows['Quantity'], errors='coerce').sum())
            if qty <= 0: continue
            
            # Fix: Parse YYYYMMDD integers correctly
            def parse_date_fixed(d):
                if pd.isna(d): return None
                s = str(int(float(d)))
                if len(s) == 8: return pd.to_datetime(s, format='%Y%m%d')
                return pd.to_datetime(d, errors='coerce')

            trade_dates = rows['Trade Date'].apply(parse_date_fixed).dropna()
            earliest_date = trade_dates.min() if not trade_dates.empty else None
            
            # Calculate weighted purchase price
            total_cost = (rows['Purchase Price'] * rows['Quantity']).sum()
            avg_price = total_cost / qty if qty > 0 else 0
            
            h = Holding(
                symbol=symbol,
                broker=broker,
                account_type=account_type,
                quantity=qty,
                purchase_price=float(avg_price),
                trade_date=earliest_date,
                comment=str(comment) if pd.notna(comment) else ""
            )
            session.add(h)
            session.commit()
            session.refresh(h)
            
            # Add these as historical "BUY" transactions so they show up in P&L
            for _, row in rows.iterrows():
                tx = Transaction(
                    holding_id=h.id,
                    symbol=symbol,
                    date=pd.to_datetime(row['Trade Date'], errors='coerce') or earliest_date,
                    type='BUY',
                    quantity=float(row['Quantity']),
                    price=float(row['Purchase Price']),
                    amount=float(row['Quantity'] * row['Purchase Price']),
                    broker=broker,
                    account_type=account_type,
                    source="portfolio.csv"
                )
                session.add(tx)
        session.commit()
        
        # 3. Import Historical Trades from broker files (for realized P&L)
        TRANS_DIR = "transactions"
        if os.path.exists(TRANS_DIR):
            for filename in os.listdir(TRANS_DIR):
                path = os.path.join(TRANS_DIR, filename)
                if not filename.endswith('.csv'): continue
                
                df_t = pd.DataFrame()
                if "CIBC" in filename.upper(): df_t = parse_cibc(path)
                elif "RBC" in filename.upper(): df_t = parse_rbc(path)
                elif "TD" in filename.upper(): df_t = parse_td(path)
                
                if not df_t.empty:
                    print(f"  - Importing historical activity from {filename}...")
                    for _, row in df_t.iterrows():
                        sym = clean_symbol(str(row['Symbol']))
                        
                        # Find or create a matching holding shell for historical trades
                        h_q = select(Holding).where(Holding.symbol == sym, Holding.broker == (filename.split()[0]))
                        h = session.exec(h_q).first()
                        if not h:
                            h = Holding(symbol=sym, broker=filename.split()[0], quantity=0.0)
                            session.add(h)
                            session.commit()
                            session.refresh(h)
                        
                        tx = Transaction(
                            holding_id=h.id,
                            symbol=sym,
                            date=row['Date'],
                            type=row['Action'],
                            quantity=float(row['Quantity']),
                            price=float(row['Price']),
                            amount=float(row['Amount']),
                            broker=h.broker,
                            source=filename
                        )
                        session.add(tx)
            session.commit()

        # 4. Final check - restore any missing Thesis entries from thesis.json
        if os.path.exists("thesis.json"):
            with open("thesis.json", "r") as f:
                thesis_data = json.load(f)
            for sym, data in thesis_data.items():
                existing = session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == sym)).first()
                if not existing:
                    it = InvestmentThesis(
                        symbol=sym,
                        thesis=data.get("Thesis"),
                        conviction=data.get("Conviction"),
                        timeframe=data.get("Timeframe"),
                        kill_switch=data.get("Kill Switch")
                    )
                    session.add(it)
            session.commit()

    print("\n✅ Restoration Complete. Your data, performance, and thesis are back.")

if __name__ == "__main__":
    restore_everything()
