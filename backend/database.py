import os
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")

# connect_args={"check_same_thread": False} is required for SQLite and FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
