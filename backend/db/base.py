# backend/db/base.py
"""
SQLAlchemy base configuration and database setup
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./seetheplay.db")

# Create SQLAlchemy engine
# For SQLite, we need to enable foreign keys and set check_same_thread=False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )
else:
    # For PostgreSQL or other databases
    engine = create_engine(DATABASE_URL, echo=os.getenv("DB_ECHO", "false").lower() == "true")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()

# Metadata for table operations
metadata = MetaData()

# Database dependency for FastAPI
def get_db():
    """
    Dependency function to get database session
    Use in FastAPI endpoints like: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    Call this when starting the application
    """
    try:
        logger.info(f"Initializing database with URL: {DATABASE_URL}")
        
        # Import all models so they're registered with Base
        from . import models  # Import models to register them
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def drop_all_tables():
    """
    Drop all tables (useful for reset/testing)
    USE WITH CAUTION!
    """
    try:
        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        return False

# Test database connection
def test_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as connection:
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
