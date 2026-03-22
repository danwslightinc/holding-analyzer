from sqlmodel import Session, select, func
from backend.database import engine
from backend.models import Holding, Transaction, InvestmentThesis

def check_portfolio():
    print("Checking Supabase Holdings with quantity > 0...")
    with Session(engine) as session:
        active_holdings = session.exec(select(Holding).where(Holding.quantity > 0)).all()
        print(f"Active Holdings Count: {len(active_holdings)}")
        for h in active_holdings:
            print(f"  {h.symbol} ({h.broker} {h.account_type}): {h.quantity}")
        
        print("\nChecking InvestmentThesis...")
        theses = session.exec(select(InvestmentThesis)).all()
        print(f"InvestmentThesis Count: {len(theses)}")
        for t in theses[:5]: # Show first 5
             print(f"  {t.symbol}: {t.thesis[:50]}...")

if __name__ == "__main__":
    check_portfolio()
