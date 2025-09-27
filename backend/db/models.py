# backend/db/models.py (SQLAlchemy models if database is needed)
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"
    
    id = Column(String, primary_key=True)
    home_team_id = Column(String, nullable=False)
    away_team_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    quarter = Column(Integer, default=1)
    time_remaining = Column(String, default="15:00")
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    player_id = Column(String, nullable=False)
    stat_type = Column(String, nullable=False)  # passing_yards, touchdowns, etc.
    predicted_value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    probability_over = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GameEvent(Base):
    __tablename__ = "game_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    event_type = Column(String, nullable=False)
    player_id = Column(String, nullable=True)
    description = Column(String, nullable=False)
    quarter = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# backend/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()