"""
Script: migrate_realized_pnl.py
Reads all broker CSVs from the `transactions/` folder, runs the FIFO
calculate_holdings engine to extract realized (closed-trade) P&L, then
upserts it into the RealizedPnL table in Supabase.

Run from project root:
    python scripts/migrate_realized_pnl.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv
from sqlmodel import Session, select, SQLModel

load_dotenv()

from backend.database import engine
from backend.models import RealizedPnL
from transaction_parser import load_all_transactions, calculate_holdings

TX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transactions")

def migrate():
    print("Loading broker CSVs from:", TX_DIR)
    df_all = load_all_transactions(TX_DIR)
    print(f"  Parsed {len(df_all)} raw transactions from broker files")

    # Run FIFO engine — we only care about realized_pnl
    _, realized_pnl = calculate_holdings(df_all)
    print(f"  Found realized PnL for {len(realized_pnl)} symbols")

    # Ensure table exists
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Wipe existing realizedpnl rows (re-seed each run)
        existing = session.exec(select(RealizedPnL)).all()
        for row in existing:
            session.delete(row)
        session.commit()
        print(f"  Cleared {len(existing)} old RealizedPnL rows")

        inserted = 0
        for symbol, currency_map in realized_pnl.items():
            for currency, amount in currency_map.items():
                if pd.isna(amount):
                    continue
                row = RealizedPnL(
                    symbol=symbol,
                    currency=currency,
                    pnl_amount=float(amount),
                    source="broker_csv"
                )
                session.add(row)
                inserted += 1
                print(f"    {symbol} [{currency}]: {amount:+.2f}")

        session.commit()
        print(f"\nInserted {inserted} RealizedPnL rows into Supabase.")

if __name__ == "__main__":
    migrate()
