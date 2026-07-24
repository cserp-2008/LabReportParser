from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# 使用 SQLite（默认）
DATABASE_URL = "sqlite:///./labreport.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_timeout=30,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
