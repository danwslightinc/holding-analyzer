import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")

# SQLAlchemy 1.4 requires "postgresql://" instead of "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Check same thread is only needed for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "supabase" in DATABASE_URL:
    # Adding SSL requirements for cloud DBs
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    
    # Log connection attempt (redacted)
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    print(f"DEBUG: Attempting connection to {parsed.hostname} on port {parsed.port}")

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
