import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define database directory
db_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(db_dir, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(db_dir, 'carepilot.db')}"

# Create Engine & Session Factory
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite multi-threading in FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()

def get_db():
    """Dependency injection helper to yield database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
