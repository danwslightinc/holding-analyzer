from sqlmodel import Session, select, create_engine
import os
from backend.models import InvestmentThesis

# Local database path
SQLITE_URL = "sqlite:///./portfolio.db"
SUPABASE_URL = "postgresql://postgres:47Cranleigh!@db.oytloymrzmriqueyockm.supabase.co:5432/postgres"

def recover_thesis():
    print("Attempting to recover thesis data from local SQLite backup (Mar 10)...")
    if not os.path.exists("./portfolio.db"):
        print("No local portfolio.db found.")
        return

    sqlite_engine = create_engine(SQLITE_URL)
    supabase_engine = create_engine(SUPABASE_URL)
    
    recovered_count = 0
    with Session(sqlite_engine) as sqlite_session:
        try:
            theses = sqlite_session.exec(select(InvestmentThesis)).all()
            print(f"Found {len(theses)} thesis entries in local backup.")
            
            with Session(supabase_engine) as supabase_session:
                for t in theses:
                    # Check if already exists in Supabase
                    existing = supabase_session.exec(select(InvestmentThesis).where(InvestmentThesis.symbol == t.symbol)).first()
                    if not existing:
                        # Re-create to avoid ID conflicts
                        new_t = InvestmentThesis(
                            symbol=t.symbol,
                            thesis=t.thesis,
                            conviction=t.conviction,
                            timeframe=t.timeframe,
                            kill_switch=t.kill_switch
                        )
                        supabase_session.add(new_t)
                        recovered_count += 1
                supabase_session.commit()
                print(f"Successfully restored {recovered_count} thesis entries to Supabase.")
        except Exception as e:
            print(f"Error during recovery: {e}")

if __name__ == "__main__":
    recover_thesis()
