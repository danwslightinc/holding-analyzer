from sqlmodel import Session, select, func
from backend.database import engine
from backend.models import Holding, Transaction, InvestmentThesis

def check_counts():
    print("Checking Supabase DB counts...")
    with Session(engine) as session:
        h_count = session.exec(select(func.count()).select_from(Holding)).one()
        t_count = session.exec(select(func.count()).select_from(Transaction)).one()
        it_count = session.exec(select(func.count()).select_from(InvestmentThesis)).one()
        
        print(f"Holdings: {h_count}")
        print(f"Transactions: {t_count}")
        print(f"InvestmentThesis: {it_count}")
        
        if h_count > 0:
            h_sample = session.exec(select(Holding).limit(1)).first()
            print(f"Sample Holding: {h_sample.symbol} - {h_sample.quantity}")

if __name__ == "__main__":
    check_counts()
