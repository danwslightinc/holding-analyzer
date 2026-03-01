import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")

# SQLAlchemy 1.4+ requires "postgresql://" instead of "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Check same thread is only needed for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10

# Handle Supabase-specific connection issues
if "supabase.co" in DATABASE_URL:
    # Ensure SSL is required for Supabase
    if "sslmode=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&sslmode=require"
        else:
            DATABASE_URL += "?sslmode=require"
    
    # Fix for DNS resolution issues on some machines
    if "db.oytloymrzmriqueyockm.supabase.co" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("db.oytloymrzmriqueyockm.supabase.co", "oytloymrzmriqueyockm.supabase.co")
    
    # Log connection attempt (redacted)
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    print(f"DEBUG: Attempting connection to {parsed.hostname} on port {parsed.port}")

# --- Database Connection Logic (with Fallback) ---
def create_monitored_engine(url, args):
    """Attempt to create engine and verify connection; fallback to SQLite if needed."""
    try:
        # If it's Postgres, test the connection immediately with a short timeout
        new_engine = create_engine(url, connect_args=args, pool_pre_ping=True, pool_recycle=300)
        with new_engine.connect() as conn:
            pass # Success
        return new_engine
    except Exception as e:
        if "sqlite" in url: # If even SQLite fails, we have bigger problems
            raise e
        print(f"⚠️ DATABASE WARNING: Primary connection failed. Falling back to local SQLite. Error: {e}")
        sqlite_url = "sqlite:///./portfolio.db"
        sqlite_args = {"check_same_thread": False}
        return create_engine(sqlite_url, connect_args=sqlite_args, pool_pre_ping=True)

engine = create_monitored_engine(DATABASE_URL, connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
