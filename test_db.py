from sqlmodel import Session, select
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import engine
from backend.models import Transaction, Holding

with Session(engine) as session:
    txs = session.exec(select(Transaction)).all()
    print("Total transactions in DB:", len(txs))
    holds = session.exec(select(Holding)).all()
    print("Total holdings in DB:", len(holds))
