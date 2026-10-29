"""backend/app/database/connection.py"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./driver_safety.db")
# If user puts MongoDB URI into DATABASE_URL, fall back to SQLite for SQLAlchemy
if DATABASE_URL.startswith("mongodb://") or DATABASE_URL.startswith("mongodb+srv://"):
    DATABASE_URL = "sqlite:///./driver_safety.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
