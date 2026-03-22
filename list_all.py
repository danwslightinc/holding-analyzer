from sqlmodel import Session, select
from backend.database import engine
from backend.models import Holding

def list_all():
    with Session(engine) as session:
        holdings = session.exec(select(Holding)).all()
        for h in holdings:
            print(f"'{h.symbol}' - {h.broker} - {h.quantity}")

if __name__ == "__main__":
    list_all()
