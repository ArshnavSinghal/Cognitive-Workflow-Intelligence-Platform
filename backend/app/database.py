import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env from backend/ regardless of the working directory.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

# Allow DATABASE_URL to be absent during testing.
# The test suite overrides get_db with its own SQLite engine.
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    )
else:
    engine = create_engine("sqlite:///:memory:")

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
