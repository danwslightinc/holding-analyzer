from sqlmodel import Session, select
from backend.database import engine
from backend.models import Holding

def check_one():
    with Session(engine) as session:
        h = session.exec(select(Holding).where(Holding.symbol == 'VFV.TO')).first()
        if h:
            print(f"VFV.TO: qty={h.quantity}, broker={h.broker}, account={h.account_type}")
        else:
            print("VFV.TO not found")

if __name__ == "__main__":
    check_one()
