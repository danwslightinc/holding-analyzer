"""
Script: migrate_realized_pnl.py
Reads all broker CSVs from the `transactions/` folder, runs a FIFO
engine per file to extract realized (closed-trade) P&L per broker/account,
then upserts it into the RealizedPnL table in Supabase.

Run from project root:
    python scripts/migrate_realized_pnl.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob, re
import pandas as pd
from dotenv import load_dotenv
from sqlmodel import Session, select, SQLModel

load_dotenv()

from backend.database import engine
from backend.models import RealizedPnL
from transaction_parser import parse_cibc, parse_rbc, parse_td, load_all_transactions, clean_symbol

TX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transactions")

# Symbols used purely for Norbert's Gambit FX conversion — exclude from P&L
NORBERT_GAMBIT_EXCLUDE = {"DLR", "DLR.TO"}


# -----------------------------------------------------------------------
# Filename → (broker, account_type)
# -----------------------------------------------------------------------
def parse_file_meta(filename: str) -> tuple[str, str]:
    name = os.path.basename(filename).upper()
    if "CIBC" in name:
        broker = "CIBC"
        account = "TFSA" if "TFSA" in name else "Open"
    elif "RBC" in name:
        broker = "RBC"
        account = "RRSP" if "RRSP" in name else "TFSA"
    elif "TD" in name:
        broker = "TD"
        account = "RRSP" if "RRSP" in name else "TFSA"
    else:
        broker = "Unknown"
        account = "Unknown"
    return broker, account


# -----------------------------------------------------------------------
# FIFO realized PnL with cost-basis tracking — runs per single DataFrame
# Returns: dict of {(symbol, currency): {pnl, cost_basis}}
# -----------------------------------------------------------------------
def compute_realized_fifo(df_tx: pd.DataFrame) -> dict:
    """
    Returns {(symbol, currency): {"pnl": float, "cost_basis": float}}
    """
    lots = {}                # symbol -> list of lots
    result = {}              # (symbol, currency) -> {pnl, cost_basis}
    merger_basis = {}

    for _, tx in df_tx.iterrows():
        sym  = tx["Symbol"]
        action = tx["Action"]
        qty  = float(tx["Quantity"]) if pd.notna(tx["Quantity"]) else 0.0
        curr = tx.get("Currency", "CAD")

        if qty <= 0:
            continue

        if action == "BUY":
            if sym not in lots:
                lots[sym] = []
            amt = tx.get("Amount", 0)
            price = tx.get("Price", 0) or 0
            comm = tx.get("Commission", 0) or 0
            cost = abs(amt) if amt and not pd.isna(amt) and amt != 0 else (qty * price + comm)
            desc = str(tx.get("Description", "")).upper()
            if "RECEIVED" in desc and ("MERGER" in desc or "ADJUSTMENT" in desc or "REORG" in desc):
                cost += merger_basis.pop(sym, 0)
            lots[sym].append({"qty": qty, "cost": cost, "currency": curr})

        elif action == "SELL":
            if sym not in lots:
                continue
            amt = tx.get("Amount", 0)
            price = tx.get("Price", 0) or 0
            comm = tx.get("Commission", 0) or 0
            total_proceeds = amt if amt and not pd.isna(amt) and amt != 0 else (qty * price - comm)
            desc = str(tx.get("Description", "")).upper()
            is_merger = "SURRENDERED" in desc and ("MERGER" in desc or "ADJUSTMENT" in desc or "REORG" in desc)

            remaining = qty
            while remaining > 0 and lots[sym]:
                lot = lots[sym][0]
                sold = min(lot["qty"], remaining)
                frac = sold / qty
                cost_piece = lot["cost"] * (sold / lot["qty"])
                proceeds_piece = total_proceeds * frac

                if is_merger:
                    merger_basis[sym] = merger_basis.get(sym, 0) + cost_piece
                else:
                    key = (sym, curr)
                    if key not in result:
                        result[key] = {"pnl": 0.0, "cost_basis": 0.0}
                    result[key]["pnl"] += proceeds_piece - cost_piece
                    result[key]["cost_basis"] += cost_piece

                lot["qty"] -= sold
                lot["cost"] -= cost_piece
                remaining -= sold
                if lot["qty"] <= 1e-6:
                    lots[sym].pop(0)

    return result


# -----------------------------------------------------------------------
# Main migration
# -----------------------------------------------------------------------
def migrate():
    print("Loading broker CSVs from:", TX_DIR)

    files = glob.glob(os.path.join(TX_DIR, "**/*.csv"), recursive=True) + \
            glob.glob(os.path.join(TX_DIR, "*.csv"))
    files = list(set(files))

    # Ensure table exists (also picks up new columns)
    SQLModel.metadata.create_all(engine)

    # Collect all rows to insert
    all_rows = []

    for f in sorted(files):
        fname = os.path.basename(f)
        broker, account = parse_file_meta(fname)
        print(f"\n  Parsing: {fname}  →  {broker} {account}")

        try:
            if "CIBC" in fname:
                df = parse_cibc(f)
            elif "RBC" in fname:
                df = parse_rbc(f)
            elif "TD" in fname:
                df = parse_td(f)
            else:
                print("    Skipped (unknown broker)")
                continue

            # Normalize symbols using shared cleaner
            df["Symbol"] = df.apply(
                lambda row: clean_symbol(row["Symbol"], broker, row.get("Description", "")), axis=1
            )
            df = df[df["Symbol"].str.strip() != ""]

            # Sort so buys come before sells on same day
            def rank(a):
                return 0 if a == "BUY" else (1 if a == "SELL" else 2)
            df["_rank"] = df["Action"].map(rank)
            df = df.sort_values(["Date", "_rank"])

            realized = compute_realized_fifo(df)

            for (sym, curr), vals in realized.items():
                if sym in NORBERT_GAMBIT_EXCLUDE:
                    print(f"    {sym:12s} [{curr}]  Skipped (Norbert's Gambit)")
                    continue
                pnl = vals["pnl"]
                cb  = vals["cost_basis"]
                if pd.isna(pnl):
                    continue
                print(f"    {sym:12s} [{curr}]  PnL={pnl:+.2f}  CostBasis={cb:.2f}")
                all_rows.append(RealizedPnL(
                    symbol=sym,
                    currency=curr,
                    pnl_amount=float(pnl),
                    cost_basis_sold=float(cb),
                    broker=broker,
                    account_type=account,
                    source="broker_csv",
                ))

        except Exception as e:
            print(f"    ERROR: {e}")

    # Upsert into DB
    with Session(engine) as session:
        existing = session.exec(select(RealizedPnL)).all()
        for row in existing:
            session.delete(row)
        session.commit()
        print(f"\nCleared {len(existing)} old rows.")

        for row in all_rows:
            session.add(row)
        session.commit()
        print(f"Inserted {len(all_rows)} RealizedPnL rows into Supabase.\n")


if __name__ == "__main__":
    migrate()
