import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

def get_processed_database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    
    # SQLAlchemy 1.4+ requires "postgresql://" instead of "postgres://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Handle Supabase-specific connection issues
    if "supabase.co" in url:
        # Ensure SSL is required for Supabase
        if "sslmode=" not in url:
            if "?" in url:
                url += "&sslmode=require"
            else:
                url += "?sslmode=require"
    return url

DATABASE_URL = get_processed_database_url()

# Check same thread is only needed for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10

if "supabase.co" in DATABASE_URL:
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
