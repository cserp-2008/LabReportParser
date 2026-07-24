from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# 使用 SQLite
DATABASE_URL = "sqlite:///./labreport.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
